import os
import sys
from utils import *

def debug_xor(foo):
    print('is xor')

if sys.argv[0] == 'debug-rand.py':
    sys.stdout.write(os.urandom(int(sys.argv[1])))
else:
    fs = []
    for f in sys.argv[1:]:
        fs.append(open(f, 'r').read())
    sys.stdout.write(xor_strings(*fs))
