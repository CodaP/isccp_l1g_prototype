import numpy as np
import pandas as pd
import xarray as xr

from utils import AHI_BANDS, ABI_BANDS, MSG_BANDS, remap_fast_mean, WMO_IDS, ALL_SATS, get_grid
from tqdm import tqdm
import netCDF4
from pathlib import Path
from make_geometry import SATZEN_CACHE
from make_index import get_index_bands, get_max_satzen
from make_sample import SAMPLE_CACHE, INDEX

def get_sorting(sat_comp, grid_shape):
    satzens = xr.DataArray(np.full((len(ALL_SATS), *grid_shape), np.nan, dtype=np.float32), dims=['layer','latitude','longitude'])
    wmo_ids = xr.DataArray(np.full((len(ALL_SATS), *grid_shape), 0, dtype=np.uint16), dims=['layer','latitude','longitude'])
    sample_mode = xr.DataArray(np.full((len(ALL_SATS), *grid_shape), 0, dtype=np.uint8), dims=['layer','latitude','longitude'])
    with tqdm(ALL_SATS) as bar:
        for i,attrs in enumerate(bar):
            sat = attrs['sat']
            if sat not in sat_comp:
                continue
            bar.set_description(f'sat: {sat}')
            wmo_id = WMO_IDS[sat]
            index_band = get_index_bands(attrs['res'])[attrs['res']['temp_11_00um']]
            max_satzen = get_max_satzen(max(attrs['res'].values())/2, 2)
            bar.set_description(f'max satzen: {max_satzen}')
            index_dir = INDEX / sat / f'{index_band}'
            src_index = np.memmap(index_dir / 'src_index.dat', mode='r', dtype=np.uint32)
            dst_index = np.memmap(index_dir / 'dst_index.dat', mode='r', dtype=np.uint32)
            src_index_nn = np.memmap(index_dir / 'src_index_nn.dat', mode='r', dtype=np.uint32)
            dst_index_nn = np.memmap(index_dir / 'dst_index_nn.dat', mode='r', dtype=np.uint32)
            satzen = xr.open_dataset(SATZEN_CACHE / f'{sat}_satellite_zenith_angle.nc')
            nn_satzen = remap_fast_mean(src_index_nn, dst_index_nn, satzen.satellite_zenith_angle.values, grid_shape)
            satzens.values[i,...] = nn_satzen
            wmo_ids.values[i,np.isfinite(nn_satzen)] = wmo_id
            sample_mode.values[i, np.isfinite(nn_satzen)] = 1
            ellip_satzen = remap_fast_mean(src_index, dst_index, satzen.satellite_zenith_angle.values, grid_shape)
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

def get_output_paths(sat_comp):
    paths = {}
    sat_comp_str = '_'.join(sat_comp)
    paths['out_dir'] = SAMPLE_CACHE / sat_comp_str
    paths['wmo_id_f'] = paths['out_dir'] / 'wmo_id.nc'
    paths['satzen_f'] = paths['out_dir'] / 'satellite_zenith_angle.nc'
    paths['sample_mode_f'] = paths['out_dir'] / 'sample_mode.nc'
    return paths


def save_sorting(sat_comp, satzens, wmo_ids, sample_mode):
    
    output_paths = get_output_paths(sat_comp)
    output_paths['out_dir'].mkdir(parents=True, exist_ok=True)
    for f in output_paths.values():
        if f.exists() and not f.is_dir():
            print(f'Overwriting {f}')
            f.unlink()

    wmo_ids.to_dataset(name='wmo_id').to_netcdf(output_paths['wmo_id_f'], encoding={'wmo_id':{'zlib':True}})
    satzens.to_dataset(name='satellite_zenith_angle').to_netcdf(output_paths['satzen_f'],
                                                 encoding={
                                                     'satellite_zenith_angle':{'zlib':True, 'scale_factor':.1,
                                                               'dtype':'i2',
                                                               '_FillValue':netCDF4.default_fillvals['i2']}})
    sample_mode.to_dataset(name='sample_mode').to_netcdf(output_paths['sample_mode_f'],
                                                 encoding={
                                                     'sample_mode':{'_FillValue':0, 'zlib':True}})

def main(sat_comp, grid=None):
    output_paths = get_output_paths(sat_comp)
    if all([f.exists() for f in output_paths.values()]):
        print('All output files already exist. Skipping.')
        return
    if grid is None:
        grid = get_grid()
    grid_shape = grid.shape
    satzens, wmo_ids, sample_mode = get_sorting(sat_comp, grid_shape)
    save_sorting(sat_comp, satzens, wmo_ids, sample_mode)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('sat_comp', type=str)
    args = parser.parse_args()
    sat_comp = sorted(set(args.sat_comp.split(',')))
    main(sat_comp)
