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
WMO_ID = WMO_IDS
from make_index import get_index_bands
from collect_l1b import band_dir_path
import time
import tempfile
import os
USER = os.environ['USER']
import shutil

import repair_msg

import sys

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

WMO_IDS = xr.open_dataset(COMP_CACHE / 'wmo_id.nc').wmo_id
SAMPLE_MODE = xr.open_dataset(COMP_CACHE / 'sample_mode.nc').sample_mode
GRID_SHAPE = WMO_IDS.shape
print(GRID_SHAPE)

orig_print = print
def print(*args, flush=False, **kwargs):
    orig_print(*args, flush=True, **kwargs)


def open_index(INDEX, sat, index_band):
    index_dir = INDEX / sat / f'{index_band}'
    assert index_dir.is_dir()
    src_index = np.memmap(index_dir / 'src_index.dat', mode='r', dtype=np.uint32)
    dst_index = np.memmap(index_dir / 'dst_index.dat', mode='r', dtype=np.uint32)
    src_index_nn = np.memmap(index_dir / 'src_index_nn.dat', mode='r', dtype=np.uint32)
    dst_index_nn = np.memmap(index_dir / 'dst_index_nn.dat', mode='r', dtype=np.uint32)
    return src_index, dst_index, src_index_nn, dst_index_nn


def read_scene(files, reader, bar=None):
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
        except Exception as e:
            raise IOError('Problem reading files')
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        try:
            area = scene[ds_names[0]].area
        except KeyError as e:
            print('Error', e.args)
            raise IOError('Problem reading files')
        if bar is not None:
            bar.set_description(dt.strftime(f'Loading {sat} band {band} %Y%m%dT%H%M'))
        v = scene[ds_names[0]]
        return v, area


def composite_band(composite, band, index_band, sat, dt, reader, wmo_id, wmo_ids, sample_mode, tmp, with_stats=False, bar=None):
    wavelength = BAND_CENTRAL_WAV[band]
    if composite is None:
        if with_stats:
            composite = {k:
                         xr.DataArray(np.full(GRID_SHAPE, np.nan, dtype=np.float32), dims=['layer','latitude','longitude'])
                         for k in STATS_FUNCS}
        else:
            composite = xr.DataArray(np.full(GRID_SHAPE, np.nan, dtype=np.float32), dims=['layer','latitude','longitude'])
    band_dir = band_dir_path(dt, sat, band)
    if not band_dir.is_dir():
        raise IOError(f"Missing {band_dir}")
    src_index, dst_index, src_index_nn, dst_index_nn = open_index(INDEX, sat, index_band)
    files = list(band_dir.glob('*'))
    try:
        v, area = read_scene(files, reader)
    except IOError:
        # if MSG, we may have a fix
        if sat[0] == 'm':
            for l1b_f in files:
                repair_msg.repair_msg_l1b_cache(l1b_f, tmp)
            # Try again
            v, area = read_scene(files, reader)
        else:
            raise
        
    v = v.values
    if np.isnan(v).all():
        print(sat, band, 'All NaN')
    if bar is not None:
        bar.set_description(dt.strftime(f'Remapping imagery {sat} {band} %Y%m%dT%H%M'))
        
        
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
        
    out = remap(src_index, dst_index, v, GRID_SHAPE[-2:])
    out_nn = remap(src_index_nn, dst_index_nn, v, GRID_SHAPE[-2:])
    #scene.unload()
    
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


def comp_cache_dir(dt):
    out_dir = COMP_CACHE / dt.strftime('%Y/%m/%d/%H%M')
    out_dir.mkdir(exist_ok=True, parents=True)
    return out_dir


def save_netcdf(ds, out_nc, encoding=None):
    out_nc = Path(out_nc)
    tmp_out_nc = out_nc.parent / (out_nc.name+'.tmp')
    ds.to_netcdf(tmp_out_nc, encoding=encoding)
    tmp_out_nc.rename(out_nc)


def main(dt, progress=True):
    ordered_bands = ['temp_11_00um', *sorted(ALL_BANDS - set(['temp_11_00um']))]
    out_dir = comp_cache_dir(dt)
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
                wmo_id = WMO_ID[sat]
                index_band = get_index_bands(attrs['res'])[res]
                tmp_root = Path(tempfile.gettempdir())
                tmp = tmp_root / dt.strftime(f'{USER}_{sat}_{band}_%Y%m%dT%H%M')
                if tmp.is_dir():
                    shutil.rmtree(tmp)
                tmp.mkdir()
                try:
                    tempfile.tempdir = str(tmp)
                    os.environ['TMP'] = str(tmp)
                    composite = composite_band(composite, band, index_band, sat, dt, reader, wmo_id, WMO_IDS, SAMPLE_MODE, tmp, with_stats=with_stats, bar=bar)
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
        if with_stats and composite is not None:
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
                save_netcdf(composite[k].to_dataset(name=k), out_nc[k], encoding={k:ENCODING})
        elif composite is not None:
            save_netcdf(composite.to_dataset(name=band), out_nc, encoding={band:ENCODING})
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
            print(dt)
            try:
                main(dt)
            #except Exception as e:
                #print(e, flush=True)
            finally:
                pass
    else:
        main(dt)

