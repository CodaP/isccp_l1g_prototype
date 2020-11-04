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

#G16_ROOT = Path('/apollo/ait/dc/noaa/goes_r/abi/')
G16_ROOT = Path('/arcdata/goes/grb/goes16/')
#G17_ROOT = Path('/apollo/ait/dc/noaa/goes_s/abi/')
G17_ROOT = Path('/arcdata/goes/grb/goes17/')
#H8_ROOT = Path('/apollo/ait/dc/jma/himawari08/HSD/ahi/')
H8_ROOT = Path('/arcdata/nongoes/jma/himawari08/ahi/')
M8_ROOT = Path('/arcdata/nongoes/meteosat/meteosat8/')
M11_ROOT = Path('/arcdata/nongoes/meteosat/meteosat11/')


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
    return files


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
            return segs.iloc[:0]
        else:
            return segs
    full_files = files.groupby(['band']).apply(all_or_none)
    assert set(files.index.get_level_values('band').unique()) == set(range(1,17))
    return full_files


def get_fd_hrit(files, start):
    all_segments = [f'00000{i}' for i in range(1,9)]
    bands = [ 'VIS008', 'VIS006', 'IR_039', 'IR_087', 'WV_073',
        'IR_108', 'IR_097', 'IR_134', 'WV_062', 'IR_016', 'IR_120']
    files = files.set_index('dt').loc[start]
    def all_or_none(x):
        segs = x.set_index('segment').reindex(all_segments)
        if segs.path.isnull().any():
            return segs.iloc[:0]
        else:
            return segs
    full_files = files.loc[files.band.isin(bands)].groupby('band').apply(all_or_none).path
    pro = files.loc[files.segment == 'PRO'].set_index(['band','segment']).path
    epi = files.loc[files.segment == 'EPI'].set_index(['band','segment']).path
    full_files = pd.concat([full_files, pro, epi])
    return full_files
        

def save_goes_files(out_root, sat, files, copy_func=shutil.copy, progress=True):
    tasks = list(files.iteritems())
    def run(it):
        for (start, band), f in it:
            variable = utils.ABI_VARIABLES[f'{band:02d}']
            out_dir = out_root / start.strftime('%Y%m%dT%H%M') / sat / f'{variable}'
            out_dir.mkdir(exist_ok=True, parents=True)
            out = out_dir / f.name
            if out.exists():
                out.unlink()
            copy_func(f, out)
    if progress:
        with tqdm(tasks) as bar:
            run(bar)
    else:
        run(tasks)
            
            
def save_him_files(out_root, sat, files, start, copy_func=shutil.copy, progress=True):
    tasks = list(files.iteritems())
    def run(it):
        for (band, seg), f in it:
            variable = utils.AHI_VARIABLES[f'{band:02d}']
            out_dir = out_root / start.strftime('%Y%m%dT%H%M') / sat / f'{variable}'
            out_dir.mkdir(exist_ok=True, parents=True)
            out = out_dir / f.name
            if out.exists():
                out.unlink()
            copy_func(f, out)
    if progress:
        with tqdm(tasks) as bar:
            run(bar)
    else:
        run(tasks)

        
def save_hrit_files(out_root, sat, files, start, copy_func=shutil.copy, progress=True):
    bands = list(files.groupby('band'))
    def run(it):
        for band, _ in it:
            if band != '':
                # include EPI + PRO
                subfiles = files.loc[[band,''],:].tolist()
                variable = utils.MSG_VARIABLES[band]
                out_dir = out_root / start.strftime('%Y%m%dT%H%M') / sat / f'{variable}'
                out_dir.mkdir(exist_ok=True, parents=True)
                for f in subfiles:
                    out = out_dir / f.name
                    if out.exists():
                        out.unlink()
                    copy_func(f, out)
    if progress:
        with tqdm(bands) as bar:
            run(bar)
    else:
        run(bands)

            
def get_all_fd(start, end):
    G16_DIR = G16_ROOT / start.strftime('%Y/%Y_%m_%d_%j/abi/L1b/RadF')
    G17_DIR = G17_ROOT / start.strftime('%Y/%Y_%m_%d_%j/abi/L1b/RadF')
    H8_DIR = H8_ROOT / start.strftime('%Y/%Y_%m_%d_%j/%H%M')
    M8_DIR = M8_ROOT / start.strftime('%Y/%Y_%m_%d_%j')
    M11_DIR = M11_ROOT / start.strftime('%Y/%Y_%m_%d_%j')
    for d in G16_DIR, G17_DIR, H8_DIR, M8_DIR, M11_DIR:
        assert d.is_dir(), d
    g16_files = get_or_files(G16_DIR)
    g17_files = get_or_files(G17_DIR)
    h8_files = get_dat_files(H8_DIR)
    m8_files = get_hrit_files(M8_DIR)
    m11_files = get_hrit_files(M11_DIR)
    
    g16_fd = get_fd_goes(g16_files, start, end)
    g17_fd = get_fd_goes(g17_files, start, end)
    h8_fd = get_fd_him(h8_files, start)
    m8_fd = get_fd_hrit(m8_files, start)
    m11_fd = get_fd_hrit(m11_files, start)
    return g16_fd, g17_fd, h8_fd, m8_fd, m11_fd


def get_start_dt(dt):
    round_down_30min = (dt - timedelta(minutes=dt.minute % 30)).replace(second=0, microsecond=0)
    start = round_down_30min
    return start


def collect_all(dt, out_root=L1B_DIR, copy_func=os.symlink, progress=True):
    start = get_start_dt(dt)
    end = start + timedelta(minutes=10)
    
    g16_fd, g17_fd, h8_fd, m8_fd, m11_fd = get_all_fd(start, end)
    save_goes_files(out_root, 'g16', g16_fd, copy_func=copy_func, progress=progress)
    save_goes_files(out_root, 'g17', g17_fd, copy_func=copy_func, progress=progress)
    save_him_files(out_root, 'h8', h8_fd, start, copy_func=copy_func, progress=progress)
    # MSG are access controlled, so copy the files
    save_hrit_files(out_root, 'm8', m8_fd, start, copy_func=copy_func, progress=progress)
    save_hrit_files(out_root, 'm11', m11_fd, start, copy_func=copy_func, progress=progress)
    
    

    

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('dt')
    parser.add_argument('end_dt', nargs='?')
    args = parser.parse_args()
    dt = pd.to_datetime(args.dt)
    if args.end_dt is not None:
        dt = pd.date_range(dt, args.end_dt, freq='30min')
        for d in dt:
            collect_all(d)
    else:
        collect_all(dt)

