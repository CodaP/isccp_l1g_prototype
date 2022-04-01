import numpy as np
import pandas as pd
import xarray as xr

from utils import AHI_BANDS, ABI_BANDS, MSG_BANDS, remap_fast_mean, WMO_IDS, ALL_SATS, get_grid
from tqdm import tqdm
import netCDF4
from pathlib import Path
from make_geometry import SATZEN_CACHE
from make_index import get_index_bands, get_max_satzen

INDEX = Path('index')
COMP_CACHE = Path('composite_cache')
COMP_CACHE.mkdir(exist_ok=True)

def get_sorting(grid_shape):
    satzens = xr.DataArray(np.full((len(ALL_SATS), *grid_shape), np.nan, dtype=np.float32), dims=['layer','latitude','longitude'])
    wmo_ids = xr.DataArray(np.full((len(ALL_SATS), *grid_shape), 0, dtype=np.uint16), dims=['layer','latitude','longitude'])
    sample_mode = xr.DataArray(np.full((len(ALL_SATS), *grid_shape), 0, dtype=np.uint8), dims=['layer','latitude','longitude'])
    with tqdm(ALL_SATS) as bar:
        for i,attrs in enumerate(bar):
            sat = attrs['sat']
            wmo_id = WMO_IDS[sat]
            index_band = get_index_bands(attrs['res'])[attrs['res']['temp_11_00um']]
            max_satzen = get_max_satzen(max(attrs['res'].values())/2, 2)
            bar.set_description(f'max satzen: {max_satzen}')
            index_dir = INDEX / sat / f'{index_band}'
            src_index = np.memmap(index_dir / 'src_index.dat', mode='r', dtype=np.uint32)
            dst_index = np.memmap(index_dir / 'dst_index.dat', mode='r', dtype=np.uint32)
            src_index_nn = np.memmap(index_dir / 'src_index_nn.dat', mode='r', dtype=np.uint32)
            dst_index_nn = np.memmap(index_dir / 'dst_index_nn.dat', mode='r', dtype=np.uint32)
            satzen = xr.open_dataset(SATZEN_CACHE / f'{sat}_satzen.nc')
            nn_satzen = remap_fast_mean(src_index_nn, dst_index_nn, satzen.satellite_zenith.values, grid_shape)
            satzens.values[i,...] = nn_satzen
            wmo_ids.values[i,np.isfinite(nn_satzen)] = wmo_id
            sample_mode.values[i, np.isfinite(nn_satzen)] = 1
            ellip_satzen = remap_fast_mean(src_index, dst_index, satzen.satellite_zenith.values, grid_shape)
            mask = np.isfinite(ellip_satzen) & (ellip_satzen < max_satzen)
            satzens.values[i,mask] = ellip_satzen[mask]
            wmo_ids.values[i,mask] = wmo_id
            sample_mode.values[i,mask] = 2
            
    argsort = satzens.fillna(900).argsort(axis=0)
    satzens_sort = xr.DataArray(np.take_along_axis(satzens.values, argsort, 0), dims=satzens.dims)
    wmo_ids_sort = xr.DataArray(np.take_along_axis(wmo_ids.values, argsort, 0), dims=wmo_ids.dims)
    sample_mode_sort = xr.DataArray(np.take_along_axis(sample_mode.values, argsort, 0), dims=sample_mode.dims)
    
    # Prune
    layer_mask = (sample_mode_sort>0).any(dim=['latitude','longitude'])
    satzens_sort = satzens_sort.sel(layer=layer_mask)
    wmo_ids_sort = wmo_ids_sort.sel(layer=layer_mask)
    sample_mode_sort = sample_mode_sort.sel(layer=layer_mask)
    
    return satzens_sort, wmo_ids_sort, sample_mode_sort


def save_sorting(satzens, wmo_ids, sample_mode):
    wmo_ids.to_dataset(name='wmo_id').to_netcdf(COMP_CACHE / 'wmo_id.nc', encoding={'wmo_id':{'zlib':True}})
    satzens.to_dataset(name='satellite_zenith_angle').to_netcdf(COMP_CACHE / 'satzen.nc',
                                                 encoding={
                                                     'satzen':{'zlib':True, 'scale_factor':.1,
                                                               'dtype':'i2',
                                                               '_FillValue':netCDF4.default_fillvals['i2']}})
    
    sample_mode.to_dataset(name='sample_mode').to_netcdf(COMP_CACHE / 'sample_mode.nc',
                                                 encoding={
                                                     'sample_mode':{'_FillValue':0, 'zlib':True}})
def main(grid=None):
    if grid is None:
        grid = get_grid()
    grid_shape = grid.shape
    satzens, wmo_ids, sample_mode = get_sorting(grid_shape)
    save_sorting(satzens, wmo_ids, sample_mode)

if __name__ == '__main__':
    main()
