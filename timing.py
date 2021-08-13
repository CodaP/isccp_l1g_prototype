import xarray as xr
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from pathlib import Path
import warnings
import satpy
import scipy.interpolate
import himawari.HimawariScene


def himawari_line_times(files):
    assert len(files) == 10
    fake_fname = str(min(files)).replace('S0110.DAT','S????.DAT')
    scene = himawari.HimawariScene.HimawariScene(fake_fname)
    start_time, line_times = scene.line_times
    start_time = pd.to_datetime(start_time, unit='s')
    scene.close()
    return start_time, line_times


def himawari_estimate_pixel_time_offsets(line_starttimes):
    fd_shape = tuple([line_starttimes.size]*2)
    line_starttimes = pd.Series(line_starttimes).value_counts().sort_index()

    interp = scipy.interpolate.interp1d(np.arange(len(line_starttimes)), line_starttimes.index, kind='slinear', fill_value='extrapolate')
    line_times = interp(np.arange(len(line_starttimes)+1))

    pixel_times = np.full(fd_shape, np.nan, dtype=np.float32)

    splits = np.cumsum(line_starttimes.values)[:-1]
    for chunk,start_time,end_time in zip(np.split(pixel_times, splits, axis=0), line_times[:-1], line_times[1:]):
        chunk[:] = np.linspace(start_time, end_time, chunk.shape[1])[np.newaxis]
    return pixel_times


def meteosat_get_time_offset(d):
    acq_time = d.acq_time
    mask = acq_time.notnull()
    start_time = acq_time[mask].min()
    time_offset = (acq_time - start_time).astype(np.float64).where(mask)
    start_time = pd.to_datetime(start_time.item())
    return start_time, time_offset.values/1e9


def meteosat_estimate_pixel_time_offsets(time_offset):
    idx = np.arange(len(time_offset))
    new_idx = np.linspace(0, max(idx), len(time_offset)**2)
    interp = scipy.interpolate.interp1d(idx, time_offset, fill_value='extrapolate')
    pixel_times_flip = interp(new_idx).reshape((-1,len(time_offset)))

    pixel_times = pixel_times_flip[:,::-1]
    return pixel_times



def goes_pixel_time_offset(ABI_SCAN_DIR):
    timeline_file = ABI_SCAN_DIR / 'ABI-Timeline05B_Mode 6A_20190612-183017.nc'
    ds = xr.open_dataset(timeline_file)
    pixel_times = ds.FD_pixel_times
    mask = pixel_times.notnull()
    time_offsets = (pixel_times).astype(np.float64).where(mask).values * 1e-9
    ds.close()
    # They must like MATLAB
    time_offsets = time_offsets.T
    return time_offsets


def goes_start_time(files):
    f = Path(min(files))
    start = f.name.split('_')[3]
    return datetime.strptime(start[:-1], 's%Y%j%H%M%S') + timedelta(microseconds=int(start[-1])*.1e6)
