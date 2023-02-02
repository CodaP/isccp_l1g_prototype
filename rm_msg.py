
from pathlib import Path
import shutil
from make_sample import band_dir_path, COMP_CACHE
from datetime import datetime


f = 'decompress_errors.txt'
with open(f) as fp:
    for line in fp:
        l1b,size = line.strip().split()
        l1b = Path(l1b)
        # l1b/2019/201907/20190701/20190701T1900/m11/temp_09_70um/H-000-MSG4__-MSG4________-IR_097___-000006___-201907011900-C_
        if size != 'None':
            band = l1b.parent.name
            #sat = l1b.parent.parent.name
            dt = l1b.parent.parent.parent.name
            dt = datetime.strptime(dt, '%Y%m%dT%H%M')
            path = COMP_CACHE / dt.strftime('%Y') / dt.strftime('%Y%m') / dt.strftime('%Y%m%d') / dt.strftime('%Y%m%dT%H%M')
            files = list(path.glob(f'{band}*.nc'))
            if len(files) > 0:
                for f2 in files:
                    print(f2)
                    f2.unlink()

