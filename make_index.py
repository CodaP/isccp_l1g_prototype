
import pyresample
from pyresample.kd_tree import get_neighbour_info
import numpy as np
import xarray as xr
import pandas as pd
from utils import get_area, get_grid
from pathlib import Path
import warnings


def get_nn_index(area, pc, radius=5e3, nprocs=8):
    valid_input_index, valid_output_index, index_array, distance_array = get_neighbour_info(area,
                           pc,
                           radius,
                           neighbours=1,
                           nprocs=nprocs)
    grid_idx = np.arange(valid_output_index.size)[valid_output_index][index_array!=valid_input_index.sum()]
    sat_idx = np.arange(valid_input_index.size)[valid_input_index][index_array[index_array!=valid_input_index.sum()]]
    return grid_idx, sat_idx
    

def get_index(area, pc, satzen, max_satzen, radius=5000, nprocs=8):
    valid_input_index, valid_output_index, index_array, distance_array = get_neighbour_info(pc,
                           area,
                           radius,
                           neighbours=1,
                           nprocs=nprocs)
    sat_idx = np.arange(valid_output_index.size)[valid_output_index][index_array!=valid_input_index.sum()]
    grid_idx = np.arange(valid_input_index.size)[valid_input_index][index_array[index_array!=valid_input_index.sum()]]
    s = pd.Series(sat_idx, index=grid_idx)
    s.sort_index(inplace=True)
    mask = satzen.ravel()[s.values] < max_satzen
    s = s.loc[mask]
    grid_idx = s.index.values.astype(np.uint64)
    sat_idx = s.values.astype(np.uint64)
    return grid_idx, sat_idx


def main(files, out_dir, satzen_nc, max_satzen):
    out_dir.mkdir(exist_ok=True, parents=True)
    satzen = xr.open_dataset(satzen_nc).satzen.load()
    area = get_area(files)
    satzen = satzen.interp(y=np.linspace(0,satzen.shape[0], area.shape[0]),
        x=np.linspace(0,satzen.shape[1], area.shape[1])).values
    grid = get_grid(.05)
    grid_idx, sat_idx = get_index(area, grid, satzen, max_satzen, radius=2e3)
    grid_idx_nn, sat_idx_nn = get_nn_index(area, grid, radius=10e3, nprocs=1)
    with open(out_dir / 'dst_index.dat','wb') as fp:
        grid_idx.tofile(fp)
    with open(out_dir / 'src_index.dat','wb') as fp:
        sat_idx.tofile(fp)
    with open(out_dir / 'dst_index_nn.dat','wb') as fp:
        grid_idx_nn.tofile(fp)
    with open(out_dir / 'src_index_nn.dat','wb') as fp:
        sat_idx_nn.tofile(fp)


def get_max_satzen(r_footprint, r_sample):
    max_satzen = np.rad2deg(np.arccos(r_footprint / r_sample))
    return max_satzen
        
        
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input_files', nargs='+')
    parser.add_argument('output_dir')
    parser.add_argument('satzen_nc')
    parser.add_argument('max_satzen', type=float)
    args = parser.parse_args()
    main(Path(args.input_file), Path(args.output_dir), Path(args.satzen_nc), args.max_satzen)
    
