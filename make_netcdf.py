from pathlib import Path
import numpy as np
import xarray as xr

from datetime import datetime, timedelta
import json

import utils
import netCDF4

def default_attrs():
    attrs = {}
    for k in utils.ALL_BANDS:
        d = {}
        if k in utils.AHI_BANDS:
            d['ahi_band_number'] = utils.AHI_BANDS[k]
            d['ahi_original_nadir_resolution_km'] = utils.AHI_RES[k]
        if k in utils.ABI_BANDS:
            d['abi_band_number'] = utils.ABI_BANDS[k]
            d['abi_original_nadir_resolution_km'] = utils.ABI_RES[k]
        d['band_nickname'] = utils.BAND_NICKNAME[k]
        d['central_wavelength_um'] = utils.BAND_CENTRAL_WAV[k]
        d['em_class'] = utils.BAND_CLASS[k]
        if k.startswith('temp_'):
            d['units'] = 'K'
            d['standard_name'] = 'brightness_temperature'
            d['gsics_calibration'] = json.dumps({})
        elif k.startswith('refl_'):
            d['units'] = '%'
            d['standard_name'] = 'toa_bidirectional_reflectance'
            d['gsics_calibration'] = json.dumps({})
        attrs[k] = d

    attrs['wmo_id'] = {
        'long_name':'WMO id for satellite used in pixel',
        'satellite_names':';'.join(f'{v}={utils.SAT_NAMES[k]}' for k,v in utils.WMO_IDS.items())
    }

    attrs['satellite_zenith_angle'] = {
        'long_name':'satellite zenith angle',
        'standard_name':'satellite zenith angle',
        'units':'degrees'
    }

    attrs['satellite_azimuth_angle'] = {
        'long_name':'satellite azimuth angle',
        'standard_name':'satellite azimuth angle',
        'units':'degrees',
        'description': 'satellite angle for surface observer in degrees clockwise from north',
        'value_range': '-180 to 180 degrees'
    }

    attrs['sample_mode'] = {
        'long_name':'data sampling mode',
        'flag_values':[1,2],
        'flag_meanings':"nearest-neighbor constant-footprint-area"
    }
    
    attrs['pixel_time'] = {
        'long_name':'approximate scan time',
        'standard_name':'time',
    }
    attrs['solar_azimuth_angle'] = {
        'standard_name': 'solar_azimuth_angle',
        'units':'degree',
        'description':'solar angle for surface observer in degrees clockwise from north',
        'value_range':'-180 to 180 degrees'
    }
    attrs['solar_zenith_angle'] = {
        'standard_name': 'solar_zenith_angle',
        'units':'degree',
        'description':'solar angle for surface observer in degrees from zenith',
        'value_range':'0 to 180 degrees'
    }
    return attrs


def add_time(ds, dt, encoding):
    start_dt = dt
    end_dt = start_dt + timedelta(minutes=10)
    ds = ds.expand_dims('time')
    ds['start_time'] = ['time'], [start_dt]
    ds['start_time'].attrs['description'] = 'time at start of window for data inclusion'
    ds['end_time'] = ['time'], [end_dt]
    ds['end_time'].attrs['description'] = 'time at end of window for data inclusion'
    ds = ds.set_coords(['start_time','end_time'])
    encoding['start_time'] = {'units':'seconds since 1970-01-01'}
    encoding['end_time'] = {'units':'seconds since 1970-01-01'}
    return ds


