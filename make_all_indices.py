from make_index import main
from pathlib import Path
import warnings
INDEX = Path('index')
L1B = Path('l1b')

for sat in ['g16','g17','h8']:
    if sat.startswith('g'):
        bands = [14,1,2]
    else:
        bands = [14,1,3]
    for band in bands:
        band_dir = next((L1B / sat).glob('*')) / f'{band:02d}'
        assert band_dir.is_dir(), str(band_dir)
        out_dir = INDEX / sat / f'{band:02d}'
        if (out_dir / 'src_index.dat').exists():
            print(f'Already have {sat} {band:02d}')
            continue
        files = list(band_dir.glob('*'))
        print(f'Running {str(files[0])} -> {str(out_dir)}')
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            main(files, out_dir)

