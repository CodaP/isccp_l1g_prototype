import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from tqdm import tqdm
import warnings
import satpy
import pyresample


def get_grid(res):
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
        scene = satpy.Scene(
            files, reader=reader
            )
        name = scene.available_dataset_names()[0]
        scene.load([name])
        area = scene[name].area
        scene.unload()
        return area

def spherical_angle_add(a, b):
    C = np.pi/2  # a1 and a2 are orthogonal
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        cosc = np.cos(a)*np.cos(b)+abs(np.sin(a)*np.sin(b))*np.cos(C)
        c = np.arccos(cosc)
    return c

AHI_VARIABLES = {
    1:'refl_00_47um',
    2:'refl_00_51um',
    3:'refl_00_65um',
    4:'refl_00_86um',
    5:'refl_01_60um',
    6:'refl_02_20um',
    7:'temp_03_80um',
    8:'temp_06_20um',
    9:'temp_06_70um',
    10:'temp_07_30um',
    11:'temp_08_50um',
    12:'temp_09_70um',
    13:'temp_10_40um',
    14:'temp_11_00um',
    15:'temp_12_00um',
    16:'temp_13_30um'
}
ABI_VARIABLES = AHI_VARIABLES.copy()
ABI_VARIABLES.update({2:'refl_00_65um',3:'refl_00_86um',4:'refl_01_38um'})


ABI_BANDS = {v:k for k,v in ABI_VARIABLES.items()}
AHI_BANDS = {v:k for k,v in AHI_VARIABLES.items()}


ALL_CHANNELS = set(AHI_BANDS) | set(ABI_BANDS)

ABI_RES = {k:2 for k in ABI_BANDS.values()}
ABI_RES[5] = 1
ABI_RES[3] = 1
ABI_RES[1] = 1
ABI_RES[2] = 0.5

AHI_RES = {k:2 for k in AHI_BANDS.values()}
AHI_RES[1] = 1
AHI_RES[2] = 1
AHI_RES[4] = 1
AHI_RES[3] = 0.5

CHANNEL_NICKNAME = {
 'refl_00_47um': 'Blue',
 'refl_00_51um': 'Green',
 'refl_00_65um': 'Red',
 'refl_00_86um': 'Vegetation',
 'refl_01_38um': 'Cirrus',
 'refl_01_60um': 'Snow/Ice',
 'refl_02_20um': 'Cloud Phase',
 'temp_03_80um': 'Shortwave Window',
 'temp_06_20um': 'Upper-Level Tropospheric Water Vapor',
 'temp_06_70um': 'Mid-Level Tropospheric Water Vapor',
 'temp_07_30um': 'Lower-level Water Vapor',
 'temp_08_50um': 'Cloud-Top Phase',
 'temp_09_70um': 'Ozone Band',
 'temp_10_40um': 'Clean IR Longwave Window',
 'temp_11_00um': 'IR Longwave Window Band',
 'temp_12_00um': 'Dirty Longwave Window',
 'temp_13_30um': 'CO2 longwave infrared'
}

CHANNEL_CLASS = {
 'refl_00_47um': 'visible',
 'refl_00_51um': 'visible',
 'refl_00_65um': 'visible',
 'refl_00_86um': 'near-infrared',
 'refl_01_38um': 'near-infrared',
 'refl_01_60um': 'near-infrared',
 'refl_02_20um': 'near-infrared',
 'temp_03_80um': 'infrared',
 'temp_06_20um': 'infrared',
 'temp_06_70um': 'infrared',
 'temp_07_30um': 'infrared',
 'temp_08_50um': 'infrared',
 'temp_09_70um': 'infrared',
 'temp_10_40um': 'infrared',
 'temp_11_00um': 'infrared',
 'temp_12_00um': 'infrared',
 'temp_13_30um': 'infrared'}


def remap(src_index, dst_index, v, shape):
    a = pd.Series(v.ravel()[src_index], index=dst_index)
    resample = a.groupby(a.index).mean()
    out = np.full(shape, np.nan, dtype=np.float32)
    out.ravel()[resample.index] = resample.values
    return out

def remap(src_index, dst_index, v, shape):
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
    'h8':'Himawari-8'
}
WMO_IDS = {
    'g16':152,
    'g17':664,
    'h8':167
}

    
