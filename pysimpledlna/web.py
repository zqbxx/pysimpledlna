import json
import os
import time
from pathlib import Path
from typing import Callable, List, Tuple

from bottle import request, static_file, abort, HTTPResponse
from pysimpledlna.entity import Playlist, PlayListWrapper

from pysimpledlna.ac import ActionController
from pysimpledlna.dlna import DefaultResource
from pysimpledlna.ui.terminal import PlayerStatus
from pysimpledlna.utils import format_time


class WebRoot(DefaultResource):

    def __init__(self, ac: ActionController, web_root: Path, index: int):
        super().__init__(f'/s{index}/<filepath:path>', method=['GET', 'POST'])
        self.index = index
        self.ac = ac
        self.render = self.serve_static
        self.web_root = web_root

    def get_player_page_url(self):
        dlna_server = self.ac.device.dlna_server
        protocol = 'http' + ('s' if dlna_server.is_ssl_enabled else '')
        return protocol + '://' + dlna_server.server_ip + ':' + str(dlna_server.server_port) + '/s' + str(self.index) + '/player.html'

    def serve_static(self, filepath):

        if filepath == 'js/app.js':

            return self.dynamic_content(filepath=filepath,
                                        content_type='application/javascript',
                                        data_map={'{device_key}': self.ac.device.device_key},
                                        encoding='utf-8')

        elif filepath == 'player.html':
            return self.dynamic_content(filepath=filepath,
                                        content_type='text/html',
                                        data_map={'{randomstr}': str(time.time())},
                                        encoding='utf-8')

        response = static_file(filepath, root=str(self.web_root.absolute()))
        response['Last-Modified'] = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())

        return response

    def dynamic_content(self, filepath, content_type, data_map, encoding='utf-8'):
        dynamic_file = self.web_root / Path(filepath)
        dynamic_file_content = dynamic_file.read_text(encoding)
        replaced_content = dynamic_file_content
        for k, v in data_map.items():
            replaced_content = replaced_content.replace(k, v)
        replaced_bytes = replaced_content.encode(encoding)

        headers = dict()
        headers['Content-Encoding'] = encoding
        headers['Content-Type'] = content_type
        headers['Content-Length'] = len(replaced_bytes)
        headers["Accept-Ranges"] = "bytes"
        headers["Last-Modified"] = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
        return HTTPResponse(replaced_bytes, **headers)


