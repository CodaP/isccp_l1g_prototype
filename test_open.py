from make_sample import read_scene, band_dir_path, L1B_DIR
from datetime import datetime
from utils import _readers


def main(sat,band,dt):
    band_dir = band_dir_path(L1B_DIR, dt, sat, band)
    print(band_dir)
    files = list(band_dir.glob('*'))
    reader = _readers[sat[0]]
    v, area = read_scene(files, reader)
    v[:]

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('sat')
    parser.add_argument('band')
    parser.add_argument('dt')
    args = parser.parse_args()
    dt = datetime.strptime(args.dt, '%Y-%m-%dT%H:%M')
    main(args.sat, args.band, dt)
