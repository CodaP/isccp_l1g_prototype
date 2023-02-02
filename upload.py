from pathlib import Path
from ftplib import FTP, error_perm, error_temp
import pandas as pd
from find_files import all_files
from tqdm import tqdm


def filter_files(dts):
    for dt,k,f in all_files():
        if dt in dts:
            yield f


def try_mkd(ftp, d):
    try:
        ftp.mkd(d)
    except error_perm:
        pass


def file_exists(ftp, f):
    try:
        ftp.nlst(str(f))
        return True
    except error_temp:
        return False



def upload(ftp, root, f, overwrite=False):
    dst = Path('/ISCCP-NG/L1g') / root / f.relative_to(Path('dat/final'))
    try_mkd(ftp, str(dst.parent.parent.parent.parent.parent))
    try_mkd(ftp, str(dst.parent.parent.parent.parent))
    try_mkd(ftp, str(dst.parent.parent.parent))
    try_mkd(ftp, str(dst.parent.parent))
    try_mkd(ftp, str(dst.parent))
    if not file_exists(ftp, dst) or overwrite:
        with open(f,'rb') as fp:
            ftp.storbinary(f'STOR {dst}', fp)
        return 1
    else:
        return 0


def main(root, start, end, freq):
    ftp = FTP('ftp.ssec.wisc.edu')
    _ = ftp.login()
    try:
        dts = set(pd.date_range(start, end, freq=freq))
        num_uploaded = 0
        with tqdm(filter_files(dts)) as bar:
            for f in bar:
                num_uploaded += upload(ftp, root, f)
                bar.set_description(f'uploaded: {num_uploaded}')
    finally:
        ftp.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('root_name')
    parser.add_argument('start')
    parser.add_argument('end')
    parser.add_argument('--freq', default='30min', required=False)
    args = parser.parse_args()
    start = pd.to_datetime(args.start)
    end = pd.to_datetime(args.end)
    main(args.root_name, start,end,args.freq)

