from make_index import main, get_max_satzen
from pathlib import Path
import warnings
INDEX = Path('dat/index')
L1B = Path('dat/l1b')


satzen_ncs = ['dat/satzen_cache/g16_satzen.nc','dat/satzen_cache/g17_satzen.nc','dat/satzen_cache/h8_satzen.nc']

r_sample = 2e3

for sat,satzen_nc in zip(['g16','g17','h8'], satzen_ncs):
    if sat.startswith('g'):
        bands = ['14','01','02']
        r_footprints = [1e3,1e3,1e3]
    else:
        bands = ['14','01','03']
        r_footprints = [1e3,1e3,1e3]
    for band, r_footprint in zip(bands, r_footprints):
        max_satzen = get_max_satzen(r_footprint, r_sample)
        print('max satzen:', max_satzen)
        band_dir = next((L1B / sat).glob('*')) / f'{band}'
        assert band_dir.is_dir(), str(band_dir)
        out_dir = INDEX / sat / f'{band}'
        if (out_dir / 'src_index.dat').exists():
            print(f'Already have {sat} {band}')
            continue
        files = list(band_dir.glob('*'))
        print(f'Running {str(files[0])} -> {str(out_dir)}')
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            main(files, out_dir, satzen_nc, max_satzen)

