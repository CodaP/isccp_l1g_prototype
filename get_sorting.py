import numpy as np
import pandas as pd
import xarray as xr

from utils import AHI_BANDS, ABI_BANDS, MSG_BANDS, remap_fast_mean, WMO_IDS, ALL_SATS, get_grid
from tqdm import tqdm
import netCDF4
from pathlib import Path
from make_index import get_index_bands
from make_sample import INDEX, sample_path, open_index
from make_composite import read_dat

COMP_DIR = Path('dat/comp').resolve()
COMP_DIR.mkdir(exist_ok=True)

def get_sorting(dt, sat_comp, grid_shape):
    satzens = xr.DataArray(np.full((len(sat_comp), *grid_shape), np.nan, dtype=np.float32), dims=['layer','latitude','longitude'])
    wmo_ids = xr.DataArray(np.full((len(sat_comp), *grid_shape), 0, dtype=np.uint16), dims=['layer','latitude','longitude'])
    sample_mode = xr.DataArray(np.full((len(sat_comp), *grid_shape), 0, dtype=np.uint8), dims=['layer','latitude','longitude'])
    with tqdm(sat_comp) as bar:
        for i,sat in enumerate(bar):
            for attrs in ALL_SATS:
                if sat == attrs['sat']:
                    break
            else:
                raise ValueError(f'{sat} is not recognized')
            bar.set_description(f'sat: {sat}')
            wmo_id = WMO_IDS[sat]
            f = sample_path(dt, 'satellite_zenith_angle', sat)
            satzen = read_dat(f, 'satellite_zenith_angle', grid_shape=grid_shape)
            satzens.values[i,...] = satzen.astype(np.float32).filled(np.nan)
            wmo_ids.values[i,...] = np.where(np.ma.getmaskarray(satzen), 0, wmo_id)
            index_band = get_index_bands(attrs['res'])[attrs['res']['temp_11_00um']]
            _, dst_index, _, dst_index_nn = open_index(INDEX, sat, index_band)
            sample_mode.values[i].ravel()[dst_index_nn] = 2
            sample_mode.values[i,np.ma.getmaskarray(satzen)] = 0
            sample_mode.values[i].ravel()[dst_index] = 1
            
    argsort = satzens.argsort(axis=0)
    wmo_ids_sort = xr.DataArray(np.take_along_axis(wmo_ids.values, argsort, 0), dims=wmo_ids.dims)
    sample_mode_sort = xr.DataArray(np.take_along_axis(sample_mode.values, argsort, 0), dims=sample_mode.dims)
    
    # Prune
    layer_mask = (sample_mode_sort>0).any(dim=['latitude','longitude'])
    print(f'pruning {len(layer_mask)} layers down to {layer_mask.sum().item()} layers')
    wmo_ids_sort = wmo_ids_sort.sel(layer=layer_mask)
    sample_mode_sort = sample_mode_sort.sel(layer=layer_mask)
    
    return wmo_ids_sort, sample_mode_sort

def get_output_paths(sat_comp):
    paths = {}
    sat_comp_str = '_'.join(sat_comp)
    paths['out_dir'] = COMP_DIR / sat_comp_str
    paths['wmo_id_f'] = paths['out_dir'] / 'wmo_id.nc'
    paths['sample_mode_f'] = paths['out_dir'] / 'sample_mode.nc'
    return paths


def save_sorting(sat_comp, wmo_ids, sample_mode):
    
    output_paths = get_output_paths(sat_comp)
    output_paths['out_dir'].mkdir(parents=True, exist_ok=True)
    for f in output_paths.values():
        if f.exists() and not f.is_dir():
            print(f'Overwriting {f}')
            f.unlink()

    wmo_ids.to_dataset(name='wmo_id').to_netcdf(output_paths['wmo_id_f'], encoding={'wmo_id':{'zlib':True}})
    sample_mode.to_dataset(name='sample_mode').to_netcdf(output_paths['sample_mode_f'],
                                                 encoding={
                                                     'sample_mode':{'_FillValue':0, 'zlib':True}})

def main(dt, sat_comp, grid=None):
    output_paths = get_output_paths(sat_comp)
    if all([f.exists() for f in output_paths.values()]):
        print('All output files already exist. Skipping.')
        return
    if grid is None:
        grid = get_grid()
    grid_shape = grid.shape
    wmo_ids, sample_mode = get_sorting(dt, sat_comp, grid_shape)
    save_sorting(sat_comp, wmo_ids, sample_mode)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('sat_comp', type=str)
    parser.add_argument('dt', type=str)
    args = parser.parse_args()
    sat_comp = sorted(set(args.sat_comp.split(',')))
    dt = pd.to_datetime(args.dt)
    main(dt, sat_comp)
