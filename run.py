import subprocess
import pandas as pd


times = pd.date_range('20211101','20211201',freq='1D')

procs = []


for start,end in zip(times, times[1:]):
    #args = ['srun','--pty','--time','02:00:00', 'python', 'collect_l1b.py', start.strftime('%Y%m%dT%H%M'), end.strftime('%Y%m%dT%H%M')]
    #print(' '.join(args))
    #subprocess.run(args)
    args = ['srun','-p','cirrus','-c','8','--time','03:00:00','--mem=20G','python','make_composite.py','--freq=3H',start.strftime('%Y%m%dT%H%M'), end.strftime('%Y%m%dT%H%M')]
    p = subprocess.Popen(args)
    print(' '.join(args))
    #p.wait()
    procs.append(p)

for p in procs:
    try:
        p.wait()
    except KeyboardInterrupt:
        for p in procs:
            p.terminate()