class DLNAService(DefaultResource):

    def __init__(self,
                 ac: ActionController,
                 play_list: PlayListWrapper,
                 playlist_accessor: Callable[[], List[Tuple[str, str]]],
                 switch_playlist: Callable[[List[str], List[str]], None],
                 switch_video: Callable[[List[str], List[str]], None]) -> None:
        super().__init__(f'/api/{ac.device.device_key}', method=['GET', 'POST'])
        self.ac = ac
        self.render = self.render_request
        self._playlist_accessor = playlist_accessor
        self._switch_playlist = switch_playlist
        self._play_list = play_list
        self._switch_video = switch_video

    def render_request(self):
        request_command = request.params.get('command')
        if request_command == 'status':
            return self.get_dlna_status()
        elif request_command == 'pause':
            self.ac.device.pause()
            return ''
        elif request_command == 'play':
            self.ac.device.play()
            return ''
        elif request_command == 'stop':
            self.ac.stop()
            return ''
        elif request_command == 'index':
            return self.index()
        elif request_command == 'seek':
            pos = int(request.params.get('pos'))
            self.ac.device.seek(format_time(pos + self.ac.current_video_position))
            return ''
        elif request_command == 'getAllPlaylist':
            return self.get_all_playlist()
        elif request_command == 'switchPlayList':
            return self.switch_playlist()
        elif request_command == 'playAtApp':
            return self.playAtApp()
        elif request_command == 'backToDlna':
            pos = int(request.params.get('pos'))
            self.back_to_dlna(pos)
            return ''

        abort(404, "错误的命令")

    def back_to_dlna(self, seek_to: int):
        self.ac.resume(stop=False, seek_to=seek_to)

    def index(self):
        index = int(request.params.get('index'))
        video_name = request.params.get('name').encode('iso8859-1').decode('utf-8')
        is_same_file_name = Path(self.ac.local_file_path).name == video_name and self._play_list.is_sync()

        if not self._play_list.is_sync():
            self._switch_video([self._play_list.playlist.media_list[self.ac.current_idx], ''], [self._play_list.playlist_view[index], ''])
        else:
            if index == -1:
                self.ac.stop()
            elif index == self.ac.current_idx and is_same_file_name:
                self.ac.resume()
            else:
                self.ac.current_idx = index
                self.ac.play()

        ret_obj = {}
        ret_obj.update(self._create_view_playlist_data())
        ret_obj.update(self._create_dlna_player_data())
        return json.dumps(ret_obj, indent=2).encode('utf-8')

    def switch_playlist(self):
        old_playlist = str(request.params.get('o').encode('iso8859-1').decode('utf-8'))
        new_playlist = str(request.params.get('n').encode('iso8859-1').decode('utf-8'))
        playlist_list = self._playlist_accessor()
        old_path = ''
        old_name = old_playlist
        new_path = ''
        new_name = new_playlist
        for playlist in playlist_list:
            playlist_path = playlist[0]
            playlist_name = playlist[1]
            if playlist_name == new_name:
                new_path = playlist_path
            if playlist_name == old_name:
                old_path = playlist_path

        self._switch_playlist([old_path, old_name], [new_path, new_name])
        ret_obj = self._create_view_playlist_data()
        return json.dumps(ret_obj, indent=2).encode('utf-8')

    def get_all_playlist(self):
        playlist_list = [p[1] for p in self._playlist_accessor()]
        return json.dumps(playlist_list, indent=2).encode('utf-8')

    def get_dlna_status(self):
        ret_obj = self._create_all_data()
        return json.dumps(ret_obj, indent=2).encode('utf-8')

    def playAtApp(self):
        return self.current_video_file()

    def current_video_file(self):
        file_path = Path(self.ac.local_file_path)
        return static_file(file_path.name, root=str(file_path.parent))

    def _create_current_playlist_data(self):
        return {
                    'currentPlaylist': {
                        'name': self._play_list.playlist.get_playlist_name(),
                        'index': self.ac.current_idx,
                    }
                }

    def _create_current_video_data(self):
        video_file_path = Path(self.ac.local_file_path)
        return {
                    'currentVideo': {
                        'path': str(video_file_path.absolute()),
                        'name': video_file_path.name,
                        'position': self.ac.current_video_position,
                        'duration': self.ac.current_video_duration,
                    }
                }

    def _create_dlna_player_data(self):
        return {
                    'dlnaPlayer': {
                        'occupied': self.ac.is_occupied,
                        'status': self.ac.player.player_status.value,
                    }
                }

    def _create_view_playlist_data(self):
        view_playlist = self._play_list.playlist_view.playlist
        current_index = view_playlist.current_index
        if self._play_list.is_sync():
            # 当视图显示的播放列表和播放使用的播放列表同步时，使用播放使用的播放列表的播放位置
            current_index = self.ac.current_idx
        return {
                    'viewPlaylist': {
                        'name': view_playlist.get_playlist_name(),
                        'index': current_index,
                        'position': view_playlist.current_pos,
                        'duration': view_playlist.current_duration,
                        'videoList': [Path(f).name for f in self.ac.play_list.playlist_view]
                    }
                }

    def _create_all_data(self):
        result = {}
        func_array = [self._create_current_playlist_data,
                      self._create_current_video_data,
                      self._create_dlna_player_data,
                      self._create_view_playlist_data]
        for func in func_array:
            result.update(func())
        return result
