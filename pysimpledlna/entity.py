import fnmatch
import json
import os
import re
import time
from enum import Enum
from pathlib import Path
from typing import List, Dict, Union


class ThreadStatus(Enum):
    STOPPED = 1
    RUNNING = 2
    PAUSED = 3


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


class Settings:

    def __init__(self, file_path):
        self.file_path = file_path
        self.d: Dict[str, Union[str, bool]] = self.read()
        self.original = self.d.copy()
        if 'default_device' not in self.d:
            self.d['default_device'] = ''
        if 'enable_ssl' not in self.d:
            self.d['enable_ssl'] = False

    def set_default_device(self, url: str):
        self.d['default_device'] = url

    def set_enable_ssl(self, enable_ssl:bool):
        self.d['enable_ssl'] = enable_ssl

    def get_default_device(self) -> str:
        return self.d['default_device']

    def get_enable_ssl(self) -> bool:
        return self.d['enable_ssl']

    def read(self) -> Dict[str, Union[str, bool]]:
        try:
            with open(self.file_path, 'r', encoding='utf-8-sig') as f:
                d: Dict[str, Union[str, bool]] = json.load(f)
                return d
        except:
            return {}    # empty dict

    def write(self) -> None:
        if self.d == self.original:
            return
        self._make_dir()
        with open(self.file_path, "w", encoding='utf-8') as f:
            json.dump(self.d, f, indent=2)

    def _make_dir(self) -> None:
        folder = Path(self.file_path).parent
        if not folder.is_dir():
            folder.mkdir(parents=True)
