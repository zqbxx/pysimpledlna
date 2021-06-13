import sys
import os

exe_dir = sys.path[1]
lib_dir = os.path.join(exe_dir, 'lib')
dll_dir = os.path.join(exe_dir, 'dll')
sys.path.append(lib_dir)
os.environ["PATH"] = dll_dir + os.pathsep + os.environ["PATH"]
os.environ["nuitka"] = '0'
os.environ["nuitka_exe_dir"] = exe_dir
from pysimpledlna.cli import main

if __name__ == "__main__":
    main()
