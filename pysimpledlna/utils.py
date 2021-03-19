import fnmatch
import re
from typing import List
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

    def __init__(self, file_path, filter: str = None, input: List[str] = None, min_save_interval=30):
        self.file_path = file_path
        self._current_index = 0
        self._current_file_path = None
        self._current_pos = 0
        self._file_list = []
        self.min_save_interval = min_save_interval
        self.last_save = 0
        self._skip_head = 0
        self._skip_tail = 0
        self._filter = filter
        self._input = input

    def filter_files(self):
        if self._filter is not None:
            regex = fnmatch.translate(self._filter)
            pattern = re.compile(regex)
        self._file_list = [os.path.join(input_dir, file_name) for input_dir in self._input for file_name in
                           os.listdir(input_dir) if pattern is not None and pattern.search(file_name) is not None]

    def load_playlist(self):
        if not os.path.isfile(self.file_path):
            return
        jo = None
        import codecs
        with open(self.file_path, 'r', encoding="utf-8-sig") as f:
            jo = json.loads(f.read())
        if jo.get('file_list') is not None:
            self._file_list = jo.get('file_list')
        if jo.get('current_index') is not None:
            self._current_index = int(jo.get('current_index'))
            self._current_file_path = self._file_list[self._current_index]
        if jo.get('current_pos') is not None:
            self._current_pos = int(jo.get('current_pos'))
        if jo.get('skip_head') is not None:
            self._skip_head = jo.get('skip_head')
        if jo.get('skip_tail') is not None:
            self._skip_tail = jo.get('skip_tail')
        if jo.get('filter') is not None:
            self._filter = jo.get('filter')
        if jo.get('input') is not None:
            self._input = jo.get('input')

    def save_playlist(self, force=False):
        current = time.time()
        interval = current - self.last_save
        if force or interval >= self.min_save_interval:
            json_str = json.dumps({
                "current_index": self._current_index,
                "current_pos": self._current_pos,
                "file_list": self._file_list,
                "skip_head": self._skip_head,
                "skip_tail": self._skip_tail,
                "filter": self._filter,
                "input": self._input,
            }, ensure_ascii=False, indent=2)
            with open(self.file_path, 'w', encoding="utf-8") as fp:
                fp.write(json_str)
            self.last_save = current

    def refresh_playlist(self):
        current_file = self._file_list[self._current_index]

        self.filter_files()

        self._current_index = 0

        for i, f in enumerate(self._file_list):
            if os.path.exists(current_file) and os.path.samefile(f, current_file):
                self._current_index = i
                break

        # 刷新后没有找到当前的文件，位置信息也需要清0
        if self._current_index == 0:
            self._current_pos = 0

        self.save_playlist(force=True)

    @property
    def current_file_path(self):
        return self._current_file_path

    @property
    def current_index(self):
        return self._current_index

    @current_index.setter
    def current_index(self, current_index):
        self._current_index = current_index
        self._current_file_path = self._file_list[self._current_index]

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

    @property
    def skip_head(self):
        return self._skip_head

    @skip_head.setter
    def skip_head(self, skip_head):
        self._skip_head = skip_head

    @property
    def skip_tail(self):
        return self._skip_tail

    @skip_tail.setter
    def skip_tail(self, skip_tail):
        self._skip_tail = skip_tail
