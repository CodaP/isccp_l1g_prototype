from tqdm import tqdm
import subprocess
from pathlib import Path
import shutil


XRIT = Path('xrit/PublicDecompWT/xRITDecompress/xRITDecompress').absolute()
assert XRIT.exists()

SCRATCH = Path('/scratch')

def decompress_one(f, scratch):
    p = subprocess.run([str(XRIT), str(f.absolute())], cwd=scratch, capture_output=True)
    lines = list(p.stdout.decode().splitlines())
    expected = None
    for l in lines:
        if l.startswith('Expected'):
            expected = int(l.split(':')[1])
    return expected


def iter_files():
    for f in Path('l1b').glob('*/*/*/*/m11/*/H-000-*-00*C_'):
        yield f

def test_decompress_one():
    scratch = Path('./')
    f = Path('H-000-MSG4__-MSG4________-IR_039___-000006___-202007012200-C_')
    f = Path('l1b/2020/202007/20200701/20200701T0000/m11/temp_06_20um/H-000-MSG4__-MSG4________-WV_062___-000003___-202007010000-C_')
    print(decompress_one(f, scratch))


def main():
    previous = {}
    assert SCRATCH.is_dir()
    scratch = SCRATCH / 'test_decompress'
    if scratch.is_dir():
        shutil.rmtree(scratch)
    num_tests = 0
    with open('decompress_errors.txt','r+') as fp:
        for line in fp:
            l1b,size = line.strip().split()
            previous[l1b] = size
        with tqdm(iter_files(), disable=False) as bar:
            for f in bar:
                if str(f) not in previous:
                    try:
                        h = f.name[-15:][:10]
                        #bar.set_description(h)
                        scratch.mkdir()
                        expected = decompress_one(f,scratch)
                        line = str(f)+' '+str(expected)+'\n'
                        fp.write(line)
                        fp.flush()
                        #print(line)
                        num_tests += 1
                        bar.set_description(str(num_tests))
                    finally:
                        shutil.rmtree(scratch)

if __name__ == '__main__':
    main()
