import sys

def debug_rand(foo):
    print('is rand')

def debug_xor(foo):
    print('is xor')

if sys.argv[0] == 'debug-rand.py':
    debug_rand(sys.argv[1:])
else:
    debug_xor(sys.argv[1:])
