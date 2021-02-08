import sys
import os
import pkgutil
import sysconfig

from pysimpledlna.cli import main as cli_main
from pysimpledlna.utils import get_user_data_dir, get_desktop_dir
import subprocess

install_reg = '''Windows Registry Editor Version 5.00

[HKEY_CLASSES_ROOT\Directory\shell\DLNA Share]

[HKEY_CLASSES_ROOT\Directory\shell\DLNA Share\command]
@="\\"{Path}\\" \\"%1\\""
'''
uninstall_reg = """Windows Registry Editor Version 5.00
[-HKEY_CLASSES_ROOT\Directory\shell\DLNA Share\command]
[-HKEY_CLASSES_ROOT\Directory\shell\DLNA Share]
"""


def main():

    action = sys.argv[1]

    if action == 'install':
        install()
    elif action == 'uninstall':
        uninstall()
    else:
        play()


def play():

    path = sys.argv[1]
    current_file = sys.argv[0]

    if not os.path.isdir(path):
        return

    file_list = [os.path.join(path, f) for f in os.listdir(path)
                 if f.endswith('.mp4') or f.endswith('.mkv')]

    for file_path in file_list:
        print(os.path.split(file_path)[1])

    sys.argv = [current_file, 'play', '-a', '-i'] + file_list

    try:
        cli_main()
    finally:
        input('\n press any key to continue')
        sys.exit()


def install():

    scripts_dir = sysconfig.get_path('scripts')
    target = os.path.join(scripts_dir, 'pysimpledlnaW.exe')
    target = target.replace('\\', '\\\\')

    desktop = get_desktop_dir()
    install_context_menu_file_path = os.path.join(desktop, 'PYSD安装右键菜单.reg')

    with open(install_context_menu_file_path, 'w') as f:
        f.write(install_reg.format(**{'Path': target}))

    os.system(install_context_menu_file_path)

    input('press any key to continue')


def uninstall():

    desktop = get_desktop_dir()
    uninstall_context_menu_file_path = os.path.join(desktop, 'PYSD删除右键菜单.reg')

    with open(uninstall_context_menu_file_path, 'w') as f:
        f.write(uninstall_reg)

    os.system(uninstall_context_menu_file_path)

    input('press any key to continue')


if __name__ == '__main__':
    main()
