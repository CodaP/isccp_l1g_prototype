import numpy as np
import xarray as xr
import netCDF4
import cartopy.crs as ccrs
from tqdm import tqdm

from satpy.readers.utils import get_geostationary_angle_extent
from utils import spherical_angle_add, ABI_BANDS, AHI_BANDS, get_area

from collect_l1b import L1B_DIR

from pathlib import Path
import warnings

SATZEN_CACHE = Path('satzen_cache')
SATZEN_CACHE.mkdir(exist_ok=True)

def get_satzen(area):
    height, width = area.shape
    xang, yang = get_geostationary_angle_extent(area)
    x,y = np.meshgrid(np.linspace(-xang, xang,width, dtype=np.float32),
                      np.linspace(-yang, yang, height, dtype=np.float32))
    proj = area.to_cartopy_crs()
    h = proj.proj4_params['h']
    lon,lat = ccrs.PlateCarree().transform_points(proj, y*h, x*h).T[:2]
    a = np.deg2rad(lon - proj.proj4_params['lon_0'])
    b = np.deg2rad(lat)
    star_zen = np.rad2deg(spherical_angle_add(a, b))
    sat_ang = np.rad2deg(spherical_angle_add(x, y))
    sat_zen = sat_ang + star_zen
    return sat_zen.astype(np.float32)


ENCODING = {
    'satzen':{
        'zlib':True,
        'scale_factor':.1,
        'dtype':'i2',
        '_FillValue':netCDF4.default_fillvals['i2']
    }
}


def make_geometry(dt_dir):
    rows = [
            ('g16', ABI_BANDS, 'abi_l1b'),
            ('g17', ABI_BANDS, 'abi_l1b'),
            ('h8', AHI_BANDS, 'ahi_hsd')]
    with tqdm(rows) as bar:
        for sat, band_lookup, reader in bar:
            band = band_lookup['temp_11_00um']
            files = list((dt_dir / sat / f'{band:02d}').glob('*'))
            area = get_area(files, reader=reader)
            sat_zen = get_satzen(area)

            ds = xr.Dataset()
            ds['satzen'] = ['y','x'], sat_zen
            out = SATZEN_CACHE / f'{sat}_satzen.nc'
            if out.is_file():
                out.unlink()
            ds.to_netcdf(out, encoding=ENCODING)
        
