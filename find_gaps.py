from pathlib import Path
import xarray as xr
from tqdm import tqdm

ROOT = Path('final')

#final/2020/202007/20200701/20200701T0000/ISCCP-NG_L1g_demo_A1_v1_res_0_10deg__temp_11_00um_20200701T0000.nc
#*/*/*/*/ISCCP-NG_L1g_demo_A1_v1_res_0_10deg__temp_11_00um_20200701T0000.nc
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

    
