import numpy as np
import pandas as pd

def read_int(fp, dtype):
    bytes = np.array([0], dtype=dtype).nbytes
    buf = fp.read(bytes)
    #print(buf)
    return np.frombuffer(buf, dtype=dtype)[0]

def mjd2dt(mjd):
    epoch = np.datetime64('1858-11-17 00:00')
    day2usec = 24 * 3600 * 1E6
    mjd_usec = (mjd*day2usec).astype('timedelta64[us]')
    return epoch + mjd_usec

def get_obs_time_block(f):
    with open(f, 'rb') as fp:
        for i in range(1,9):
            bid = read_int(fp, np.uint8)
            blen = read_int(fp, np.uint16)
            fp.seek(blen-3, 1)

        bid = read_int(fp, np.uint8)
        blen = read_int(fp, np.uint16)
        time_block = fp.read(blen-3)
    return time_block


def parse_time_block(time_block):
    nobs = np.frombuffer(time_block[:2], dtype=np.uint16)[0]
    obs_block = time_block[2:]
    lines = {}
    for i in range(nobs):
        pair = obs_block[i*10:i*10+10]
        line = np.frombuffer(pair[:2], dtype=np.uint16)[0]
        ob_time = pair[2:]
        mjd = np.frombuffer(ob_time, dtype=np.float64)[0]
        dt = mjd2dt(mjd)
        lines[line] = dt
    return lines



def get_scan_time(f):
    time_block = get_obs_time_block(f)
    lines = parse_time_block(time_block)
    return lines

