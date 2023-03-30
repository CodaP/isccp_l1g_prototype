import subprocess
import pandas as pd
import asyncio
from pathlib import Path


async def main(n_workers):
    tasks = []
    for start,end in zip(dates, dates[1:]):
        end = end - pd.to_timedelta(1, unit='s')
        if DO_ANCIL:
            args = ['srun','-N1','-n1','-p','cirrus','-c','1','--time','01:00:00','--mem-per-cpu=3G',
                'python','make_ancil.py',
                '--sortdir',str(SORTDIR),
                f'--freq={freq}',start.strftime('%Y%m%dT%H%M'), end.strftime('%Y%m%dT%H%M')
            ]
            tasks.append(args)

        if DO_COLLECT:
            args = ['srun','-N1','-n1','-p','cirrus','-c','1','--time','01:00:00','--mem-per-cpu=3G',
                'python','collect_l1b.py',
                f'--freq={freq}',start.strftime('%Y%m%dT%H%M'), end.strftime('%Y%m%dT%H%M')
            ]
            tasks.append(args)
        if DO_SOLAR:
            args = ['srun','-N1','-n1','-p','cirrus','-c','1','--time','01:00:00','--mem-per-cpu=3G',
                'python','solar.py',
                f'--freq={freq}',start.strftime('%Y%m%dT%H%M'), end.strftime('%Y%m%dT%H%M')
            ]
            tasks.append(args)
        for sat in ['g16','g17','h8','m8','m11']:#,'m9']:
            if DO_TIMING:
                args = ['srun','-N1','-n1','-p','cirrus','-c','4','--time','01:00:00','--mem-per-cpu=3G','python','make_timing.py',
                    '--sortdir',str(SORTDIR),
                    f'--freq={freq}',
                    sat,start.strftime('%Y%m%dT%H%M'), end.strftime('%Y%m%dT%H%M')]
                tasks.append(args)
            if DO_GEOMETRY:
                args = ['srun','-N1','-n1','-p','cirrus','-c','4','--time','01:00:00','--mem-per-cpu=3G','python','make_geometry.py',
                    f'--freq={freq}',
                    sat,start.strftime('%Y%m%dT%H%M'), end.strftime('%Y%m%dT%H%M')]
                tasks.append(args)
        for k in VARIABLES:
            for sat in ['g16','g17','h8','m8','m11']:#,'m9']:
                if DO_SAMPLE:
                    args = ['srun','-N1','-n1','-p','cirrus','-c','4','--time','01:00:00','--mem-per-cpu=3G','python','make_sample.py',
                        #'--sortdir','dat/sample_cache/g16_g17_h8_m11_m9',
                        '--sortdir',str(SORTDIR),
                        f'--freq={freq}',
                        sat,k,start.strftime('%Y%m%dT%H%M'), end.strftime('%Y%m%dT%H%M')]
                    tasks.append(args)

            if DO_COMPOSITE:
                if FORCE:
                    force = ['-f']
                else:
                    force = []
                args = ['srun','-N1','-n1','-p','cirrus','-c','1','--time','01:00:00','--mem-per-cpu=3G',
                    'python','make_composite.py',
                    #'-w','dat/sample_cache/g16_g17_h8_m11_m9/wmo_id.nc',
                    *force,
                    '-w',str(WMO_ID_FILE),
                    f'--freq={freq}',k,start.strftime('%Y%m%dT%H%M'), end.strftime('%Y%m%dT%H%M')
                ]
                tasks.append(args)
        for k in AUX_VARS:
            if DO_AUX_COMPOSITE:
                args = ['srun','-N1','-n1','-p','cirrus','-c','1','--time','01:00:00','--mem-per-cpu=3G',
                    'python','make_composite.py',
                    '-w',str(WMO_ID_FILE),
                    f'--freq={freq}',k,start.strftime('%Y%m%dT%H%M'), end.strftime('%Y%m%dT%H%M')
                ]
                tasks.append(args)

    print(len(tasks), 'tasks')
    
    workers = []
    running_procs = set()
    for _ in range(n_workers):
        workers.append(asyncio.create_task(worker(tasks, running_procs)))
    try:
        await asyncio.gather(*workers)
    except:
        for p in running_procs:
            p.terminate()
        raise
    

async def worker(tasks, running_procs):
    while True:
        if len(tasks) > 0:
            args = tasks.pop(0)
            p = await asyncio.create_subprocess_exec(args[0], *args[1:])
            running_procs.add(p)
            await p.wait()
            running_procs.remove(p)
        else:
            return

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--freq',default='30min')
    parser.add_argument('--sortdir')
    parser.add_argument('stage')
    parser.add_argument('dt')
    parser.add_argument('end', nargs='?')
    args = parser.parse_args()
    dt = pd.to_datetime(args.dt)
    DO = args.stage
    freq = args.freq
    SORTDIR = Path(args.sortdir)
    WMO_ID_FILE = SORTDIR / 'wmo_id.nc'

    if args.end is not None:
        end = pd.to_datetime(args.end)
        dates = pd.date_range(dt, end, freq='1D')
    else:
        dates = [dt]

    procs = []

    VARIABLES = {
    #'refl_00_47um',
    'refl_00_65um',
    #'refl_00_51um',
    'refl_00_86um',
    'refl_01_60um',
    #'refl_02_20um',
    'temp_03_80um',
    #'temp_06_20um',
    #'temp_06_70um',
    'temp_07_30um',
    'temp_08_60um',
    #'temp_09_70um',
    'temp_10_40um',
    'temp_11_00um',
    'temp_12_00um',
    'temp_13_30um',
    }
    VARIABLES = {'temp_11_00um_min','temp_11_00um_max', 'refl_00_65um_min','refl_00_65um_max'}
    AUX_VARS = {
    'pixel_time',
    'satellite_zenith_angle',
    'satellite_azimuth_angle'
    }

    DO_COLLECT=DO=='collect'
    DO_SOLAR=DO=='solar'
    DO_TIMING=DO=='timing'
    DO_SAMPLE=DO=='sample'
    DO_COMPOSITE=DO=='composite'
    DO_AUX_COMPOSITE=DO=='aux'
    DO_GEOMETRY=DO=='geometry'
    DO_ANCIL=DO=='ancil'

    FORCE=False

    asyncio.run(main(17))

