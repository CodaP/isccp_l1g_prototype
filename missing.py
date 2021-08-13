from pathlib import Path

l1b = Path('l1b')
final = Path('final')

l1b_dirs = set(i.name for i in l1b.glob('*'))
final_dirs = set(i.name for i in final.glob('*'))
missing = l1b_dirs - final_dirs
for d in sorted(missing):
    print(d)
