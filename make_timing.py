from pathlib import Path
import os
os.environ['XRIT_DECOMPRESS_PATH'] = str(Path('xrit/PublicDecompWT/xRITDecompress/xRITDecompress').absolute())
import timing
import xarray as xr
import numpy as np
from utils import ALL_SATS, remap_fast_mean
from make_index import get_index_bands
from make_sample import open_index, read_scene, sample_path, SAMPLE_CACHE, INDEX, save
from collect_l1b import band_dir_path
import pandas as pd

ABI_SCAN_DIR = Path('dat/ancil/abi_scan_schedule/')

def load_sort_data(comp_dir):
    global GRID_SHAPE
    if comp_dir is None:
        comp_dir = SAMPLE_CACHE
    else:
        comp_dir = Path(comp_dir)
    wmo_ids = xr.open_dataset(comp_dir / 'wmo_id.nc').wmo_id
    GRID_SHAPE = wmo_ids.shape[-2:]
    return wmo_ids

def run_one(sat, dt):
    out_path = sample_path(dt, 'pixel_time', sat)
    if out_path.exists():
        return

    for attrs in ALL_SATS[:]:
        if attrs['sat'] != sat:
            continue
    
        pixel_time = np.full(GRID_SHAPE, np.nan, dtype=np.float32)
        _,index_band = max(get_index_bands(attrs['res']).items())

        src_index, dst_index, src_index_nn, dst_index_nn = open_index(INDEX, attrs['sat'], index_band)

        band_dir = band_dir_path(dt, sat=attrs['sat'], band='temp_11_00um')
        print(band_dir)

        files = list(band_dir.glob('*'))
        if len(files) == 0:
            print('no files found for ', dt, sat, ' skipping')
            return

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

        for layer in reversed(range(WMO_IDS.shape[0])):
            mask = (WMO_IDS[layer].values  == attrs['wmo_id'])
            pixel_time[mask] = out_nn[mask]
        
        save(pixel_time, 'pixel_time', out_path)

    

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--freq',default='30min')
    parser.add_argument('--compdir', required=True)
    parser.add_argument('sat')
    parser.add_argument('dt')
    parser.add_argument('end', nargs='?')
    args = parser.parse_args()
    dt = pd.to_datetime(args.dt)
    WMO_IDS = load_sort_data(args.compdir)
    if args.end is not None:
        end = pd.to_datetime(args.end)
        for dt in pd.date_range(dt, end, freq=args.freq):
            print(args.sat, dt)
            try:
                run_one(args.sat, dt)
            except Exception as e:
                print(e, flush=True)
            finally:
                pass
    else:
        run_one(args.sat, dt)
