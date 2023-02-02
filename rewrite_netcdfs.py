from pathlib import Path
from tqdm import tqdm
from datetime import datetime
import make_netcdf
import utils
from make_sample import comp_cache_dir
from multiprocessing import Pool
OUT = Path('dat/final')
COMPOSITE_CACHE = Path('dat/composite_cache')

LAT=None
LON=None

def doit(item):
    dt, f = item
    try:
        return str(make_netcdf.rewrite_nc(f, OUT, dt, LAT, LON))
    #except Exception as e:
        #return str(type(e))
    finally:
        pass



def main(task_id, num_tasks, missing=False):
    tasks = []
    grid = utils.get_grid()
    grid_shape=grid.shape

    lon, lat = grid.get_lonlats()
    global LON,LAT
    LON = lon[0]
    LAT = lat[:,0]
    if not missing:
        #composite_cache/2020/202001/20200101/20200101T0000/
        with open('date_list.txt') as fp:
            dts = [datetime.strptime(d.strip(),'%Y%m%dT%H%M') for d in fp]
    else:
        dts = set()
        with open('missing.txt') as fp:
            for l in fp:
                f = Path(l.strip())
                dt = datetime.strptime(''.join(f.parts[-5:-1]), '%Y%m%d%H%M')
                dts.add(dt)
        dts = sorted(dts)

    dts = dts[task_id::num_tasks]
    print(len(dts), 'dts')
    for i,dt in enumerate(dts,1):
        out_dir = comp_cache_dir(dt)
        if out_dir.is_dir():
            for f in out_dir.glob('*.nc'):
                tasks.append((dt, f))
            tasks.append((dt, COMPOSITE_CACHE / 'wmo_id.nc'))
            tasks.append((dt, COMPOSITE_CACHE / 'satzen.nc'))
            tasks.append((dt, COMPOSITE_CACHE / 'satazi.nc'))
            tasks.append((dt, COMPOSITE_CACHE / 'sample_mode.nc'))
    tasks = sorted(tasks)

    print(len(tasks), 'tasks')
    
    with tqdm(tasks) as bar:
        for task in bar:
            ret = doit(task)
            bar.write(f'{task[0]} {task[1].name}\n{str(ret)}\n')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--missing',action='store_true')
    parser.add_argument('task_id',type=int)
    parser.add_argument('max_task_id',type=int)
    args = parser.parse_args()
    main(args.task_id, args.max_task_id+1, missing=args.missing)

