"""
Create src_index.dat and dst_index.dat files in $DAT/index/$sat/$band
"""

import pyresample
from pyresample.kd_tree import get_neighbour_info
import numpy as np
import xarray as xr
import pandas as pd
from utils import get_area, get_grid, ALL_SATS
from pathlib import Path
import warnings
from tqdm import tqdm
import subprocess
from collect_l1b import band_dir_path


def get_index_bands(res):
    """
    Pick one band to represent each resolution
    """
    index = {}
    for channel,r in sorted(res.items(), reverse=True):
        index[r] = channel
    return index


def get_nn_index(area, pc, radius=5e3, nprocs=8):
    valid_input_index, valid_output_index, index_array, distance_array = get_neighbour_info(area,
                           pc,
                           radius,
                           neighbours=1,
                           nprocs=nprocs)
    grid_idx = np.arange(valid_output_index.size)[valid_output_index][index_array!=valid_input_index.sum()]
    sat_idx = np.arange(valid_input_index.size)[valid_input_index][index_array[index_array!=valid_input_index.sum()]]
    return grid_idx, sat_idx
    


def get_index_fast(area, pc, radius=2e3, nprocs=8):
    assert radius == 2e3
    rows,cols = area.shape
    grid_rows, grid_cols = pc.shape
    coords = area.get_cartesian_coords(nprocs=nprocs)
    coords_padded = np.pad(coords.astype(np.float32), ((0,0),(0,0),(0,1))).astype(np.float32)
    coords_padded.tofile('coord_descent/sat_coords.dat')
    grid_coords = pc.get_cartesian_coords()
    grid_coords_pad = np.pad(grid_coords, ((0,0),(0,0),(0,1))).astype(np.float32)
    grid_coords_pad.astype(np.float32).tofile('coord_descent/grid_coords.dat')
    subprocess.run(['./main',str(rows),str(cols), str(grid_rows),str(grid_cols), f'{radius:.0f}'], cwd='coord_descent', capture_output=False)
    sat_idx = np.memmap('coord_descent/src_index.dat', mode='r', dtype=np.uint32)
    grid_idx = np.memmap('coord_descent/dst_index.dat', mode='r', dtype=np.uint32)
    return grid_idx, sat_idx


def set_d(bar, msg):
    if bar is not None:
        bar.set_description(f'{bar.prefix} {msg}')

def make_one(files, out_dir, bar=None):
    dst_index_path = out_dir / 'dst_index.dat'
    src_index_path = out_dir / 'src_index.dat'
    dst_index_nn_path = out_dir / 'dst_index_nn.dat'
    src_index_nn_path = out_dir / 'src_index_nn.dat'

    # if all files exist, return
    if dst_index_path.exists() and src_index_path.exists() and dst_index_nn_path.exists() and src_index_nn_path.exists():
        set_d(bar, 'all files exist')
        return

    set_d(bar, f'Making {out_dir}')
    out_dir.mkdir(exist_ok=True, parents=True)
    set_d(bar, 'getting area')
    area = get_area(files)
    set_d(bar, 'setup grid')
    grid = get_grid()
    
    # Elliptical mean
    if not (dst_index_path.exists() and src_index_path.exists()):
        set_d(bar, f'making ellip index ({area.shape}) -> ({grid.shape})')
        grid_idx, sat_idx = get_index_fast(area, grid, radius=2e3)
        set_d(bar, 'saving ellip index')
        with open(dst_index_path,'wb') as fp:
            grid_idx.tofile(fp)
        with open(src_index_path,'wb') as fp:
            sat_idx.tofile(fp)
    else:
        print('ellip index exists', dst_index_path, src_index_path)
    
    # NN mean
    if not (dst_index_nn_path.exists() and src_index_nn_path.exists()):
        set_d(bar, 'making nn index')
        grid_idx_nn, sat_idx_nn = get_nn_index(area, grid, radius=10e3, nprocs=1)
        set_d(bar, 'saving nn index')
        with open(dst_index_nn_path,'wb') as fp:
            grid_idx_nn.tofile(fp)
        with open(src_index_nn_path,'wb') as fp:
            sat_idx_nn.tofile(fp)
    else:
        print('nn index exists', dst_index_nn_path, src_index_nn_path)
        
        
def main(dt, r_sample=2):
    all_index = []
    for attrs in ALL_SATS:
        bands = get_index_bands(attrs['res'])
        r_footprint = max(bands)
        for res,band in sorted(bands.items()):
            all_index.append((attrs['sat'],band,res,r_footprint))
            print(all_index[-1])
        
    with tqdm(all_index) as bar:
        for sat,band,res,r_footprint in bar:
            prefix = f'{sat} {band}:'
            bar.prefix = prefix
            input_dir = band_dir_path(dt, sat, band)
            if not input_dir.exists():
                print(sat, band, 'no input files')
                continue
            input_files = list(input_dir.glob('*'))
            output_dir = Path('dat/index') / sat / band
            set_d(bar, 'making index')
            make_one(input_files, output_dir, bar=bar)
        
        
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('dt')
    args = parser.parse_args()
    dt = pd.to_datetime(args.dt)
    main(dt)
    
