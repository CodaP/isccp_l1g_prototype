import xarray as xr
import numpy as np
import pandas as pd
import make_netcdf
from make_composite import NETCDF_OUT
import time
from utils import get_grid

import warnings
from pysolar.solar import get_altitude, get_azimuth, get_altitude_fast, get_azimuth_fast

def _get_solzen(start_time, latitude, longitude):
    lon,lat = np.meshgrid(longitude, latitude, copy=False)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        altitude = get_altitude_fast(lat.ravel(), lon.ravel(), start_time)
    solzen = (90-altitude).reshape(lon.shape)
    return solzen


def _get_solazi(start_time, latitude, longitude):
    lon,lat = np.meshgrid(longitude, latitude, copy=False)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        azimuth = get_azimuth_fast(lat.ravel(), lon.ravel(), start_time)
    solazi = azimuth.reshape(lon.shape)
    solazi = (solazi+180) % 360 - 180
    return solazi


def save_netcdf(v, out, k, dt, lat, lon):
    dt = dt.replace(tzinfo=None)
    da = xr.DataArray(v, dims=['latitude','longitude'])
    ds = da.to_dataset(name=k)
    grid_shape = ds[k].shape[-2:]
    tmp_out = out.with_suffix('.tmp')

    make_netcdf.set_latlon(ds, lat, lon)

    attrs = make_netcdf.default_attrs()
    ds[k].attrs.update(attrs.get(k,{}))

    encoding = make_netcdf.default_encoding(grid_shape)
    ds = make_netcdf.add_time(ds, dt, encoding)

    encoding = {k:v for k,v in encoding.items() if k in ds}
    
    ds.to_netcdf(tmp_out, encoding=encoding)
    tmp_out.rename(out)
    return out


def make_solar(dt):
    start = time.time()

    out_dir = make_netcdf.make_output_dir(NETCDF_OUT, dt)
    sza_out = out_dir / make_netcdf.filename('solar_zenith_angle', dt)
    saa_out = out_dir / make_netcdf.filename('solar_azimuth_angle', dt)
    if sza_out.exists() and saa_out.exists():
        print(f'Already have {saa_out} and {sza_out}')
        return
    # load grid
    grid = get_grid()
    lon, lat = grid.get_lonlats()
    lon = lon[0]
    lat = lat[:,0]
    print('Calculating solar zenith angle')
    sza = _get_solzen(dt, lat, lon)
    save_netcdf(sza, sza_out, 'solar_zenith_angle', dt, lat, lon)
    print('Calculating solar azimuth angle')
    saa = _get_solazi(dt, lat, lon)
    save_netcdf(saa, saa_out, 'solar_azimuth_angle', dt, lat, lon)
    print(f'Wrote {saa_out} and {sza_out} in {time.time()-start:.1f} seconds')
    

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--freq', default='30min')
    parser.add_argument('start')
    parser.add_argument('end', nargs='?', default=None)
    args = parser.parse_args()
    dt = pd.to_datetime(args.start, utc=True).to_pydatetime()
    if args.end is not None:
        end = pd.to_datetime(args.end, utc=True).to_pydatetime()
        for dt in pd.date_range(dt, end, freq=args.freq):
            print(dt)
            try:
                 make_solar(dt)
            except Exception as e:
                print(e, flush=True)
            finally:
                pass
    else:
         make_solar(dt)


