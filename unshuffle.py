import warnings

import pickle
from tqdm import tqdm
from pathlib import Path

import netCDF4

from datetime import datetime
import itertools
from pathlib import Path

import zstandard as zstd
import numpy as np


SAMPLE_CACHE = Path('dat/sample_cache').resolve()
SAMPLE_CACHE.mkdir(exist_ok=True)

COMP_CACHE = Path('dat/composite_cache/').resolve()

WMO_IDS = {55, 70, 173, 270, 271}

def prepare():
    wmo_id_nc = netCDF4.Dataset(COMP_CACHE / 'wmo_id.nc')

    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        wmo_id = wmo_id_nc['wmo_id'][:]
    wmo_masks = {id: (wmo_id == id).filled(False).nonzero() for id in WMO_IDS}
    wmo_id_nc.close()
    return wmo_masks


def read_netcdf(f):
    with open(f,'rb') as fp:
        data = fp.read()
    nc = netCDF4.Dataset('memory', memory=data)
    nc.set_auto_scale(False)
    k = sorted(nc.variables)[0]
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        v = nc[k][:]
    nc.close()
    return k, v

def unshuffle(f, dst_dir, wmo_masks):
    k,v = read_netcdf(f)
    layer = np.ma.masked_all(v.shape[1:], dtype=v.dtype)
    for id, mask in wmo_masks.items():
        layer[:] = np.ma.masked
        layer[mask[1:]] = v[mask]
        if not layer.mask.all():
            dir = dst_dir / str(id)
            dir.mkdir(exist_ok=True)
            dst = dir / f'{k}.dat.zstd'
            tmp = dir / f'.{k}.dat.zstd'
            if dst.exists():
                continue
            with open(tmp, 'wb') as fp:
                fp.write(zstd.compress(layer.filled(v.fill_value)))
            tmp.rename(dst)
            


def main(task_id, ntasks):
    with open('unshuffle_tasks.pickle','rb') as fp:
        tasks = pickle.load(fp)
    my_tasks = tasks[task_id::ntasks]

    wmo_masks = prepare()

    for i,(f, dst_dir) in enumerate(my_tasks,1):
        print(f'{i}/{len(my_tasks)}',flush=True)
        print(f)
        unshuffle(f, dst_dir, wmo_masks)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('task_id', type=int)
    parser.add_argument('max_id', type=int)
    args = parser.parse_args()
    main(args.task_id, args.max_id+1)

