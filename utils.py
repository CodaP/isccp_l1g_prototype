import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from tqdm import tqdm

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
    #end = datetime.strptime(end[:-1], 'e%Y%j%H%M%S')
    #return (start, end)
    return start, band, segment