import numpy as np
import xarray as xr
import netCDF4
import cartopy.crs as ccrs
from tqdm import tqdm

from satpy.readers.utils import get_geostationary_angle_extent
from utils import spherical_angle_add, get_area, ALL_SATS

from collect_l1b import L1B_DIR
import make_sample
from make_sample import GRID_SHAPE
import tempfile

from pathlib import Path
import shutil
import warnings
import time
import os

SATZEN_CACHE = Path('satzen_cache')
SATZEN_CACHE.mkdir(exist_ok=True)
SATAZI_CACHE = Path('satazi_cache')
SATAZI_CACHE.mkdir(exist_ok=True)

def get_satzen(area):
    height, width = area.shape
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        proj = area.to_cartopy_crs()
        xang, yang = get_geostationary_angle_extent(area)
    x,y = np.meshgrid(np.linspace(-xang, xang,width, dtype=np.float32),
                      np.linspace(-yang, yang, height, dtype=np.float32))
    h = proj.proj4_params['h']
    lon,lat = ccrs.PlateCarree().transform_points(proj, y*h, x*h).T[:2]
    a = np.deg2rad(lon - proj.proj4_params['lon_0'])
    b = np.deg2rad(lat)
    star_zen = np.rad2deg(spherical_angle_add(a, b))
    sat_ang = np.rad2deg(spherical_angle_add(x, y))
    sat_zen = sat_ang + star_zen
    return sat_zen.astype(np.float32)


def get_satazi(area):
    lon, lat = area.get_lonlats()
    proj = area.to_cartopy_crs()
    azi = sensor_azimuth(proj.proj4_params['lon_0'], 0, lon, lat)
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


def make_geometry(dt_dir):
    with tqdm(ALL_SATS) as bar:
        for attrs in bar:
            sat = attrs['sat']
            reader = attrs['reader']
            
            files = list((dt_dir / sat / f'temp_11_00um').glob('*'))
            area = get_area(files, reader=reader)
            bar.set_description(f'{sat} satzen')
            sat_zen = get_satzen(area)
            bar.set_description(f'{sat} satazi')
            sat_azi = get_satazi(area)
            
            ds = xr.Dataset()
            ds['satellite_zenith_angle'] = ['y','x'], sat_zen
            out = SATZEN_CACHE / f'{sat}_satellite_zenith_angle.nc'
            bar.set_description(f'saving {out}')
            if out.is_file():
                out.unlink()
            ds.to_netcdf(out, encoding=SATZEN_ENCODING)

            ds = xr.Dataset()
            ds['satellite_azimuth_angle'] = ['y','x'], sat_azi
            out = SATAZI_CACHE / f'{sat}_satellite_azimuth_angle.nc'
            bar.set_description(f'saving {out}')
            if out.is_file():
                out.unlink()
            ds.to_netcdf(out, encoding=SATAZI_ENCODING)


def _composite_geometry(CACHE, k):
    out_nc = make_sample.COMP_CACHE / f'{k}.nc'
    if out_nc.exists():
        print(f'Already have {out_nc}')
        return
    start = time.time()
    composite = xr.DataArray(np.full(GRID_SHAPE, np.nan, dtype=np.float32), dims=['layer','latitude','longitude'])
    with tqdm(ALL_SATS) as bar:
        for attrs in bar:
            sat = attrs['sat']
            reader = attrs['reader']
            res = attrs['res']['temp_11_00um']
            wmo_id = make_sample.WMO_ID[sat]
            cache_file = (CACHE / f'{sat}_{k}.nc')
            ds = xr.open_dataset(cache_file)
            v = ds[k].load().values
            ds.close()
            index_band = make_sample.get_index_bands(attrs['res'])[res]
            src_index, dst_index, src_index_nn, dst_index_nn = make_sample.open_index(make_sample.INDEX, sat, index_band)

            if 'azimuth' in k:
                rad_v = np.deg2rad(v)
                cos_v = np.cos(rad_v)
                sin_v = np.sin(rad_v)
                out_cos_v = make_sample.remap_fast_mean(src_index, dst_index, cos_v, GRID_SHAPE[-2:])
                out_sin_v = make_sample.remap_fast_mean(src_index, dst_index, sin_v, GRID_SHAPE[-2:])
                out = np.rad2deg(np.arctan2(out_sin_v, out_cos_v))
            else:
                out = make_sample.remap_fast_mean(src_index, dst_index, v, GRID_SHAPE[-2:])
            out_nn = make_sample.remap_fast_mean(src_index_nn, dst_index_nn, v, GRID_SHAPE[-2:])

            bar.set_description(f'Compositing {sat} {k}')
            for layer in range(composite.shape[0]):
                # Nearest-neighbor sampling
                mask = (make_sample.WMO_IDS[layer].values == wmo_id) & (make_sample.SAMPLE_MODE[layer].values == 1)
                composite.values[layer, mask] = out_nn[mask]
                # Agg sampling
                mask = (make_sample.WMO_IDS[layer].values  == wmo_id) & (make_sample.SAMPLE_MODE[layer].values == 2)
                composite.values[layer, mask] = out[mask]

    print(f"Saving {out_nc}")
    make_sample.save_netcdf(composite.to_dataset(name=k), out_nc, encoding={k:make_sample.ENCODING})
    end = time.time()
    dur = end - start
    print(f'Took {dur:.1f} sec')

def composite_azimuth():
    k = 'satellite_azimuth_angle'
    cache = SATAZI_CACHE
    _composite_geometry(cache, k)

def composite_zenith():
    k = 'satellite_zenith_angle'
    cache = SATZEN_CACHE
    _composite_geometry(cache, k)
        


if __name__ == '__main__':
    #make_geometry(Path('l1b/2020/07/01/0000/'))
    composite_zenith()

