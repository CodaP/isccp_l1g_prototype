import subprocess
import pandas as pd
from find_files import extract_var
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

N = 10

with open('missing.txt') as fp:
    missing_files = list(fp)

missing_times = set()
for f in missing_files:
    f = Path(f)
    k = extract_var(f.name)
    if 'refl' in k or 'temp' in k:
        missing_times.add(datetime.strptime(f.parent.name, '%Y%m%dT%H%M'))

print(len(missing_times))

dts = [dt.strftime('%Y%m%dT%H%M') for dt in sorted(missing_times)]

def run_one(start):
    args = ['srun','--time','00:10:00','--mem=20G','-n1','python','make_sample.py',start]
    print(' '.join(args))
    p = subprocess.run(args)
    

with ThreadPoolExecutor(max_workers=N) as executor:
    list(executor.map(run_one, dts))


