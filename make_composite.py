import numpy as np
import pandas as pd
import xarray as xr

from pathlib import Path
import time
import os
USER = os.environ['USER']
import make_netcdf
import zstandard as zstd
from utils import ALL_SATS, get_grid
from make_sample import sample_path
import traceback

NETCDF_OUT = Path('dat/final').absolute()
NETCDF_OUT.mkdir(exist_ok=True)
AUX_VARS = {'pixel_time', 'satellite_azimuth_angle', 'satellite_zenith_angle', 'wmo_id'}

orig_print = print
def print(*args, flush=False, **kwargs):
    orig_print(*args, flush=True, **kwargs)

def save_netcdf(da, out, k, dt, lat, lon):
    ds = da.to_dataset(name=k)
    grid_shape = ds[k].shape[-2:]
    tmp_out = out.with_suffix('.tmp')

    make_netcdf.set_latlon(ds, lat, lon)

    attrs = make_netcdf.default_attrs()
    ds[k].attrs.update(attrs.get(k,{}))

    encoding = make_netcdf.default_encoding(grid_shape)
    ds = make_netcdf.add_time(ds, dt, encoding)

    encoding = {k:v for k,v in encoding.items() if k in ds}
    for a in ['scale_factor', 'add_offset']:
        if a in encoding.get(k,{}):
            ds[k].attrs[a] = encoding[k][a]
            del encoding[k][a]
    
    ds.to_netcdf(tmp_out, encoding=encoding)
    tmp_out.rename(out)
    return out


def read_dat(f, band, grid_shape=None):
    if grid_shape is None:
        grid_shape = GRID_SHAPE
    encoding = make_netcdf.default_encoding(grid_shape)[band]
    fill = encoding['_FillValue']
    dtype = encoding['dtype']
    with open(f, 'rb') as fp:
        dat = np.frombuffer(zstd.decompress(fp.read()), dtype=dtype)
    dat = dat.reshape(grid_shape[-2:])
    dat = np.ma.masked_equal(dat, fill)
    dat.fill_value = fill
    return dat

def load_wmo_ids(f):
    global GRID_SHAPE
    wmo_id = xr.open_dataset(f).wmo_id
    GRID_SHAPE = wmo_id.shape
    return wmo_id

def netcdf_path(band, dt, root=NETCDF_OUT):
    out_dir = make_netcdf.make_output_dir(root, dt)
    out = out_dir / make_netcdf.filename(band, dt)
    return out

def main(dt, band, wmo_id_file=None, force=False):
    out = netcdf_path(band, dt)
    if out.exists() and not force:
        print(f'Already have {out}')
        return
    make_composite(out, dt, band, wmo_id_file=wmo_id_file)


def make_composite(out, dt, band, wmo_id_file=None):
    grid = get_grid()
    lon, lat = grid.get_lonlats()
    lon = lon[0]
    lat = lat[:,0]

    wmo_ids = load_wmo_ids(wmo_id_file)
    
    start = time.time()
    composite = None
    for attrs in ALL_SATS:
        sat = attrs['sat']
        bands = attrs['bands']
        wmo_id = attrs['wmo_id']
        if band not in (set(bands) | AUX_VARS):
            print(f'{sat} might not have {band}')
        sample_f = sample_path(dt, band, sat)
        if band == 'wmo_id':
            sample_f = Path(wmo_id_file)
        if not sample_f.exists():
            print(f'{sample_f} does not exist')
            continue
        print(f'Loading {sample_f}')
        sample = read_dat(sample_f, band)
        if composite is None:
            composite = xr.DataArray(np.full(GRID_SHAPE, sample.fill_value, dtype=sample.dtype), dims=['layer','latitude','longitude'])
        for layer in range(composite.shape[0]):
            mask = (wmo_ids[layer] == wmo_id)
            composite.values[layer, mask] = sample[mask]
    if composite is None:
        print(f'No data for {dt}')
        return
    print(f'Compositing took {time.time()-start:.1f}s')
    print(f'Writing {out}')
    save_netcdf(composite, out, band, dt, lat, lon)
    return out


def ladvise(dt, band):
    import subprocess
    for attrs in ALL_SATS:
        sat = attrs['sat']
        sample_f = sample_path(dt, band, sat)
        if sample_f.exists():
            subprocess.run(['lfs','ladvise','-a','willread',str(sample_f)])


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--freq',default='30min')
    parser.add_argument('-w', '--wmoids', required=True)
    parser.add_argument('-f','--force', action='store_true')
    parser.add_argument('band')
    parser.add_argument('dt')
    parser.add_argument('end', nargs='?')
    args = parser.parse_args()
    dt = pd.to_datetime(args.dt)
    if args.end is not None:
        end = pd.to_datetime(args.end)
        for dt in pd.date_range(dt, end, freq=args.freq):
            print(dt)
            try:
                main(dt, args.band, wmo_id_file=args.wmoids, force=args.force)
            except Exception as e:
                traceback.print_exc()
            finally:
                pass
    else:
        main(dt, args.band, wmo_id_file=args.wmoids, force=args.force)

