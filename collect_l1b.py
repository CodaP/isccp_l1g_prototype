import utils
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from tqdm import tqdm
import warnings
import shutil
import os

L1B_DIR = Path('l1b')
L1B_DIR.mkdir(exist_ok=True)

G16_ROOT = Path(('/apollo/ait/dc/noaa/goes_r/abi/'))
G17_ROOT = Path(('/apollo/ait/dc/noaa/goes_s/abi/'))
H8_ROOT = Path(('/apollo/ait/dc/jma/himawari08/HSD/ahi/'))


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


def get_or_files(d):
    files = pd.Series({parse_or(f.name):f for f in d.glob('*.nc')}).sort_index()
    files.index.names=['start','end','band']
    return files

def get_dat_files(d):
    files = {}
    for f in d.rglob("*FLDK*.DAT"):
        files[parse_dat(f.name)] = f
    files = pd.Series(files).sort_index()
    files.index.names=['start','band','segment']
    return files

def get_fd_goes(files, start, end):
    candidates = files.loc[:end, start:]
    longest = candidates.groupby(['start','band']).apply(lambda x: x.sort_index().iloc[-1])
    sizes = longest.groupby('start').size()
    full = longest.loc[[sizes.index[sizes == 16][0]]]
    return full

def get_fd_him(files, start):
    all_segments = [f'S{i:02}10' for i in range(1,11)]
    files = files.loc[start]
    def all_or_none(x):
        segs = x.droplevel('band').reindex(all_segments)
        if segs.isnull().any():
            return []
        else:
            return segs
    full_files = files.groupby(['band']).apply(all_or_none)
    assert set(files.index.get_level_values('band').unique()) == set(range(1,17))
    return full_files

def save_goes_files(out_root, sat, files, copy_func=shutil.copy):
    with tqdm(list(files.iteritems())) as bar:
        for (start, band), f in bar:
            out_dir = out_root / start.strftime('%Y%m%dT%H%M') / sat / f'{band:02d}'
            out_dir.mkdir(exist_ok=True, parents=True)
            out = out_dir / f.name
            if out.exists():
                out.unlink()
            copy_func(f, out)
            
            
def save_him_files(out_root, sat, files, start, copy_func=shutil.copy):
    with tqdm(list(files.iteritems())) as bar:
        for (band, seg), f in bar:
            out_dir = out_root / start.strftime('%Y%m%dT%H%M') / sat / f'{band:02d}'
            out_dir.mkdir(exist_ok=True, parents=True)
            out = out_dir / f.name
            if out.exists():
                out.unlink()
            copy_func(f, out)

            
def get_all_fd(start, end):
    G16_DIR = G16_ROOT / start.strftime('%Y%m%d/L1b/G16/RadF')
    G17_DIR = G17_ROOT / start.strftime('%Y%m%d/L1b/G17/RadF')
    H8_DIR = H8_ROOT / start.strftime('%Y/%Y_%m_%d_%j/%H%M')
    for d in G16_DIR, G17_DIR, H8_DIR:
        assert d.is_dir(), d
    g16_files = get_or_files(G16_DIR)
    g17_files = get_or_files(G17_DIR)
    h8_files = get_dat_files(H8_DIR)
    
    g16_fd = get_fd_goes(g16_files, start, end)
    g17_fd = get_fd_goes(g17_files, start, end)
    h8_fd = get_fd_him(h8_files, start)
    return g16_fd, g17_fd, h8_fd



def collect_all(dt, out_root=L1B_DIR, copy_func=os.symlink):
    round_down_30min = (dt - timedelta(minutes=dt.minute % 30)).replace(second=0, microsecond=0)
    start = round_down_30min
    end = start + timedelta(minutes=10)
    
    g16_fd, g17_fd, h8_fd = get_all_fd(start, end)
    save_goes_files(out_root, 'g16', g16_fd, copy_func=copy_func)
    save_goes_files(out_root, 'g17', g17_fd, copy_func=copy_func)
    save_him_files(out_root, 'h8', h8_fd, start, copy_func=copy_func)
    
    

    