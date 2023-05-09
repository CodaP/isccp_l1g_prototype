import numpy as np
import xarray as xr
import netCDF4
import cartopy.crs as ccrs
from tqdm import tqdm

from satpy.readers.utils import get_geostationary_angle_extent
from utils import spherical_angle_add, get_area, ALL_SATS

from collect_l1b import L1B_DIR
import make_sample
import tempfile
from collect_l1b import band_dir_path

from pathlib import Path
import shutil
import warnings
import time
from datetime import datetime
import os
import pandas as pd

def get_satzen(area):
    height, width = area.shape
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        proj = area.to_cartopy_crs()
        xang, yang = get_geostationary_angle_extent(area)
        x,y = np.meshgrid(np.linspace(-xang, xang,width, dtype=np.float32),
                        np.linspace(-yang, yang, height, dtype=np.float32))
        if 'h' in proj.proj4_params:
            h = proj.proj4_params['h']
        else:
            h = proj.to_dict()['h']
        if 'lon_0' in proj.proj4_params:
            lon_0 = proj.proj4_params['lon_0']
        else:
            lon_0 = proj.to_dict()['lon_0']
    lon,lat = ccrs.PlateCarree().transform_points(proj, y*h, x*h).T[:2]
    a = np.deg2rad(lon - lon_0)
    b = np.deg2rad(lat)
    star_zen = np.rad2deg(spherical_angle_add(a, b))
    sat_ang = np.rad2deg(spherical_angle_add(x, y))
    sat_zen = sat_ang + star_zen
    return sat_zen.astype(np.float32)


def get_satazi(area):
    lon, lat = area.get_lonlats()
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        proj = area.to_cartopy_crs()
        if 'lon_0' in proj.proj4_params:
            lon_0 = proj.proj4_params['lon_0']
            print(proj.proj4_params)
        else:
            lon_0 = proj.to_dict()['lon_0']
            print(proj.to_dict())
    azi = sensor_azimuth(lon_0, 0, lon, lat)
    azi = azi.astype(np.float32)
    return azi


def sensor_azimuth(satlon,satlat,pixlon,pixlat):
    xlon = np.deg2rad(pixlon - satlon)
    xlat = np.deg2rad(pixlat - satlat)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        beta = np.arccos( np.cos(xlat) * np.cos(xlon) )
        sine_beta = np.sin(beta)
        sensor_azimuth = np.sin(xlon) / sine_beta
        sensor_azimuth = sensor_azimuth.clip(-1,1)
        sensor_azimuth = np.rad2deg(np.arcsin(sensor_azimuth))
    sensor_azimuth[np.isclose(sine_beta, 0)] = 0.0

    sensor_azimuth[xlat < 0.0] = 180.0 - sensor_azimuth[xlat < 0.0]

    sensor_azimuth[sensor_azimuth < 0.0] += 360.0
    
    sensor_azimuth = sensor_azimuth - 180.0
    return sensor_azimuth


SATZEN_ENCODING = {
    'satellite_zenith_angle':{
        'zlib':True,
        'scale_factor':.1,
        'dtype':'i2',
        '_FillValue':netCDF4.default_fillvals['i2']
    }
}

SATAZI_ENCODING = {
    'satellite_azimuth_angle':{
        'zlib':True,
        'scale_factor':.1,
        'dtype':'i2',
        '_FillValue':netCDF4.default_fillvals['i2']
    }
}


def sample_geometry(sat, dt, grid_shape=(3600, 7200)):
    start = time.time()
    ## Resolve satellite
    for attrs in ALL_SATS:
        if attrs['sat'] == sat:
            break
    else:
        print(f'Unknown satellite {sat}')
        return

    sat_zen_out = make_sample.sample_path(dt, 'satellite_zenith_angle', sat)
    sat_azi_out = make_sample.sample_path(dt, 'satellite_azimuth_angle', sat)
    if sat_zen_out.exists() and sat_azi_out.exists():
        print(f'Already have {sat}')
        return

    reader = attrs['reader']
    # order bands in descending resolution
    ordered_bands = sorted(attrs['res'].items(), key=lambda x:x[1], reverse=True)
    for band,_ in ordered_bands:
        band_dir = band_dir_path(dt, sat, band)
        if band_dir.is_dir():
            files = list(band_dir.glob('*'))
            if len(files) > 0:
                index_band = band
                res = attrs['res'][band]
                index_band = make_sample.get_index_bands(attrs['res'])[res]
                del band
                break
    else:
        print(f'No data for {sat} on {dt}')
        return
    print(f'Using {index_band} for {sat} on {dt}')
    _, _, src_index_nn, dst_index_nn = make_sample.open_index(make_sample.INDEX, sat, index_band)
    print('Reading projection')
    area = get_area(files, reader=reader)
    print('Compute satellite zenith angle')
    sat_zen = get_satzen(area)
    print('Resample satellite zenith angle')
    sat_zen = make_sample.remap_fast_mean(src_index_nn, dst_index_nn, sat_zen, grid_shape)
    print('Compute satellite azimuth angle')
    sat_azi = get_satazi(area)
    rad_azi = np.deg2rad(sat_azi)
    cos_azi = np.cos(rad_azi)
    sin_azi = np.sin(rad_azi)
    print('Resample satellite azimuth angle')
    sat_azi = make_sample.remap_fast_mean(src_index_nn, dst_index_nn, sat_azi, grid_shape)
    print('Save')
    make_sample.save(sat_zen, 'satellite_zenith_angle', sat_zen_out)
    make_sample.save(sat_azi, 'satellite_azimuth_angle', sat_azi_out)
    print(f'Done in {time.time()-start:.1f}s')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--freq', default='30min')
    parser.add_argument('sat')
    parser.add_argument('start')
    parser.add_argument('end', nargs='?', default=None)
    args = parser.parse_args()
    sat = args.sat
    dt = pd.to_datetime(args.start)
    if args.end is not None:
        end = pd.to_datetime(args.end)
        for dt in pd.date_range(dt, end, freq=args.freq):
            print(args.sat, dt)
            try:
                 sample_geometry(sat, dt)
            except Exception as e:
                print(e, flush=True)
            finally:
                pass
    else:
         sample_geometry(sat, dt)
   
