import fnmatch
import json
import os
import re
import time
from pathlib import Path
from typing import List, Dict, Union


class Playlist:

    def __init__(self, file_path: str, _type: str, _filter: str = None, min_save_interval=30):
        self._current_index = 0
        self._current_media_path = None
        self._current_pos = 0
        self._media_list = []
        self._skip_head = 0
        self._skip_tail = 0
        self._min_save_interval = 30
        self._last_save = 0
        self._filter = _filter
        self._type = _type

        self._jso = None
        self.file_path = file_path

    @staticmethod
    def get_playlist(file_path: str):
        with open(file_path, 'r', encoding="utf-8-sig") as f:
            jso = json.loads(f.read())
            _type = jso.get('type')
            playlist = None
            if type == 'LocalFile':
                playlist = LocalFilePlaylist(file_path)
            elif type == 'LocalTempFile':
                playlist = LocalTempFilePlaylist(file_path)
            else:
                playlist = LocalFilePlaylist(file_path)
                playlist._type = 'LocalFile'
            playlist.load_playlist()
            return playlist

    def can_save(self):
        current = time.time()
        interval = current - self._last_save
        return interval >= self._min_save_interval

    def get_playlist_data(self):
        return {
                'type': self._type,
                "current_index": self._current_index,
                "current_pos": self._current_pos,
                "file_list": self._media_list,
                "skip_head": self._skip_head,
                "skip_tail": self._skip_tail,
                "filter": self._filter,
            }

    def save_playlist_dict(self, data: dict):
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        with open(self.file_path, 'w', encoding="utf-8") as fp:
            fp.write(json_str)
        self._last_save = time.time()

    def clear(self):
        self._current_index = 0
        self._current_media_path = None
        self._current_pos = 0
        self._media_list = []
        self._skip_head = 0
        self._skip_tail = 0
        self._filter = '*'
        self._last_save = 0

        self._jso = None

    def load_playlist(self):
        self.clear()
        if not os.path.isfile(self.file_path):
            return
        with open(self.file_path, 'r', encoding="utf-8-sig") as f:
            self._jso = json.loads(f.read())
        if self._jso.get('file_list') is not None:
            self._media_list = self._jso.get('file_list')
        if self._jso.get('current_index') is not None:
            self._current_index = int(self._jso.get('current_index'))
            self._current_media_path = self._media_list[self._current_index]
        if self._jso.get('current_pos') is not None:
            self._current_pos = int(self._jso.get('current_pos'))
        if self._jso.get('skip_head') is not None:
            self._skip_head = self._jso.get('skip_head')
        if self._jso.get('skip_tail') is not None:
            self._skip_tail = self._jso.get('skip_tail')
        if self._jso.get('filter') is not None:
            self._filter = self._jso.get('filter')
        if self._jso.get('type') is not None:
            self._type = self._jso.get('type')
        else:
            self._filter = "*"

    def save_playlist(self, force=False):
        pass

    def refresh_playlist(self):
        pass

    @property
    def current_file_path(self):
        return self._current_media_path

    @property
    def current_index(self):
        return self._current_index

    @current_index.setter
    def current_index(self, current_index):
        self._current_index = current_index
        self._current_media_path = self._media_list[self._current_index]

    @property
    def current_pos(self):
        return self._current_pos

    @current_pos.setter
    def current_pos(self, current_pos):
        self._current_pos = current_pos

    @property
    def media_list(self):
        return self._media_list

    @media_list.setter
    def media_list(self, media_list):
        self._media_list = media_list

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


class LocalFilePlaylist(Playlist):

    def __init__(self, file_path: str, _filter: str = None, input: List[str] = None, min_save_interval=30):
        Playlist.__init__(self, file_path, 'LocalFile', _filter, min_save_interval)
        self._input = input

    def get_playlist_name(self):
        return Path(self.file_path).stem

    def clear(self):
        super().clear()
        self._input = []

    def filter_files(self):

        self._media_list.clear()

        if self._filter is not None:
            regex = fnmatch.translate(self._filter)
            pattern = re.compile(regex)

        filter_str = self._filter if self._filter is not None else '*'

        for input_dir in self._input:
            input_dir_path = Path(input_dir)
            self._media_list += [str(fpath) for fpath in input_dir_path.glob(filter_str) if fpath.is_file()]

    def load_playlist(self):
        super().load_playlist()
        self._input: List[str] = []
        input_dirs = self._jso.get('input')
        if input_dirs is None:
            if len(self._media_list) > 0:
                input_dirs = [str(Path(self._media_list[0]).parent)]

        for input_dir in input_dirs:
            input_dir_path = Path(input_dir)
            if input_dir_path.exists() and input_dir_path.is_dir():
                self._input.append(str(input_dir_path))

    def save_playlist(self, force=False):
        if force or self.can_save():
            data = self.get_playlist_data()
            data.update({
                "input": self._input,
            })
            self.save_playlist_dict(data)

    def refresh_playlist(self):
        if self._input is None:
            return

        current_file = self._media_list[self._current_index]

        self.filter_files()

        self._current_index = 0

        for i, f in enumerate(self._media_list):
            if os.path.exists(current_file) and os.path.samefile(f, current_file):
                self._current_index = i
                break

        # 刷新后没有找到当前的文件，位置信息也需要清0
        if self._current_index == 0:
            self._current_pos = 0

        self.save_playlist(force=True)


class LocalTempFilePlaylist(LocalFilePlaylist):

    def __init__(self, file_path: str):
        super().__init__(file_path, None, [], 30)
        self._type = 'LocalTempFile'

    def refresh_playlist(self):
        pass

    def filter_files(self):
        pass


class PlayListWrapper(Playlist):

    def __init__(self):
        self.playlist = None


class Settings:

    def __init__(self, file_path):
        self.file_path = file_path
        self.d: Dict[str, Union[str, bool, int, List]] = self.read()
        self.original = self.d.copy()
        if 'default_device' not in self.d:
            self.d['default_device'] = ''
        if 'default_devices' not in self.d:
            self.d['default_devices'] = list()
        if 'enable_ssl' not in self.d:
            self.d['enable_ssl'] = False
        if 'cert_file' not in self.d:
            self.d['cert_file'] = ''
        if 'key_file' not in self.d:
            self.d['key_file'] = ''
        if 'default_port' not in self.d:
            self.d['default_port'] = 18000

    def set_default_device(self, url: str):
        self.d['default_device'] = url

    def set_default_devices(self, url: str):
        self.d['default_devices'] = [u.strip() for u in url.split(';') if len(u.strip()) > 0]

    def set_enable_ssl(self, enable_ssl:bool):
        self.d['enable_ssl'] = enable_ssl

    def set_cert_file(self, cert_file: str):
        self.d['cert_file'] = cert_file

    def set_key_file(self, key_file: str):
        self.d['key_file'] = key_file

    def set_default_port(self, default_port: int):
        self.d['default_port'] = default_port

    def get_default_device(self) -> str:
        return self.d['default_device']

    def get_default_devices(self) -> List[str]:
        return self.d['default_devices']

    def get_enable_ssl(self) -> bool:
        return self.d['enable_ssl']

    def get_cert_file(self):
        return self.d['cert_file']

    def get_key_file(self):
        return self.d['key_file']

    def get_default_port(self):
        return self.d['default_port']

    def read(self) -> Dict[str, Union[str, bool]]:
        try:
            with open(self.file_path, 'r', encoding='utf-8-sig') as f:
                d: Dict[str, Union[str, bool, int]] = json.load(f)
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
