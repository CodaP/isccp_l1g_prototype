from pathlib import Path
from tqdm import tqdm
from datetime import datetime
import make_netcdf
import utils
from multiprocessing import Pool
OUT = Path('final')

LAT=None
LON=None

def doit(item):
    dt, f = item
    return str(make_netcdf.rewrite_nc(f, OUT, dt, LAT, LON))

def rewrite():
    CACHE = Path('composite_cache')
    tasks = []
    grid = utils.get_grid(.05)
    grid_shape=grid.shape

    lon, lat = grid.get_lonlats()
    global LON,LAT
    LON = lon[0]
    LAT = lat[:,0]
    for out_dir in CACHE.glob('20*'):
        if out_dir.is_dir():
            dt = datetime.strptime(out_dir.name, '%Y%m%dT%H%M')
            out_dir = Path(out_dir)
            for f in out_dir.glob('*.nc'):
                tasks.append((dt, f))
    tasks = sorted(tasks)

    with Pool(12) as pool:
        with tqdm(pool.imap(doit, tasks), total=len(tasks)) as bar:
            for ret in bar:
                bar.set_description(ret)


if __name__ == '__main__':
    #import argparse
    #parser = argparse.ArgumentParser()
    #parser.add_argument('cache_dir')
    #args = parser.parse_args()
    #rewrite(args.cache_dir)
    rewrite()