def default_encoding(grid_shape):
    encoding = {}
    bands = utils.ALL_BANDS.copy()
    for band in utils.STATS_BANDS:
        for func in utils.STATS_FUNCS:
            if func != 'mean':
                bands.add(f'{band}_{func}')
    for k in bands:
        if k.startswith('refl'):
            encoding[k] = {
                'zlib':True,
                'scale_factor':.25, 
                'add_offset':50.0,
                'dtype':'i2',
                '_FillValue':netCDF4.default_fillvals['i2'],
                'chunksizes':(1,1,*grid_shape),
                'shuffle':False,
                'complevel':1
            }
        elif k.startswith('temp'):
            encoding[k] = {
                'zlib':True,
                'scale_factor':.01,
                'add_offset':50.0,
                'dtype':'i2',
                '_FillValue':netCDF4.default_fillvals['i2'],
                'chunksizes':(1,1,*grid_shape),
                'shuffle':False,
                'complevel':1
            }
        else:
            print(k)
        if k.endswith('_count'):
            encoding[k] = {
                'zlib':True,
                'dtype':'i1',
                '_FillValue':netCDF4.default_fillvals['i1'],
                'chunksizes':(1,1,*grid_shape),
                'shuffle':False,
                'complevel':1
            }
        elif k.endswith('_std'):
            encoding[k]['add_offset'] = 0.0
    for k in ['latitude','longitude']:
        encoding[k] = {
            'zlib':False,
            'dtype':'f8',
            '_FillValue':netCDF4.default_fillvals['f8'],
            'shuffle':False,
        }
    encoding['pixel_time'] = {
        'zlib':True,
        'dtype':'i2',
        '_FillValue':netCDF4.default_fillvals['i2'],
        'chunksizes':(1,1,*grid_shape),
        'shuffle':False,
        'complevel':1
    }
    encoding['satellite_zenith_angle'] = {
        'zlib':True,
        'scale_factor':.1,
        'dtype':'i2',
        '_FillValue':netCDF4.default_fillvals['i2'],
        'chunksizes':(1,1,*grid_shape),
        'shuffle':False,
        'complevel':1
    }
    encoding['satellite_azimuth_angle'] = {
        'zlib':True,
        'scale_factor':.1,
        'dtype':'i2',
        '_FillValue':netCDF4.default_fillvals['i2'],
        'chunksizes':(1,1,*grid_shape),
        'shuffle':False,
        'complevel':1
    }
    encoding['solar_zenith_angle'] = {
        'zlib':True,
        'scale_factor':.1,
        'dtype':'i2',
        '_FillValue':netCDF4.default_fillvals['i2'],
        'chunksizes':(1,*grid_shape),
        'shuffle':False,
        'complevel':1
    }
    encoding['solar_azimuth_angle'] = {
        'zlib':True,
        'scale_factor':.1,
        'dtype':'i2',
        '_FillValue':netCDF4.default_fillvals['i2'],
        'chunksizes':(1,*grid_shape),
        'shuffle':False,
        'complevel':1
    }
    encoding['wmo_id'] = {
        'zlib':True,
        'dtype': 'i2',
        '_FillValue':netCDF4.default_fillvals['i2'],
        'chunksizes':(1,1,*grid_shape),
        'complevel':1,
        'shuffle':False,
    }
    return encoding


def rewrite_nc(f, out_root, dt, lat, lon):
    ds = xr.open_dataset(f)
    k = next(iter(ds.data_vars))
    ds.close()
    if k == 'satzen':
        return rewrite_satzen(f, out_root, dt, lat, lon)
    elif k == 'satazi':
        return rewrite_satazi(f, out_root, dt, lat, lon)
    elif k == 'pixel_time':
        return rewrite_pixel_time(f, out_root, dt, lat, lon)
    elif k == 'wmo_id':
        return rewrite_wmo_id(f, out_root, dt, lat, lon)
    else:
        return rewrite_nc_general(f, out_root, dt, lat, lon)


def filename(k, dt):
    #return f"{k}_{dt.strftime('%Y%m%dT%H%M')}.nc"
    return dt.strftime(f"ISCCP-NG_L1g_demo_v2_res_0_05deg__{k}__%Y%m%dT%H%M.nc")

def make_output_dir(out_root, dt):
    out_dir = out_root / dt.strftime('%Y') / dt.strftime('%m') / dt.strftime('%d') / dt.strftime('%H%M')
    out_dir.mkdir(exist_ok=True, parents=True)
    return out_dir


def set_latlon(ds, lat, lon):
    ds['latitude'] = ['latitude'], lat
    ds['longitude'] = ['longitude'], lon

    ds['longitude'].attrs['standard_name'] = 'longitude'
    ds['longitude'].attrs['units']='degree_east'

    ds['latitude'].attrs['standard_name'] = 'latitude'
    ds['latitude'].attrs['units']='degree_north'


def rewrite_nc_general(f, out_root, dt, lat, lon):
    out_dir = make_output_dir(out_root, dt)

    ds = xr.open_dataset(f)
    k = next(iter(ds.data_vars))
    out = out_dir / filename(k, dt)
    if out.exists():
        return out
    grid_shape = ds[k].shape[-2:]

    set_latlon(ds,lat,lon)

    attrs = default_attrs()
    ds[k].attrs.update(attrs.get(k,{}))

    encoding = default_encoding(grid_shape)
    ds = add_time(ds, dt, encoding)

    ds.to_netcdf(out, encoding={k:v for k,v in encoding.items() if k in ds})
    return out


