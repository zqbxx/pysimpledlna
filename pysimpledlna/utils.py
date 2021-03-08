from xml.dom.minidom import Childless
from enum import Enum
import time
import os
import appdirs
import socket
import json


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


def get_free_tcp_port():
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.bind(('', 0))
    addr, port = tcp.getsockname()
    tcp.close()
    return port


class Playlist:

    def __init__(self, file_path, min_save_interval=30):
        self.file_path = file_path
        self._current_index = 0
        self._current_pos = 0
        self._file_list = []
        self.min_save_interval = min_save_interval
        self.last_save = 0

    def load_playlist(self):
        if not os.path.isfile(self.file_path):
            return
        jo = None
        import codecs
        with open(self.file_path, 'r', encoding="utf-8-sig") as f:
            #line = f.readlines()
            jo = json.loads(f.read())
        if jo.get('current_index') is not None:
            self._current_index = int(jo.get('current_index'))
        if jo.get('current_pos') is not None:
            self._current_pos = int(jo.get('current_pos'))
        if jo.get('file_list') is not None:
            self._file_list = jo.get('file_list')

    def save_playlist(self, force=False):
        current = time.time()
        interval = current - self.last_save
        if force or interval >= self.min_save_interval:
            json_str = json.dumps({
                "current_index": self._current_index,
                "current_pos": self._current_pos,
                "file_list": self._file_list,
            }, ensure_ascii=False, indent=2)
            with open(self.file_path, 'w', encoding="utf-8") as fp:
                fp.write(json_str)
            self.last_save = current

    @property
    def current_index(self):
        return self._current_index

    @current_index.setter
    def current_index(self, current_index):
        self._current_index = current_index

    @property
    def current_pos(self):
        return self._current_pos

    @current_pos.setter
    def current_pos(self, current_pos):
        self._current_pos = current_pos

    @property
    def file_list(self):
        return self._file_list

    @file_list.setter
    def file_list(self, file_list):
        self._file_list = file_list
