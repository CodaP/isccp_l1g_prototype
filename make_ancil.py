from make_composite import netcdf_path, save_netcdf, load_wmo_ids
from utils import get_grid
import pandas as pd
from pathlib import Path
import xarray as xr


def load_sample_mode(f):
    ds = xr.open_dataset(f)
    return ds['sample_mode'].load()

def main(dt, comp_dir, force=False):
    comp_dir = Path(comp_dir)
    wmo_id_f = comp_dir / 'wmo_id.nc'
    sample_mode_f = comp_dir / 'sample_mode.nc'
    grid = get_grid()
    lon, lat = grid.get_lonlats()
    lon = lon[0]
    lat = lat[:,0]
    wmo_ids = lambda: load_wmo_ids(wmo_id_f)
    sample_mode = lambda: load_sample_mode(sample_mode_f)
    for k,f in [('wmo_id',wmo_ids),('sample_mode',sample_mode)]:
        out = netcdf_path(k, dt)
        if out.exists() and not force:
            print(f'Already have {out}')
        else:
            save_netcdf(f(), out, k, dt, lat, lon)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--freq', default='30min')
    parser.add_argument('--compdir')
    parser.add_argument('dt')
    parser.add_argument('end', nargs='?')
    args = parser.parse_args()
    dt = pd.to_datetime(args.dt)
    if args.end is not None:
        end = pd.to_datetime(args.end)
        for dt in pd.date_range(dt, end, freq=args.freq):
            print(dt)
            main(dt, args.compdir)
    else:
        main(dt, args.compdir)

