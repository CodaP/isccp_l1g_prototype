import numpy as np
import pandas as pd
import xarray as xr

import netCDF4

from tqdm import tqdm

import cartopy.crs as ccrs
import satpy

import warnings
from pathlib import Path
from utils import spherical_angle_add, ALL_CHANNELS, AHI_BANDS, ABI_BANDS, MSG_BANDS, remap, WMO_IDS

from collect_l1b import L1B_DIR
import time

COMP_CACHE = Path('composite_cache')
COMP_CACHE.mkdir(exist_ok=True)

INDEX = Path('index')

ENCODING = {
    'zlib':True,
    'dtype':'i2',
    '_FillValue':netCDF4.default_fillvals['i2'],
    'scale_factor':.01,
    'add_offset':50
}

def composite_channel(composite, channel, sat, dt, reader, band_map, wmo_id, wmo_ids, bar=None):
    grid_shape = wmo_ids.shape[-2:]
    if channel in band_map:
        band = band_map[channel]
    else:
        print(f'{sat} has no {channel}')
        return
    if sat.startswith('g'):
        index_band = {'01':'01','03':'01','05':'01','02':'02'}.get(band, '14')
    elif sat.startswith('h'):
        index_band = {'01':'01','02':'01','03':'03','04':'01'}.get(band, '14')
    elif sat.startswith('m'):
        index_band = 'IR_108'
    band_dir = L1B_DIR/dt/sat/f'{band}'
    assert band_dir.is_dir(), str(band_dir)
    index_dir = INDEX / sat / f'{index_band}'
    src_index = np.memmap(index_dir / 'src_index.dat', mode='r', dtype=np.uint64)
    dst_index = np.memmap(index_dir / 'dst_index.dat', mode='r', dtype=np.uint64)
    src_index_nn = np.memmap(index_dir / 'src_index_nn.dat', mode='r', dtype=np.uint64)
    dst_index_nn = np.memmap(index_dir / 'dst_index_nn.dat', mode='r', dtype=np.uint64)
    assert index_dir.is_dir()
    files = list(band_dir.glob('*'))
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        scene = satpy.Scene(files, reader=reader)
        ds_names = scene.available_dataset_names()
        scene.load(ds_names)
        area = scene[ds_names[0]].area
        if bar is not None:
            bar.set_description(f'Loading {sat} band {band}')
        v = scene[ds_names[0]].values
    if bar is not None:
        bar.set_description('Remapping imagery')
    out = remap(src_index, dst_index, v, grid_shape)
    out_nn = remap(src_index_nn, dst_index_nn, v, grid_shape)
    scene.unload()
    if bar is not None:
        bar.set_description('Compositing')
    for layer in range(composite.shape[0]):
        mask = wmo_ids[layer].values == wmo_id
        composite.values[layer, mask] = out_nn[mask]
        mask = wmo_ids[layer].values  == (wmo_id | 0x1000)
        composite.values[layer, mask] = out[mask]


def main(dt, progress=True):
    dt = dt.strftime('%Y%m%dT%H%M')
    wmo_ids = xr.open_dataset(COMP_CACHE / 'wmo_id.nc').wmo_id
    grid_shape = wmo_ids.shape[-2:]
    ordered_channels = ['temp_11_00um', *sorted(ALL_CHANNELS - set('temp_11_0um'))]
    out_dir = COMP_CACHE / dt
    out_dir.mkdir(exist_ok=True)
    for channel in ordered_channels:
        out_nc = out_dir / f'{channel}.nc'
        start = time.time()
        composite = xr.DataArray(np.full((3, *grid_shape), np.nan, dtype=np.float32), dims=['layer','lat','lon'])
        tasks = [('g16','abi_l1b', ABI_BANDS),
                   ('g17','abi_l1b', ABI_BANDS),
                   ('h8','ahi_hsd', AHI_BANDS),
                ('m8','seviri_l1b_hrit', MSG_BANDS), ('m11','seviri_l1b_hrit',MSG_BANDS)]
        if progress:
            with tqdm(tasks) as bar:
                for sat, reader, band_map in bar:
                    wmo_id = WMO_IDS[sat]
                    composite_channel(composite, channel, sat, dt, reader, band_map, wmo_id, wmo_ids, bar=bar)
        else:
            for sat, reader, band_map in tasks:
                wmo_id = WMO_IDS[sat]
                composite_channel(composite, channel, sat, dt, reader, band_map, wmo_id, wmo_ids)
        print(f"Saving {out_nc}")
        composite.to_dataset(name=channel).to_netcdf(out_nc, encoding={channel:ENCODING})
        end = time.time()
        dur = end - start
        print(f'Took {dur:.1f} sec')
    return out_dir


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('dt')
    args = parser.parse_args()
    dt = pd.to_datetime(args.dt)
    main(dt)
