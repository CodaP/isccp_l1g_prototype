import numpy as np
import pandas as pd
import xarray as xr

from utils import AHI_BANDS, ABI_BANDS, MSG_BANDS, remap, WMO_IDS
from tqdm import tqdm
import netCDF4
from pathlib import Path
from make_geometry import SATZEN_CACHE

INDEX = Path('index')
COMP_CACHE = Path('composite_cache')
COMP_CACHE.mkdir(exist_ok=True)

def get_sorting(grid_shape):
    
    sats = [('g16',ABI_BANDS),('g17', ABI_BANDS),('h8', AHI_BANDS), ('m8',MSG_BANDS), ('m11',MSG_BANDS)]
    satzens = xr.DataArray(np.full((len(sats), *grid_shape), np.nan, dtype=np.float32), dims=['layer','latitude','longitude'])
    wmo_ids = xr.DataArray(np.full((len(sats), *grid_shape), np.nan, dtype=np.uint16), dims=['layer','latitude','longitude'])
    with tqdm(sats) as bar:
        for i,(sat, band_lookup) in enumerate(bar):
            wmo_id = WMO_IDS[sat]
            index_band = band_lookup['temp_11_00um']
            index_dir = INDEX / sat / f'{index_band}'
            src_index = np.memmap(index_dir / 'src_index.dat', mode='r', dtype=np.uint64)
            dst_index = np.memmap(index_dir / 'dst_index.dat', mode='r', dtype=np.uint64)
            src_index_nn = np.memmap(index_dir / 'src_index_nn.dat', mode='r', dtype=np.uint64)
            dst_index_nn = np.memmap(index_dir / 'dst_index_nn.dat', mode='r', dtype=np.uint64)
            satzen = xr.open_dataset(SATZEN_CACHE / f'{sat}_satzen.nc')
            nn_satzen = remap(src_index_nn, dst_index_nn, satzen.satzen.values, grid_shape)
            satzens.values[i,...] = nn_satzen
            wmo_ids.values[i,...] = wmo_id
            ellip_satzen = remap(src_index, dst_index, satzen.satzen.values, grid_shape)
            mask = np.isfinite(ellip_satzen)
            satzens.values[i,mask] = ellip_satzen[mask]
            wmo_ids.values[i,mask] = (wmo_id | 0x1000)
            
    argsort = satzens.fillna(900).argsort(axis=0)
    satzens_sort = xr.DataArray(np.take_along_axis(satzens.values, argsort, 0), dims=satzens.dims)
    wmo_ids_sort = xr.DataArray(np.take_along_axis(wmo_ids.values, argsort, 0), dims=wmo_ids.dims)
    return satzens_sort, wmo_ids_sort


def save_sorting(satzens, wmo_ids):
    wmo_ids.to_dataset(name='wmo_id').to_netcdf(COMP_CACHE / 'wmo_id.nc', encoding={'wmo_id':{'zlib':True}})
    satzens.to_dataset(name='satzen').to_netcdf(COMP_CACHE / 'satzen.nc',
                                                 encoding={
                                                     'satzen':{'zlib':True, 'scale_factor':.1,
                                                               'dtype':'i2',
                                                               '_FillValue':netCDF4.default_fillvals['i2']}})
    
def main(grid_shape=(3600,7200)):
    satzens, wmo_ids = get_sorting(grid_shape)
    save_sorting(satzens, wmo_ids)

if __name__ == '__main__':
    main()
