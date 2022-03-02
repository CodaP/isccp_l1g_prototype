from pathlib import Path
import xarray as xr
from tqdm import tqdm

ROOT = Path('final')

files = sorted(ROOT.glob('*/*/*/*/*temp_11_00um_2*.nc'))
bad = []
with open('gap_files.txt','w') as fp:
    with tqdm(files) as bar:
        for f in bar:
            ds = xr.open_dataset(f)
            v = ds.temp_11_00um
            if v.sel(layer=0, latitude=slice(10,-10)).isnull().any().item():
                bad.append(f)
                bar.set_description(f'{len(bad)}')
                fp.write(str(f)+'\n')
                fp.flush()
            ds.close()

    
