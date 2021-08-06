import json
import os
import time
from pathlib import Path
from typing import Callable, List, Tuple

from bottle import request, static_file, abort, HTTPResponse
from pysimpledlna.entity import Playlist

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
                 playlist_accessor: Callable[[], List[Tuple[str, str]]],
                 switch_playlist: Callable[[List[str], List[str]], Playlist],
                 current_playlist: Callable[[], Playlist]) -> None:
        super().__init__(f'/api/{ac.device.device_key}', method=['GET', 'POST'])
        self.ac = ac
        self.render = self.render_request
        self._playlist_accessor = playlist_accessor
        self._switch_playlist = switch_playlist
        self._current_playlist = current_playlist

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

        abort(404, "错误的命令")

    def index(self):
        index = int(request.params.get('index'))
        video_name = request.params.get('name').encode('iso8859-1').decode('utf-8')
        is_same_file_name = Path(self.ac.local_file_path).name == video_name
        current_status = ''
        if index == -1:
            self.ac.stop()
            current_status = 'Stop'
        elif index == self.ac.current_idx and is_same_file_name:
            self.ac.resume()
            current_status = self.ac.player.player_status.value
        else:
            self.ac.current_idx = index
            self.ac.play()
            current_status = self.ac.player.player_status.value
        ret_obj = {
            'index': self.ac.current_idx,
            'current_status': current_status
        }
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

        playlist = self._switch_playlist([old_path, old_name], [new_path, new_name])
        file_name_list = [os.path.split(f)[1] for f in playlist.file_list]
        video_idx = playlist.current_index
        return json.dumps({
            "index": video_idx,
            "file_name_list": file_name_list
        }, indent=2).encode('utf-8')

    def get_all_playlist(self):
        playlist_list = [p[1] for p in self._playlist_accessor()]
        return json.dumps(playlist_list, indent=2).encode('utf-8')

    def get_dlna_status(self):
        video_pos = self.ac.current_video_position
        video_dur = self.ac.current_video_duration
        video_idx = self.ac.current_idx
        #video_file_path = Path(self.ac.file_list[video_idx])
        #video_file_name = video_file_path.name
        video_file_path = Path(self.ac.local_file_path)
        video_file_name = video_file_path.name
        current_status = self.ac.player.player_status.value
        file_name_list = [Path(f).name for f in self.ac.file_list]

        current_playlist = self._current_playlist()
        current_playlist_path = current_playlist.file_path

        ret_obj = {
            'position': video_pos,
            'duration': video_dur,
            'playing_file_name': video_file_name,
            'playing_file_path': str(video_file_path.absolute()),
            'current_status': current_status,
            'index_in_playlist': video_idx,
            'file_name_list': file_name_list,
            'current_playlist_name': Path(current_playlist_path).stem,
            'is_occupied': self.ac.is_occupied
        }

        return json.dumps(ret_obj, indent=2).encode('utf-8')

    def playAtApp(self):
        return self.current_video_file()

    def current_video_file(self):
        file_path = Path(self.ac.local_file_path)
        return static_file(file_path.name, root=str(file_path.parent))
