import numpy as np
import pandas as pd
import xarray as xr
import sys
import satpy
import warnings
from pathlib import Path
from utils import remap_fast_rad_mean, remap_fast_mean, remap_with_stats_rad, remap_with_stats, WMO_IDS, ALL_SATS, STATS_BANDS, STATS_FUNCS, BAND_CENTRAL_WAV
import make_netcdf
from make_index import get_index_bands
from collect_l1b import band_dir_path
import time
import tempfile
import os
import shutil
import repair_msg
from contextlib import contextmanager
import zstandard as zstd

WMO_ID = WMO_IDS
USER = os.environ['USER']

SAMPLE_CACHE = Path('dat/sample_cache').resolve()
SAMPLE_CACHE.mkdir(exist_ok=True)

INDEX = Path('dat/index').absolute()

orig_print = print
def print(*args, flush=False, **kwargs):
    orig_print(*args, flush=True, **kwargs)


def open_index(INDEX, sat, index_band):
    index_dir = INDEX / sat / f'{index_band}'
    assert index_dir.is_dir(), str(index_dir)
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
            #with open('/dev/null','w') as out:
                #with open('/dev/null','w') as err:
                    #sys.stdout = out
                    #sys.stderr = err
            scene = satpy.Scene([str(f) for f in files], reader=reader)
            ds_names = scene.available_dataset_names()
            scene.load(ds_names)
        except Exception as e:
            raise IOError('Problem reading files', e.args)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        try:
            area = scene[ds_names[0]].area
        except KeyError as e:
            print('Error', e.args)
            raise IOError('Problem reading files', e.args)
        v = scene[ds_names[0]]
        return v, area


def sample_band(band, index_band, sat, dt, reader, wmo_id, wmo_ids, sample_mode, tmp, l1b_dir=None, with_stats=False, bar=None):
    wavelength = BAND_CENTRAL_WAV[band]
    if with_stats:
        sample = {k:np.full(GRID_SHAPE, np.nan, dtype=np.float32) for k in STATS_FUNCS}
    else:
        sample = np.full(GRID_SHAPE, np.nan, dtype=np.float32)
    band_dir = band_dir_path(dt, sat, band, l1b_dir=l1b_dir)
    if not band_dir.is_dir():
        raise IOError(f"Missing {band_dir}")
    src_index, dst_index, src_index_nn, dst_index_nn = open_index(INDEX, sat, index_band)
    files = [f.absolute() for f in band_dir.glob('*')]
    cwd = os.getcwd()
    try:
        v, area = read_scene(files, reader)
        v = v.values
    except IOError:
        # if MSG, we may have a fix
        if sat[0] == 'm':
            print('Trying to repair')
            for l1b_f in files:
                repair_msg.repair_msg_l1b_cache(l1b_f, tmp)
            # Try again
            v, area = read_scene(files, reader)
            v = v.values
            print('Repair successful')
        else:
            raise
    finally:
        # read_scene will randomly destroy the cwd. like. what the hell?
        os.chdir(cwd)
    
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

    out = remap(src_index, dst_index, v, GRID_SHAPE)
    out_nn = remap(src_index_nn, dst_index_nn, v, GRID_SHAPE)
    
    def do_sample(sample, out_nn, out, do_nn=True):
        if bar is not None:
            bar.set_description(f'Sampling {sat} {band} {dt}')
        for layer in range(sample_mode.shape[0]):
            if do_nn:
                # Nearest-neighbor sampling
                mask = (wmo_ids[layer].values == wmo_id) & (sample_mode[layer].values == 2)
                sample[mask] = out_nn[mask]
            # Agg sampling
            mask = (wmo_ids[layer].values == wmo_id) & (sample_mode[layer].values == 1)
            sample[mask] = out[mask]
    if not with_stats:
        do_sample(sample, out_nn, out)
    else:
        for k in out:
            do_sample(sample[k], out_nn[k], out[k], do_nn=k == 'mean')
            
    return sample


def sample_path(dt, band, sat):
    path = SAMPLE_CACHE / dt.strftime(f'%Y/%m/%d/%H%M/{sat}/{band}.dat.zstd')
    path.parent.mkdir(exist_ok=True, parents=True)
    return path


@contextmanager
def tmpdir(sat, band, dt):
    tmp_root = Path(tempfile.gettempdir())
    tmp = tmp_root / dt.strftime(f'{USER}_{sat}_{band}_%Y%m%dT%H%M')
    if tmp.is_dir():
        shutil.rmtree(tmp)
    tmp.mkdir()
    try:
        tempfile.tempdir = str(tmp)
        os.environ['TMP'] = str(tmp)
        yield tmp
    finally:
        if tmp.is_dir():
            shutil.rmtree(tmp)
        tempfile.tempdir = str(tmp_root)
        os.environ['TMP'] = str(tmp_root)


