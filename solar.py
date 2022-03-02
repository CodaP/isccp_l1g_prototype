import xarray as xr
import numpy as np
import pandas as pd
from netCDF4 import Dataset
import netCDF4
from tqdm import tqdm
from pathlib import Path
import shutil
from datetime import datetime
from itertools import islice
from make_netcdf import filename

import warnings
from pysolar.solar import get_altitude, get_azimuth

ROOT = Path('final/')


SOLAR_ZENITH_ENCODING = {'solar_zenith_angle':{'zlib':True, 'scale_factor':.1, 'add_offset':0, 'dtype':'i2',
                                  'chunksizes':(1,3600,7200), '_FillValue':netCDF4.default_fillvals['i2']}}

SOLAR_AZIMUTH_ENCODING = {'solar_azimuth_angle':{'zlib':True, 'scale_factor':.1, 'add_offset':0, 'dtype':'i2',
                                  'chunksizes':(1,3600,7200), '_FillValue':netCDF4.default_fillvals['i2']}}


def _get_solzen(ds):
    start_time = pd.to_datetime(ds.start_time.item(), utc=True).to_pydatetime()
    lon,lat = np.meshgrid(ds.longitude.values.ravel(), ds.latitude.values.ravel(), copy=False)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        altitude = get_altitude(lat.ravel(), lon.ravel(), start_time)
    solzen = (90-altitude).reshape(lon.shape)
    
    attrs = {
        'standard_name': 'solar_zenith_angle',
        'units':'degree'
    }
    
    return xr.DataArray(solzen[np.newaxis], dims=['time','latitude','longitude'],
                        coords={'latitude':ds.latitude, 'longitude':ds.longitude, 'start_time':(['time'], ds.start_time),
                                'end_time':(['time'], ds.end_time)
                               },
                        attrs=attrs
                       )


def _get_solazi(ds):
    start_time = pd.to_datetime(ds.start_time.item(), utc=True).to_pydatetime()
    lon,lat = np.meshgrid(ds.longitude.values.ravel(), ds.latitude.values.ravel(), copy=False)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        azimuth = get_azimuth(lat.ravel(), lon.ravel(), start_time)
    solazi = ((azimuth+90)%360).reshape(lon.shape)
    
    attrs = {
        'standard_name': 'solar_azimuth_angle',
        'units':'degree',
        'description':'solar angle for surface observer in degrees clockwise from west',
        'value_range':'0 to 360 degrees'
    }
    
    return xr.DataArray(solazi[np.newaxis], dims=['time','latitude','longitude'],
                        coords={'latitude':ds.latitude, 'longitude':ds.longitude, 'start_time':(['time'], ds.start_time),
                                'end_time':(['time'], ds.end_time)
                               },
                        attrs=attrs
                       )


def get_zen_azi(f):
    ds = xr.open_dataset(f).reset_coords()
    ds = ds[['latitude','longitude','start_time','end_time']]
    ds.close()
    zen = _get_solzen(ds)
    azi = _get_solazi(ds)
    return zen,azi


def main(task_id, num_tasks):
    dirs = ROOT.glob('*/*/*/*')
    dirs = islice(dirs,task_id,None,num_tasks)

    with tqdm(dirs) as bar:
        for d in bar:
            try:
                f = min(d.glob('ISCCP-NG*.nc'))
            except ValueError:
                continue
            print(f, flush=True)
            dt = datetime.strptime(''.join(f.parent.parts[-4:]), '%Y%m%d%H%M')
            #zen_out_fname = f.parent / ('ISCCP-NG_L1g_demo_A1_v1_res_0_10deg__solar_zenith_angle_' + f.name.split('_')[-1])
            zen_out_fname = f.parent / filename('solar_zenith_angle', dt)
            #azi_out_fname = f.parent / ('ISCCP-NG_L1g_demo_A1_v1_res_0_10deg__solar_azimuth_angle_' + f.name.split('_')[-1])
            azi_out_fname = f.parent / filename('solar_azimuth_angle', dt)
            zen_tmp_fname = zen_out_fname.parent / (zen_out_fname.name+'.tmp')
            azi_tmp_fname = azi_out_fname.parent / (azi_out_fname.name+'.tmp')
            if not azi_out_fname.exists() or not zen_out_fname.exists():
                zen,azi = get_zen_azi(f)
                zen_out = zen.to_dataset(name='solar_zenith_angle')
                azi_out = azi.to_dataset(name='solar_azimuth_angle')
                zen_out.to_netcdf(zen_tmp_fname, encoding=SOLAR_ZENITH_ENCODING)
                zen_tmp_fname.rename(zen_out_fname)
                azi_out.to_netcdf(azi_tmp_fname, encoding=SOLAR_AZIMUTH_ENCODING)
                azi_tmp_fname.rename(azi_out_fname)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('task_id',type=int)
    parser.add_argument('max_task_id',type=int)
    args = parser.parse_args()
    main(args.task_id, args.max_task_id+1)


