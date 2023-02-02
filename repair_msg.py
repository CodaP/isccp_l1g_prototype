from test_decompress import decompress_one
from pathlib import Path
import shutil

def repair_msg_l1b_cache(l1b, scratch):
    l1b = Path(l1b)
    size = decompress_one(l1b, scratch)
    if size is None:
        return

    if not l1b.is_symlink():
        raise ValueError(f"{l1b} is not a symlink, don't risk it")
    l1b_resolve = l1b.resolve()
    if l1b_resolve.stat().st_size == size:
        return
    print('Repairing',l1b)
    l1b.unlink()
    try:
        shutil.copy(l1b_resolve, l1b)
        print(l1b)
        print(l1b.stat().st_size, size)
        with open(l1b,'a') as fp2:
            fp2.truncate(size)
        print(l1b.stat().st_size, size)
        print()
    except:
        print("Error while fixing MSG L1b. Putting link back")
        l1b.symlink_to(l1b_resolve)
        raise

            
