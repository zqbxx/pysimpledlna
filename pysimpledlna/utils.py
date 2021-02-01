from xml.dom.minidom import Childless
from enum import Enum
import time
import os
import appdirs


class ThreadStatus(Enum):
    STOPPED = 1
    RUNNING = 2
    PAUSED = 3


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


def get_user_data_dir():
    user_dir = appdirs.user_data_dir('pysimpledlna', 'wx_c')
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    return os.path.abspath(user_dir)


def get_desktop_dir():

    import winreg

    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
    )
    desktop, _ = winreg.QueryValueEx(key, 'Desktop')
    return desktop
