import os
import sys


if __name__ == '__main__':
    cmd = f'python -m nuitka --mingw64 --show-progress --standalone --output-dir=./{sys.argv[1]} ./pysimpledlna.py'
    print(cmd)
    os.system(cmd)
