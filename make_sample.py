import numpy as np
import pandas as pd
import xarray as xr

import netCDF4

from tqdm import tqdm

import cartopy.crs as ccrs
import satpy

import warnings
from pathlib import Path
from utils import spherical_angle_add, ALL_BANDS, AHI_BANDS, ABI_BANDS, MSG_BANDS, remap_fast_mean, remap_with_stats, WMO_IDS, ALL_SATS, STATS_BANDS, STATS_FUNCS
from make_index import get_index_bands

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

def composite_band(composite, band, index_band, sat, dt, reader, wmo_id, wmo_ids, sample_mode, with_stats=False, bar=None):
    grid_shape = wmo_ids.shape
    if composite is None:
        if with_stats:
            composite = {k:
                         xr.DataArray(np.full(grid_shape, np.nan, dtype=np.float32), dims=['layer','latitude','longitude'])
                         for k in STATS_FUNCS}
        else:
            composite = xr.DataArray(np.full(grid_shape, np.nan, dtype=np.float32), dims=['layer','latitude','longitude'])
    band_dir = L1B_DIR/dt/sat/f'{band}'
    assert band_dir.is_dir(), str(band_dir)
    index_dir = INDEX / sat / f'{index_band}'
    src_index = np.memmap(index_dir / 'src_index.dat', mode='r', dtype=np.uint32)
    dst_index = np.memmap(index_dir / 'dst_index.dat', mode='r', dtype=np.uint32)
    src_index_nn = np.memmap(index_dir / 'src_index_nn.dat', mode='r', dtype=np.uint32)
    dst_index_nn = np.memmap(index_dir / 'dst_index_nn.dat', mode='r', dtype=np.uint32)
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
        
        
    if not with_stats:
        remap = remap_fast_mean
    else:
        remap = remap_with_stats
        
    out = remap(src_index, dst_index, v, grid_shape[-2:])
    out_nn = remap(src_index_nn, dst_index_nn, v, grid_shape[-2:])
    scene.unload()
    
    def do_composite(composite, out_nn, out, do_nn=True):
        if bar is not None:
            bar.set_description('Compositing')
        for layer in range(composite.shape[0]):
            if do_nn:
                # Nearest-neighbor sampling
                mask = (wmo_ids[layer].values == wmo_id) & (sample_mode[layer].values == 1)
                composite.values[layer, mask] = out_nn[mask]
            # Agg sampling
            mask = (wmo_ids[layer].values  == wmo_id) & (sample_mode[layer].values == 2)
            composite.values[layer, mask] = out[mask]
    if not with_stats:
        do_composite(composite, out_nn, out)
    else:
        for k in out:
            do_composite(composite[k], out_nn[k], out[k], do_nn=k=='mean')
            
    return composite


def main(dt, progress=True):
    dt = dt.strftime('%Y%m%dT%H%M')
    wmo_ids = xr.open_dataset(COMP_CACHE / 'wmo_id.nc').wmo_id
    sample_mode = xr.open_dataset(COMP_CACHE / 'sample_mode.nc').sample_mode
    grid_shape = wmo_ids.shape
    ordered_bands = ['temp_11_00um', *sorted(ALL_BANDS - set('temp_11_0um'))]
    out_dir = COMP_CACHE / dt
    out_dir.mkdir(exist_ok=True)
    for band in ordered_bands:
        with_stats = band in STATS_BANDS
        if with_stats:
            out_nc = {k:out_dir / f'{band}_{k}.nc' for k in STATS_FUNCS}
            out_nc['mean'] = out_dir / f'{band}.nc'
            for f in out_nc.values():
                if f.exists():
                    print(f'Already have {f}')
                    continue
        else:
            out_nc = out_dir / f'{band}.nc'
            if out_nc.exists():
                print(f'Already have {out_nc}')
                continue
        start = time.time()
        def run(it,bar=None):
            composite = None
            for attrs in it:
                sat = attrs['sat']
                reader = attrs['reader']
                if band not in attrs['bands']:
                    continue
                res = attrs['res'][band]
                wmo_id = WMO_IDS[sat]
                index_band = get_index_bands(attrs['res'])[res]
                composite = composite_band(composite, band, index_band, sat, dt, reader, wmo_id, wmo_ids, sample_mode, with_stats=with_stats, bar=bar)
            return composite
        if progress:
            with tqdm(ALL_SATS) as bar:
                composite = run(bar, bar=bar)
        else:
            composite = run(ALL_SATS)
        print(f"Saving {out_nc}")
        if with_stats:
            for k in sorted(composite):
                if k == 'mean':
                    composite[band] = composite[k]
                    out_nc[band] = out_nc[k]
                else:
                    composite[f'{band}_{k}'] = composite[k]
                    out_nc[f'{band}_{k}'] = out_nc[k]
                del composite[k]
                del out_nc[k]
            for k in composite:
                composite[k].to_dataset(name=k).to_netcdf(out_nc[k], encoding={k:ENCODING})
        else:
            composite.to_dataset(name=band).to_netcdf(out_nc, encoding={band:ENCODING})
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
