import collect_l1b as c
import make_sample
import make_netcdf
import make_index
from tqdm import tqdm
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

OUT = Path('dat/final')
OUT.mkdir(exist_ok=True)


def main(dt, progress=True):
    dt = c.get_start_dt(dt)
    grid = make_index.get_grid(.05)
    grid_shape=grid.shape
    
    lon, lat = grid.get_lonlats()
    lon = lon[0]
    lat = lat[:,0]
    
    c.collect_all(dt, progress=progress)
    out_dir = make_sample.main(dt, progress=progress)
    
    if progress:
        with tqdm(list(out_dir.glob('*.nc'))) as bar:
            for f in bar:
                bar.set_description(str(make_netcdf.rewrite_nc(f, OUT, dt, lat, lon)))
    else:
        for f in list(out_dir.glob('*.nc')):
            make_netcdf.rewrite_nc(f, OUT, dt, lat, lon)
    
    
if __name__ == '__main__':
    now = datetime.utcnow() - timedelta(minutes=30)
    main(now)
    