def check_output_paths(sat, dt, band, with_stats):
    if with_stats:
        output_paths = {}
        any_missing = False
        for k in STATS_FUNCS:
            if k == 'mean':
                _band = band
            else:
                _band = f'{band}_{k}'
            out_path = sample_path(dt, _band, sat)
            output_paths[k] = out_path
            if not out_path.is_file():
                any_missing = True
        return output_paths, not any_missing
    else:
        out_path = sample_path(dt, band, sat)
        return out_path, out_path.is_file()


def save(sample, band, out_path, grid_shape=None):
    if grid_shape is None:
        grid_shape = (3600,7200)
    encoding = make_netcdf.default_encoding(grid_shape)[band]
    fill = encoding['_FillValue']
    dtype = encoding['dtype']
    if 'add_offset' in encoding:
        sample -= encoding['add_offset']
    if 'scale_factor' in encoding:
        sample /= encoding['scale_factor']
    # if float dtype, round to nearest integer
    if sample.dtype in (np.float32, np.float64):
        sample = np.round(sample)
        data = np.full(sample.shape, fill, dtype=dtype)
        mask = np.isfinite(sample)
        data[mask] = sample[mask].astype(dtype)
    else:
        data = sample.astype(dtype)
    tmp_out = out_path.parent / ('.' + out_path.name)
    with open(tmp_out, 'wb') as fp:
        fp.write(zstd.compress(data))
    tmp_out.rename(out_path)


def save_all(sample, band, with_stats, output_paths):
    if with_stats:
        for k in sample:
            if k == 'mean':
                _band = band
            else:
                _band = f'{band}_{k}'
            save(sample[k], _band, output_paths[k])
    else:
        save(sample, band, output_paths)

def load_sort_data(comp_dir):
    global GRID_SHAPE
    wmo_ids = xr.open_dataset(comp_dir / 'wmo_id.nc').wmo_id
    sample_mode = xr.open_dataset(comp_dir / 'sample_mode.nc').sample_mode
    GRID_SHAPE = sample_mode.shape[-2:]
    return wmo_ids, sample_mode


def main(sat, band, dt, comp_dir=None, progress=True):

    comp_dir = Path(comp_dir)
    if not comp_dir.is_dir():
        print(f'Invalid comp directory {comp_dir}')
        return
    wmo_ids, sample_mode = load_sort_data(comp_dir)

    ## Resolve satellite
    for attrs in ALL_SATS:
        if attrs['sat'] == sat:
            break
    else:
        print(f'Unknown satellite {sat}')
        return

    reader = attrs['reader']
    wmo_id = WMO_ID[sat]

    ## Resolve band
    _band, with_stats = should_stats(band)
    if _band not in attrs['bands']:
        print(f'Unknown band {_band} for satellite {sat}')
        return

    output_paths, already_have = check_output_paths(sat, dt, _band, with_stats)
    if already_have:
        print(f'Already have {sat} {_band} {dt}')
        return

    res = attrs['res'][_band]
    index_band = get_index_bands(attrs['res'])[res]

    start = time.time()
    
    try:
        with tmpdir(sat, _band, dt) as tmp:
            sample = sample_band(_band, index_band, sat, dt, reader, wmo_id, wmo_ids, sample_mode, tmp, with_stats=with_stats)
        if sample is None:
            print(f'No data for {sat} {_band} {dt}')
            return
        else:
            save_all(sample, _band, with_stats, output_paths)
    except IOError as e:
        print(f'Error reading {sat} {_band} {dt}: {e}')
        raise
        return

    end = time.time()
    print(f'Finished {sat} {_band} {dt} in {end-start:.1f} seconds')


def should_stats(band):
    for b in STATS_BANDS:
        if band.startswith(b):
            return b, True
    return band, False


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--freq',default='30min')
    parser.add_argument('--compdir', required=True)
    parser.add_argument('sat')
    parser.add_argument('band')
    parser.add_argument('dt')
    parser.add_argument('end', nargs='?')
    args = parser.parse_args()
    dt = pd.to_datetime(args.dt)
    if args.end is not None:
        end = pd.to_datetime(args.end)
        for dt in pd.date_range(dt, end, freq=args.freq):
            print(args.sat, args.band, dt)
            try:
                main(args.sat, args.band, dt, comp_dir=args.compdir)
            except Exception as e:
                print(e, flush=True)
            finally:
                pass
    else:
        main(args.sat, args.band, dt, comp_dir=args.compdir)

