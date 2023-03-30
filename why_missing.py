import pandas as pd
from collect_l1b import L1B_DIR, band_dir_path, get_fd
from make_sample import SAMPLE_CACHE, sample_path
from make_composite import NETCDF_OUT
from utils import ALL_SATS, ALL_BANDS
import itertools
from datetime import datetime, timedelta
from collections import defaultdict


def main(dts, sat=None, band=None):
    issue_counter = defaultdict(lambda : 0)
    for dt in dts:
        for b, sat_attrs in itertools.product(ALL_BANDS, ALL_SATS):
            if sat is not None and sat != sat_attrs['sat']:
                continue
            if band is not None and band != b:
                continue
            if b not in sat_attrs['bands']:
                continue

            fd = get_fd(sat_attrs['sat'], dt, dt + timedelta(minutes=10))
            if fd is None:
                print(f'No files for {sat_attrs["sat"]} {b} {dt}')
                issue_counter['missing l1b'] += 1
                issue_counter[f'missing {sat_attrs["sat"]} l1b'] += 1
                continue

            out_dir = band_dir_path(dt, sat_attrs['sat'], b)
            if not out_dir.is_dir():
                print(f'{out_dir} does not exist')
                print('Run:', 'srun','-N1','-n1','-p','cirrus','-c','1','--time','01:00:00','--mem-per-cpu=3G', 'python collect_l1b.py', dt.strftime('%Y-%m-%dT%H:%M'))
                issue_counter['l1b not collected'] += 1
                issue_counter[f'l1b not collected {sat_attrs["sat"]}'] += 1
                issue_counter[f'l1b not collected {b}'] += 1
                continue

            zstd_file = sample_path(dt, b, sat_attrs['sat'])
            if not zstd_file.is_file():
                print(f'{zstd_file} does not exist')
                print('Run:','\nsrun','-N1','-n1','-p','cirrus','-c','4','--time','01:00:00','--mem-per-cpu=3G','python make_sample.py', '--sortdir=SORTDIR', sat_attrs['sat'], b, dt.strftime('%Y-%m-%dT%H:%M'))
                issue_counter['sample not made'] += 1
                issue_counter[f'sample not made {sat_attrs["sat"]}'] += 1
                issue_counter[f'sample not made {b}'] += 1
                continue
    for k,v in sorted(issue_counter.items(), key=lambda x: x[1], reverse=True):
        print(f'{k:>40}: {v:>6}')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--sat')
    parser.add_argument('--band')
    parser.add_argument('dt')
    parser.add_argument('end', nargs='?')
    parser.add_argument('--freq', default='30min')
    args = parser.parse_args()

    dt = pd.to_datetime(args.dt)

    if args.end is not None:
        end = pd.to_datetime(args.end)
        dates = pd.date_range(dt, end, freq=args.freq)
    else:
        dates = [dt]
    
    main(dates, args.sat, args.band)
