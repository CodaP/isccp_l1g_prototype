import numpy as np
import pandas as pd
import xarray as xr

import netCDF4

from tqdm import tqdm
import sys

import cartopy.crs as ccrs
import satpy

import warnings
from pathlib import Path
from utils import spherical_angle_add, ALL_BANDS, AHI_BANDS, ABI_BANDS, MSG_BANDS, remap_fast_rad_mean, remap_fast_mean, remap_with_stats_rad, remap_with_stats, WMO_IDS, ALL_SATS, STATS_BANDS, STATS_FUNCS, BAND_CENTRAL_WAV
from make_index import get_index_bands

from collect_l1b import L1B_DIR
import time
import tempfile
import os
import shutil

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

orig_print = print
def print(*args, flush=False, **kwargs):
    orig_print(*args, flush=True, **kwargs)

def composite_band(composite, band, index_band, sat, dt, reader, wmo_id, wmo_ids, sample_mode, with_stats=False, bar=None):
    wavelength = BAND_CENTRAL_WAV[band]
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
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        try:
            with open('/dev/null','w') as out:
                with open('/dev/null','w') as err:
                    sys.stdout = out
                    sys.stderr = err
                    scene = satpy.Scene(files, reader=reader)
                    ds_names = scene.available_dataset_names()
                    scene.load(ds_names)
        except Exception:
            raise IOError('Problem reading files')
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        try:
            area = scene[ds_names[0]].area
        except KeyError:
            raise IOError('Problem reading files')
        if bar is not None:
            bar.set_description(f'Loading {sat} band {band} {dt}')
        v = scene[ds_names[0]].values
    if bar is not None:
        bar.set_description(f'Remapping imagery {sat} {band} {dt}')
        
        
    if not with_stats:
        if 'temp' in band:
            def remap(*args,**kwargs):
                return remap_fast_rad_mean(*args,wavelength,**kwargs)
        else:
            remap = remap_fast_mean
    else:
        if 'temp' in band:
            def remap(*args,**kwargs):
                return remap_with_stats_rad(*args,wavelength,**kwargs)
        else:
            remap = remap_with_stats
        
    out = remap(src_index, dst_index, v, grid_shape[-2:])
    out_nn = remap(src_index_nn, dst_index_nn, v, grid_shape[-2:])
    scene.unload()
    
    def do_composite(composite, out_nn, out, do_nn=True):
        if bar is not None:
            bar.set_description(f'Compositing {sat} {band} {dt}')
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
    print(grid_shape)
    ordered_bands = ['temp_11_00um', *sorted(ALL_BANDS - set(['temp_11_00um']))]
    out_dir = COMP_CACHE / dt
    out_dir.mkdir(exist_ok=True)
    for band in ordered_bands:
        with_stats = band in STATS_BANDS
        if with_stats:
            out_nc = {k:out_dir / f'{band}_{k}.nc' for k in STATS_FUNCS}
            out_nc['mean'] = out_dir / f'{band}.nc'
            if all([f.exists() for f in out_nc.values()]):
                continue
        else:
            out_nc = out_dir / f'{band}.nc'
            if out_nc.exists():
                #print(f'Already have {out_nc}')
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
                tmp_root = Path(tempfile.gettempdir())
                tmp = tmp_root / f'{sat}_{band}_{dt}'
                tmp.mkdir()
                try:
                    tempfile.tempdir = str(tmp)
                    os.environ['TMP'] = str(tmp)
                    composite = composite_band(composite, band, index_band, sat, dt, reader, wmo_id, wmo_ids, sample_mode, with_stats=with_stats, bar=bar)
                except IOError:
                    print(f'Error reading {sat}')
                finally:
                    shutil.rmtree(tmp)
                    tempfile.tempdir = str(tmp_root)
                    os.environ['TMP'] = str(tmp_root)
            return composite
        if progress:
            with tqdm(ALL_SATS) as bar:
                composite = run(bar, bar=bar)
        else:
            composite = run(ALL_SATS)
        if isinstance(out_nc, dict):
            print(f"Saving {out_nc.values()}")
        else:
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
    parser.add_argument('end', nargs='?')
    args = parser.parse_args()
    dt = pd.to_datetime(args.dt)
    if args.end is not None:
        end = pd.to_datetime(args.end)
        for dt in pd.date_range(dt, end, freq='30min'):
            try:
                main(dt)
            except Exception as e:
                print(e, flush=True)
    else:
        main(dt)

