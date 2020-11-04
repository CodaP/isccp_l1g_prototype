import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from tqdm import tqdm
import warnings
import satpy
import pyresample
import sys
import os

os.environ['XRIT_DECOMPRESS_PATH'] = str(Path('xrit/PublicDecompWT/xRITDecompress/xRITDecompress').absolute())

def get_grid(res=.25):
    """
    res: Grid resolution (degree)
    """
    width = 360/res
    height = 180/res
    extent = [-180,-90,180,90]
    pc = pyresample.AreaDefinition('pc','','pc','+proj=latlon +lat_0=0 +lon_0=0',
                                   width=width,
                                   height=height,area_extent=extent)
    return pc

def get_area(files, reader=None):
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
                    name = scene.available_dataset_names()[0]
                    scene.load([name])
                    area = scene[name].area
                    scene.unload()
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        return area

def spherical_angle_add(a, b):
    C = np.pi/2  # a1 and a2 are orthogonal
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        cosc = np.cos(a)*np.cos(b)+abs(np.sin(a)*np.sin(b))*np.cos(C)
        c = np.arccos(cosc)
    return c

AHI_VARIABLES = {
    '01':'refl_00_47um',
    '02':'refl_00_51um',
    '03':'refl_00_65um',
    '04':'refl_00_86um',
    '05':'refl_01_60um',
    '06':'refl_02_20um',
    '07':'temp_03_80um',
    '08':'temp_06_20um',
    '09':'temp_06_70um',
    '10':'temp_07_30um',
    '11':'temp_08_50um',
    '12':'temp_09_70um',
    '13':'temp_10_40um',
    '14':'temp_11_00um',
    '15':'temp_12_00um',
    '16':'temp_13_30um'
}
ABI_VARIABLES = AHI_VARIABLES.copy()
ABI_VARIABLES.update({'02':'refl_00_65um','03':'refl_00_86um','04':'refl_01_38um'})

MSG_VARIABLES = {
    'IR_016':'refl_01_60um',
    'IR_039':'temp_03_80um',
    'IR_087':'temp_08_70um',
    'IR_097':'temp_09_70um',
    'IR_108':'temp_11_00um',
    'IR_120':'temp_12_00um',
    'IR_134':'temp_13_30um',
    'VIS006':'refl_00_65um',
    'VIS008':'refl_00_86um',
    'WV_062':'temp_06_20um',
    'WV_073':'temp_07_30um'
}


ABI_BANDS = {v:k for k,v in ABI_VARIABLES.items()}
AHI_BANDS = {v:k for k,v in AHI_VARIABLES.items()}
MSG_BANDS = {v:k for k,v in MSG_VARIABLES.items()}


ALL_BANDS = set(AHI_BANDS) | set(ABI_BANDS) | set(MSG_BANDS)

ABI_RES = {k:2 for k in ABI_BANDS}
ABI_RES['refl_01_60um'] = 1
ABI_RES['refl_00_86um'] = 1
ABI_RES['refl_00_47um'] = 1
ABI_RES['refl_00_65um'] = 0.5

AHI_RES = {k:2 for k in AHI_BANDS}
AHI_RES['refl_00_47um'] = 1
AHI_RES['refl_00_51um'] = 1
AHI_RES['refl_00_86um'] = 1
AHI_RES['refl_00_65um'] = 0.5


MSG_RES = {k:3 for k in MSG_BANDS}


BAND_NICKNAME = {
 'refl_00_47um': 'Blue',
 'refl_00_51um': 'Green',
 'refl_00_65um': 'Red',
 'refl_00_86um': 'Vegetation',
 'refl_01_38um': 'Cirrus',
 'refl_01_60um': 'Snow/Ice',
 'refl_02_20um': 'Cloud Phase',
 'temp_03_80um': 'Shortwave Window',
 'temp_03_90um': 'Shortwave Window',
 'temp_06_20um': 'Upper-Level Tropospheric Water Vapor',
 'temp_06_70um': 'Mid-Level Tropospheric Water Vapor',
 'temp_07_30um': 'Lower-level Water Vapor',
 'temp_08_50um': 'Cloud-Top Phase',
 'temp_08_70um': 'Total Water',
 'temp_09_70um': 'Ozone Band',
 'temp_10_40um': 'Clean IR Longwave Window',
 'temp_11_00um': 'IR Longwave Window Band',
 'temp_12_00um': 'Dirty Longwave Window',
 'temp_13_30um': 'CO2 longwave infrared'
}

BAND_CLASS = {
 'refl_00_47um': 'visible',
 'refl_00_51um': 'visible',
 'refl_00_65um': 'visible',
 'refl_00_86um': 'near-infrared',
 'refl_01_38um': 'near-infrared',
 'refl_01_60um': 'near-infrared',
 'refl_02_20um': 'near-infrared',
 'temp_03_80um': 'infrared',
 'temp_03_90um': 'infrared',
 'temp_06_20um': 'infrared',
 'temp_06_70um': 'infrared',
 'temp_07_30um': 'infrared',
 'temp_08_50um': 'infrared',
 'temp_08_70um': 'infrared',
 'temp_09_70um': 'infrared',
 'temp_10_40um': 'infrared',
 'temp_11_00um': 'infrared',
 'temp_12_00um': 'infrared',
 'temp_13_30um': 'infrared'}


STATS_BANDS = {
    'temp_11_00um',
    'refl_00_65um'
}
STATS_FUNCS = ['mean','var','count','min','max']

def remap_with_stats(src_index, dst_index, v, shape, funcs=STATS_FUNCS):
    a = pd.Series(v.ravel()[src_index], index=dst_index)
    resample = a.groupby(a.index).agg(funcs)
    out = {}
    for k in funcs:
        out[k] = np.full(shape, np.nan, dtype=np.float32)
        out[k].ravel()[resample[k].index] = resample[k].values
    return out

def remap_fast_mean(src_index, dst_index, v, shape):
    dst_index = dst_index.astype(np.int64)
    weights = v.ravel()[src_index]
    counts = np.bincount(dst_index, weights=np.isfinite(weights), minlength=np.prod(shape))
    mask = counts > 0
    sums = np.bincount(dst_index, weights=np.nan_to_num(weights, nan=0.0), minlength=np.prod(shape))
    out = np.full(shape, np.nan, dtype=np.float32)
    out.ravel()[mask] = sums[mask]/counts[mask]
    return out


SAT_NAMES = {
    'g16':'GOES-16',
    'g17':'GOES-17',
    'h8':'Himawari-8',
    'm8':'Meteosat-8',
    'm11':'Meteosat-11'
}
WMO_IDS = {
    'g16':152,
    'g17':664,
    'h8':167,
    'm8':684,
    'm11':305
}

_bands = {'g':ABI_BANDS,'h':AHI_BANDS,'m':MSG_BANDS}
_res = {'g':ABI_RES,'h':AHI_RES, 'm':MSG_RES}
_readers = {'g':'abi_l1b', 'h':'ahi_hsd', 'm':'seviri_l1b_hrit'}

ALL_SATS = [
    {'sat':sat,'wmo_id':WMO_IDS[sat],'name':SAT_NAMES[sat],'bands': _bands[sat[0]], 'res':_res[sat[0]],
    'reader':_readers[sat[0]]}
            for sat in ['g16','g17','h8','m8','m11']]
    