def rewrite_wmo_id(f, out_root, dt, lat, lon):
    out_dir = make_output_dir(out_root, dt)
    out = out_dir / filename('wmo_id', dt)
    if out.exists():
        return out

    ds = xr.open_dataset(f)
    grid_shape = ds['wmo_id'].shape[-2:]

    set_latlon(ds,lat,lon)

    attrs = default_attrs()
    ds['wmo_id'].attrs.update(attrs.get('wmo_id',{}))

    encoding = default_encoding(grid_shape)
    encoding['wmo_id'] = {'dtype':'u2',
                'zlib':True,
                '_FillValue':netCDF4.default_fillvals['u2'],
                'chunksizes':(1,1,*grid_shape),
                'shuffle':False,
                'complevel':1}
    ds = add_time(ds, dt, encoding)

    ds.to_netcdf(out, encoding={k:v for k,v in encoding.items() if k in ds})
    return out


def rewrite_satazi(f, out_root, dt, lat, lon):
    out_dir = make_output_dir(out_root, dt)
    out = out_dir / filename('satellite_azimuth_angle',dt)
    if out.exists():
        return out

    ds = xr.open_dataset(f)
    grid_shape = ds['satellite_azimuth_angle'].shape[-2:]

    set_latlon(ds,lat,lon)

    attrs = default_attrs()
    ds['satellite_azimuth_angle'].attrs.update(attrs.get('satellite_azimuth_angle',{}))

    encoding = default_encoding(grid_shape)
    encoding['satellite_azimuth_angle'] = {
                'zlib':True,
                'scale_factor':.125, 
                'dtype':'i2',
                '_FillValue':netCDF4.default_fillvals['i2'],
                'chunksizes':(1,1,*grid_shape),
                'shuffle':False,
                'complevel':1
                }
    ds = add_time(ds, dt, encoding)

    ds.to_netcdf(out, encoding={k:v for k,v in encoding.items() if k in ds})
    return out


def rewrite_satzen(f, out_root, dt, lat, lon):
    out_dir = make_output_dir(out_root, dt)
    out = out_dir / filename('satellite_zenith_angle',dt)
    if out.exists():
        return out

    ds = xr.open_dataset(f)
    grid_shape = ds['satellite_zenith_angle'].shape[-2:]

    set_latlon(ds,lat,lon)

    attrs = default_attrs()
    ds['satellite_zenith_angle'].attrs.update(attrs.get('satellite_zenith_angle',{}))

    encoding = default_encoding(grid_shape)
    encoding['satellite_zenith_angle'] = {
                'zlib':True,
                'scale_factor':.125, 
                'dtype':'i2',
                '_FillValue':netCDF4.default_fillvals['i2'],
                'chunksizes':(1,1,*grid_shape),
                'shuffle':False,
                'complevel':1
                }
    ds = add_time(ds, dt, encoding)

    ds.to_netcdf(out, encoding={k:v for k,v in encoding.items() if k in ds})
    return out


def rewrite_pixel_time(f, out_root, dt, lat, lon):
    out_dir = make_output_dir(out_root, dt)
    out = out_dir / filename('pixel_time',dt)
    if out.exists():
        return out

    ds = xr.open_dataset(f)
    grid_shape = ds['pixel_time'].shape[-2:]

    set_latlon(ds,lat,lon)

    attrs = default_attrs()
    ds['pixel_time'].attrs.update(attrs.get('pixel_time',{}))
    ds['pixel_time'].attrs['units'] = dt.strftime('seconds since %Y-%m-%d')

    encoding = default_encoding(grid_shape)
    encoding['pixel_time'] = {
                'zlib':True,
                'dtype':'i2',
                '_FillValue':netCDF4.default_fillvals['i2'],
                'chunksizes':(1,1,*grid_shape),
                'shuffle':False,
                'complevel':1
                }
    ds = add_time(ds, dt, encoding)

    ds.to_netcdf(out, encoding={k:v for k,v in encoding.items() if k in ds})
    return out

