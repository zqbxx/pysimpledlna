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
    else:
        play()


def play():

    path = sys.argv[1]
    current_file = sys.argv[0]

    if not os.path.isdir(path):
        return

    file_list = [os.path.join(path, f) for f in os.listdir(path)
                 if f.endswith('.mp4') or f.endswith('.mkv')]

    sys.argv = [current_file, 'play', '-i'] + file_list

    cli_main()


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


def copy_to_user_dir(pkg_path, file_name):
    file_data = pkgutil.get_data("pysimpledlna", pkg_path)
    user_dir = get_user_data_dir()
    target_file_path = os.path.join(user_dir, file_name)
    with open(target_file_path, 'wb') as f:
        f.write(file_data)
    return target_file_path


if __name__ == '__main__':
    main()
