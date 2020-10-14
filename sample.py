import all_together
import pandas as pd
from multiprocessing import Pool
from tqdm import tqdm

def doit(dt):
    return all_together.main(dt, progress=False)

dts = pd.date_range('2020-10-01','2020-10-02',freq='30min')
with Pool(8) as pool:
    with tqdm(pool.imap(doit, dts), total=len(dts)) as bar:
        for _ in bar:
            pass

