from pathlib import Path
from tqdm import tqdm
import netCDF4

with tqdm(Path('dat/composite_cache').rglob('*.nc')) as bar:
    for f in bar:
        try:
            nc = netCDF4.Dataset(f)
            nc.close()
        except:
            print(f)

