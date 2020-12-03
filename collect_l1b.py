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

def filter_fd_goes(files, start, end):
    candidates = files.loc[:end, start:]
    longest = candidates.groupby(['start','band']).apply(lambda x: x.sort_index().iloc[-1])
    sizes = longest.groupby('start').size()
    full = longest.loc[[sizes.index[sizes == 16][0]]]
    return full

def filter_fd_him(files, start, end=None):
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


def filter_fd_hrit(files, start, end=None):
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
            out_dir = out_root / f'{variable}'
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
            
            
def save_him_files(out_root, sat, files, copy_func=shutil.copy, progress=True):
    tasks = list(files.iteritems())
    def run(it):
        for (band, seg), f in it:
            variable = utils.AHI_VARIABLES[f'{band:02d}']
            out_dir = out_root / f'{variable}'
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

        
def save_hrit_files(out_root, sat, files, copy_func=shutil.copy, progress=True):
    bands = list(files.groupby('band'))
    def run(it):
        for band, _ in it:
            if band != '':
                # include EPI + PRO
                subfiles = files.loc[[band,''],:].tolist()
                variable = utils.MSG_VARIABLES[band]
                out_dir = out_root / f'{variable}'
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


def save_files(out_dir, sat, files, copy_func=os.symlink, progress=True):
    save_func = {'g':save_goes_files, 'h':save_him_files, 'm':save_hrit_files}[sat[0]]
    save_func(out_dir, sat, files, copy_func=copy_func, progress=progress)


def _get_fd(root, fmt, get_files, filter_fd, start, end):
    dir = root / start.strftime(fmt)
    if not dir.is_dir():
        print(f'{dir} does not exist')
        return
    files = get_files(dir)
    if files is not None and len(files) > 0:
        fd = filter_fd(files, start, end)
        return fd
    else:
        print(f'no good files in {dir}')

def get_fd(sat, start, end):
    root = ROOTS[sat]
    fmts = {'g':'%Y/%Y_%m_%d_%j/abi/L1b/RadF','h':'%Y_%m/%Y_%m_%d_%j/%H%M','m':'%Y/%Y_%m_%d_%j'}
    fmt = fmts[sat[0]]
    get_files = {'g':get_or_files,'h':get_dat_files,'m':get_hrit_files}[sat[0]]
    filter_fd = {'g':filter_fd_goes, 'h':filter_fd_him, 'm':filter_fd_hrit}[sat[0]]
    return _get_fd(root, fmt, get_files, filter_fd, start, end)
            

def get_start_dt(dt):
    round_down_30min = (dt - timedelta(minutes=dt.minute % 30)).replace(second=0, microsecond=0)
    start = round_down_30min
    return start


def collect_all(dt, out_root=L1B_DIR, error_file=Path('errors.txt'), copy_func=os.symlink, progress=True):
    start = get_start_dt(dt)
    end = start + timedelta(minutes=10)
    
    for attrs in utils.ALL_SATS:
        sat = attrs['sat']
        out_dir = out_root / start.strftime('%Y%m%dT%H%M') / sat
        if out_dir.is_dir():
            #print(f'Already have {out_dir}')
            continue
        else:
            print(start.strftime(f'Collecting L1b for {sat} %Y-%m-%dT%H:%M'))
            fd = get_fd(sat, start, end)
            if fd is not None:
                save_files(out_dir, sat, fd, copy_func=copy_func, progress=progress)
            else:
                with open(error_file, 'a') as fp:
                    fp.write(str(out_dir)+'\n')
    
    

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

