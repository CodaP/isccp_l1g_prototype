
import pyresample
from pyresample.kd_tree import get_neighbour_info
import numpy as np
import pandas as pd
from utils import get_area, get_grid
from pathlib import Path
import warnings


def get_index(area, pc, radius=5000, nprocs=8):
    valid_input_index, valid_output_index, index_array, distance_array = get_neighbour_info(pc,
                           area,
                           radius,
                           neighbours=1,
                           nprocs=nprocs)
    sat_idx = np.arange(valid_output_index.size)[valid_output_index][index_array!=valid_input_index.size]
    grid_idx = index_array[index_array!=valid_input_index.size]
    s = pd.Series(sat_idx, index=grid_idx)
    s.sort_index(inplace=True)
    grid_idx = s.index.values.astype(np.uint64)
    sat_idx = s.values.astype(np.uint64)
    return grid_idx, sat_idx


def main(files, out_dir):
    out_dir.mkdir(exist_ok=True, parents=True)
    area = get_area(files)
    grid = get_grid(.05)
    grid_idx, sat_idx = get_index(area, grid, radius=2e3)
    with open(out_dir / 'dst_index.dat','wb') as fp:
        grid_idx.tofile(fp)
    with open(out_dir / 'src_index.dat','wb') as fp:
        sat_idx.tofile(fp)
        
        
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input_files', nargs='+')
    parser.add_argument('output_dir')
    args = parser.parse_args()
    main(Path(args.input_file), Path(args.output_dir))
    
