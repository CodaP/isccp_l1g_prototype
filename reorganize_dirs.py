from pathlib import Path
from datetime import datetime

def move(ROOT):
    old_style_dirs = sorted([f for f in ROOT.glob('*') if len(f.name) == 13])

    for d in old_style_dirs:
        dt = datetime.strptime(d.name, '%Y%m%dT%H%M')
        suffix = dt.strftime('%Y/%Y%m/%Y%m%d/%Y%m%dT%H%M')
        new_d = ROOT / suffix
        if not new_d.is_dir():
            new_d.parent.mkdir(exist_ok=True, parents=True)
            d.rename(new_d)


if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('root')
    args = parser.parse_args()
    move(Path(args.root))

