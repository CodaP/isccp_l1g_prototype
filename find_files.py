from pathlib import Path
from datetime import datetime

ROOT = Path('dat/final')

def band_list():
    bands = {'temp_09_70um', 'refl_00_65um', 'satellite_zenith_angle', 'temp_08_60um', 'refl_00_65um_count', 'wmo_id', 'refl_01_38um', 'refl_00_65um_max', 'solar_zenith_angle', 'satellite_azimuth_angle', 'temp_07_30um', 'temp_12_00um', 'refl_00_86um', 'temp_11_00um_std', 'refl_00_47um', 'refl_00_65um_min', 'pixel_time', 'temp_11_00um', 'temp_03_80um', 'refl_00_65um_std', 'temp_11_00um_count', 'temp_06_70um', 'refl_00_51um', 'refl_02_20um', 'refl_01_60um', 'temp_10_40um', 'temp_11_00um_max', 'solar_azimuth_angle', 'sample_mode', 'temp_06_20um', 'temp_13_30um', 'temp_11_00um_min'}
    return bands

def extract_var(fname):
    """
    >>> extract_var('ISCCP-NG_L1g_demo_v2_res_0_05deg__wmo_id__20200830T2330.nc')
    'wmo_id'
    """
    part = fname.split('__')[1]
    return part
    #return '_'.join(part.split('_')[:-1])


def gen_path(band, dt, root=ROOT):
    from make_netcdf import filename
    d = root / dt.strftime('%Y') / dt.strftime('%m') / dt.strftime('%d') / dt.strftime('%H%M')
    f = d / filename(band, dt)
    return f


def walk_files():
    return ROOT.glob('*/*/*/*/*.nc')


def extract_dt(path):
    yyyymmddHHMM = ''.join(path.parts[-5:-1])
    return datetime.strptime(yyyymmddHHMM, '%Y%m%d%H%M')


def all_files():
    for f in walk_files():
        k = extract_var(f.name)
        dt = extract_dt(f)
        yield dt, k, f


