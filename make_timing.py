from pathlib import Path
import os
os.environ['XRIT_DECOMPRESS_PATH'] = str(Path('xrit/PublicDecompWT/xRITDecompress/xRITDecompress').absolute())
import timing
import netCDF4
import xarray as xr
import numpy as np
from tqdm import tqdm
from datetime import datetime, timedelta
from utils import ALL_SATS, remap_fast_mean
from make_index import get_index_bands
from make_sample import open_index, read_scene, comp_cache_dir
from collect_l1b import band_dir_path, L1B_DIR
import satpy

COMP_CACHE = Path('composite_cache/')
INDEX = Path('index')
ABI_SCAN_DIR = Path('ancil/abi_scan_schedule/')

WMO_IDS = xr.open_dataset(COMP_CACHE / 'wmo_id.nc').wmo_id
SAMPLE_MODE = xr.open_dataset(COMP_CACHE / 'sample_mode.nc').sample_mode
GRID_SHAPE = WMO_IDS.shape

def saveit(composite, out):
    fill = netCDF4.default_fillvals['i2']
    ds = xr.Dataset()
    ds['pixel_time'] = composite.fillna(fill).astype(np.int16)

    encoding = {'pixel_time':{'zlib':True,'chunksizes':(1, 1800, 3600), '_FillValue':fill, 'dtype':'i2'}}

    ds.to_netcdf(out, encoding=encoding)


def run_one(dt):
    out_dir = comp_cache_dir(dt)
    out_path = out_dir / 'pixel_time.nc'
    if out_path.exists():
        return

    composite = xr.DataArray(np.full(GRID_SHAPE, np.nan, dtype=np.float32), dims=['layer','latitude','longitude'])

    for attrs in ALL_SATS[:]:
        prefix = (attrs['name'])
        _,index_band = max(get_index_bands(attrs['res']).items())

        src_index, dst_index, src_index_nn, dst_index_nn = open_index(INDEX, attrs['sat'], index_band)

        band_dir = band_dir_path(dt, sat=attrs['sat'], band='temp_11_00um')
        print(band_dir)

        files = list(band_dir.glob('*'))
        try:
            v, area = read_scene(files, attrs['reader'])

            if attrs['reader'] == 'seviri_l1b_hrit':
                start_time, line_times = timing.meteosat_get_time_offset(v)
                offsets = timing.meteosat_estimate_pixel_time_offsets(line_times)

            elif attrs['reader'] == 'ahi_hsd':
                start_time, line_times = timing.himawari_line_times(files)
                offsets = timing.himawari_estimate_pixel_time_offsets(line_times)

            elif attrs['reader'] == 'abi_l1b':
                offsets = timing.goes_pixel_time_offset(ABI_SCAN_DIR)
                start_time = timing.goes_start_time(files)
            adjust = (start_time - dt).total_seconds()
            offsets += adjust

            out_nn = remap_fast_mean(src_index_nn, dst_index_nn, offsets, GRID_SHAPE[-2:])

            for layer in range(composite.shape[0]):
                mask = (WMO_IDS[layer].values  == attrs['wmo_id'])
                composite.values[layer, mask] = out_nn[mask]
        except Exception as e:
            print(f'Problem reading {attrs["sat"]}')
    saveit(composite, out_path)

def get_timing_list():
    dts = sorted([datetime.strptime(''.join(i.parts[1:]),'%Y%m%d%H%M') for i in COMP_CACHE.glob('*/*/*/*')])
    with open('date_list.txt','w') as fp:
        for dt in dts:
            fp.write(dt.strftime('%Y%m%dT%H%M\n'))


def main(task_id, num_tasks):
    with open('date_list.txt') as fp:
        dts = [datetime.strptime(i.strip(),'%Y%m%dT%H%M') for i in fp]
    dts = dts[task_id::num_tasks]
    print(f'{len(dts)} tasks')

    for i,dt in enumerate(dts,1):
        print(f'{i}/{len(dts)}', flush=True)
        try:
            run_one(dt)
        except IOError:
            print('problem reading',dt, flush=True)
        print(flush=True)

    

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('task_id',type=int)
    parser.add_argument('max_task_id',type=int)
    args = parser.parse_args()
    main(args.task_id, args.max_task_id+1)

