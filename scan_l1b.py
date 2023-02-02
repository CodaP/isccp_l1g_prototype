import utils
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from tqdm import tqdm
import warnings
import shutil
import os
import re

G16_ROOT = Path('/arcdata/goes/grb/goes16/')
G17_ROOT = Path('/arcdata/goes/grb/goes17/')
H8_ROOT = Path('/arcdata/nongoes/japan/himawari08/')
M8_ROOT = Path('/arcdata/nongoes/meteosat/meteosat8/')
M11_ROOT = Path('/arcdata/nongoes/meteosat/meteosat11/')

ROOTS = {'g16':G16_ROOT, 'g17':G17_ROOT, 'h8':H8_ROOT, 'm8':M8_ROOT, 'm11':M11_ROOT}

def parse_or(fname):
    _,band,sat,start,end,create = fname.split('.')[0].split('_')
    start = datetime.strptime(start[:-1], 's%Y%j%H%M%S')
    end = datetime.strptime(end[:-1], 'e%Y%j%H%M%S')
    band = int(band[-2:])
    return (start, end, band)


def parse_dat(fname):
    _,sat,date,start,band,region,res,segment = fname.split('.')[0].split('_')
    start = datetime.strptime(date+start, '%Y%m%d%H%M')
    band = int(band.strip('B'))
    return start, band, segment


def parse_hrit_file(f):
    H,num1,msg,iodc,band,file,dt,c = f.name.split('-')
    num1 = int(num1)
    dt = datetime.strptime(dt, '%Y%m%d%H%M')
    return {'path':f,'dt':dt,'H':H,'num1':num1,'segment':file.strip('_'),'band':band.strip('_'),
            'iodc':iodc.strip('_'),'c':c,'msg':msg.strip('_')}


def get_hrit_files(d):
    files = pd.DataFrame(parse_hrit_file(f) for f in sorted(d.glob('*')))
    if files.empty:
        return
    return files


def get_or_files(d):
    files = pd.Series({parse_or(f.name):f for f in d.glob('*.nc')}).sort_index()
    if files.empty:
        return
    files.index.names=['start','end','band']
    return files

def get_dat_files(d):
    files = {}
    for f in d.rglob("*FLDK*.DAT"):
        files[parse_dat(f.name)] = f
    if files:
        files = pd.Series(files).sort_index()
        files.index.names=['start','band','segment']
        return files


def lowest_common_dir(d1,d2):
    d1 = d1.absolute()
    d2 = d2.absolute()
    shared_part = Path('/')
    for part1, part2 in zip(d1.parts[1:], d2.parts[1:]):
        if part1 == part2:
            shared_part = shared_part / part1
        else:
            return shared_part

def common_glob(d1, d2, root, const_mask):
    """
    Get the root and glob that contains both dirs
    """
    d1 = Path(d1)
    d2 = Path(d2)
    lcd = lowest_common_dir(d1, d2)
    num_relative = len(d1.relative_to(root).parts)
    num_common = len(lcd.relative_to(root).parts)
    const_mask = const_mask[num_common:]
    extra_parts = d1.relative_to(lcd).parts
    glob = '/'.join([part if m else '*' for part,m in zip(extra_parts, const_mask)])
    return lcd, glob


def parse_dt(k, fmt):
    padded = fmt
    for old,new in [('%Y','XXXX'),('%m','XX'),('%d','XX'),('%j','XXX')]:
        padded = padded.replace(old,new)

    year = None
    


def iter_files(sat, start, end):
    root = ROOTS[sat]
    fmts = {'g':'%Y/%Y_%m_%d_%j/abi/L1b/RadF','h':'%Y_%m/%Y_%m_%d_%j/%H%M','m':'%Y/%Y_%m_%d_%j'}
    fmt = fmts[sat[0]]
    start_dir = start.strftime(fmt)
    end_dir = end.strftime(fmt)
    const_mask = ['%' not in part for part in fmt.split('/')]
    lcd, glob = common_glob(root / start_dir, root / end_dir, root, const_mask)
    get_files = {'g':get_or_files,'h':get_dat_files,'m':get_hrit_files}[sat[0]]
    print(lcd, glob)
    for d in lcd.glob(glob):
        dt = datetime.strptime(str(d.relative_to(root)), fmt)
        if dt >= start and dt <= end:
            files = get_files(d)
            yield files
    

def scan(scan_start_dt, scan_end_dt):
    for attrs in utils.ALL_SATS:
        sat = attrs['sat']
        for files in iter_files(sat, scan_start_dt, scan_end_dt):
            print(files)
            break
    

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('scan_start')
    parser.add_argument('scan_end')
    args = parser.parse_args()
    scan_start = pd.to_datetime(args.scan_start)
    scan_end = pd.to_datetime(args.scan_end)
    scan(scan_start, scan_end)

