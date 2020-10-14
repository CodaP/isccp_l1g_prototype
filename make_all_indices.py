from make_index import main, get_max_satzen
from pathlib import Path
import warnings
INDEX = Path('index')
L1B = Path('l1b')


satzen_ncs = ['satzen_cache/g16_satzen.nc','satzen_cache/g17_satzen.nc','satzen_cache/h8_satzen.nc']

r_sample = 2e3

for sat,satzen_nc in zip(['g16','g17','h8'], satzen_ncs):
    if sat.startswith('g'):
        bands = [14,1,2]
        r_footprints = [1e3,1e3,1e3]
    else:
        bands = [14,1,3]
        r_footprints = [1e3,1e3,1e3]
    for band, r_footprint in zip(bands, r_footprints):
        max_satzen = get_max_satzen(r_footprint, r_sample)
        print('max satzen:', max_satzen)
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
            main(files, out_dir, satzen_nc, max_satzen)

