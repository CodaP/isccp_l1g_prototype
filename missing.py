from pathlib import Path
from find_files import gen_path, band_list, ROOT
from datetime import datetime
from tqdm import tqdm
import pandas as pd

bands = band_list()

dts = set()
with open('date_list.txt') as fp:
    for dt in fp:
        dt = datetime.strptime(dt.strip(),'%Y%m%dT%H%M')
        dts.add(dt)
dts = sorted(dts)

index = pd.read_csv('index.csv')
indexed_files = set(index.f)

num_missing = 0
with open('missing.txt','w') as missing:
    with tqdm(dts) as bar:
        for dt in bar:
            for band in bands:
                f = gen_path(band, dt)
                if str(f) not in indexed_files:
                    num_missing += 1
                    bar.write(str(f))
                    missing.write(str(f)+'\n')
                    bar.set_description(str(num_missing))
