import make_animation
import subprocess
first = True
procs = []
for variable in make_animation.PLOT_DATA:
    if first:
        stdout = None
        stderr = None
    else:
        stdout = subprocess.DEVNULL
        stderr = subprocess.DEVNULL
    args = ['python', 'make_animation.py', '--freq=3H', '-o', 'dat/animations/', variable, '2018-11-22', '2018-12-22']
    print(' '.join(args))
    p = subprocess.Popen(args, stdout=stdout, stderr=stderr)
    procs.append(p)
    first = False
for p in procs:
    p.wait()