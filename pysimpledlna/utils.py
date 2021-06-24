import random
from pathlib import Path
from xml.dom.minidom import Childless
import time
import os
import appdirs
import socket

BASE_RAND_STR = 'ABCDEFGHIGKLMNOPQRSTUVWXYZabcdefghigklmnopqrstuvwxyz0123456789'
BASE_RAND_STR_LEN = len(BASE_RAND_STR)


def random_str(str_len=16)->str:
    result_str = ''
    length = BASE_RAND_STR_LEN - 1
    for i in range(str_len):
        result_str += BASE_RAND_STR[random.randint(0, length)]
    return result_str


def is_in_nuitka() -> bool:
    t = os.environ.get("nuitka", None)
    return t is not None


def get_abs_path(rel_path=None) -> Path:

    if is_in_nuitka():
        if rel_path is None:
            return Path(os.environ.get('nuitka_exe_dir')) / Path(rel_path)
        else:
            return Path(os.environ.get('nuitka_exe_dir'))
    elif rel_path is not None:
        return Path(rel_path)
    else:
        return Path('.').absolute()


def get_element_data_by_tag_name(doc, tag_name, index=0, default=None) -> str:
    element = get_element_by_tag_name(doc, tag_name, index)
    child = element.firstChild
    if child is None:
        return default
    if not hasattr(child, 'data'):
        return default
    return child.data


def get_element_by_tag_name(doc, tag_name, index=0, default=Childless()):
    elements = doc.getElementsByTagName(tag_name)
    if len(elements) == 0:
        return default
    return elements[index]


def wait_interval(interval, start, end):
    dur = end - start
    rest = interval - dur
    if rest >= 0:
        time.sleep(rest)
    return rest


def to_seconds(t: str) -> int:
    s = 0
    a = t.split(':')
    try:
        s = int(a[0]) * 60 * 60 + int(a[1]) * 60 + int(a[2])
    except:
        return 0
    return s


def format_time(seconds) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return "%02d:%02d:%02d" % (h, m, s)


def get_user_data_dir():
    user_dir = appdirs.user_data_dir('pysimpledlna', 'wx_c')
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    return os.path.abspath(user_dir)


def get_playlist_dir(base, playlist):
    full_path = os.path.join(base, playlist)
    if not os.path.exists(full_path):
        os.makedirs(full_path)
    return os.path.abspath(full_path)


def get_desktop_dir():

    import winreg

    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
    )
    desktop, _ = winreg.QueryValueEx(key, 'Desktop')
    return desktop


def get_setting_file_path():
    user_dir = get_user_data_dir()
    return os.path.join(user_dir, 'settings.json')


def get_free_tcp_port():
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.bind(('', 0))
    addr, port = tcp.getsockname()
    tcp.close()
    return port


def is_tcp_port_occupied(port: int):
    tcp = None
    try:
        tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp.bind(('', port))
        tcp.close()
        return False
    except:
        return True
    finally:
        try:
            if tcp is not None:
                tcp.close()
        except:
            pass
