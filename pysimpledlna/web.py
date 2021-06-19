import json
from pathlib import Path

from bottle import request, static_file, abort

from pysimpledlna.ac import ActionController
from pysimpledlna.dlna import DefaultResource


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
            app_js_file = self.web_root / Path(filepath)
            app_js = app_js_file.read_text('utf-8')
            return app_js.replace('{device_key}', self.ac.device.device_key)

        return static_file(filepath, root=str(self.web_root.absolute()))


class DLNAService(DefaultResource):

    def __init__(self, ac: ActionController) -> None:
        super().__init__(f'/api/{ac.device.device_key}', method=['GET', 'POST'])
        self.ac = ac
        self.render = self.render_request

    def render_request(self):
        request_command = request.params.get('command')
        if request_command == 'status':
            return self.get_dlna_status().encode('utf-8')
        elif request_command == 'pause':
            self.ac.device.pause()
        elif request_command == 'play':
            self.ac.device.play()
        elif request_command == 'index':
            index = int(request.params.get('index'))
            self.ac.current_idx = index
            self.ac.play()
        abort(404, "错误的命令")

    def get_dlna_status(self):
        video_pos = self.ac.current_video_position
        video_dur = self.ac.current_video_duration
        video_idx = self.ac.current_idx
        video_file_path = Path(self.ac.file_list[video_idx])
        video_file_name = video_file_path.name
        current_status = self.ac.player.player_status.value
        file_name_list = [Path(f).name for f in self.ac.file_list]

        ret_obj = {
            'position': video_pos,
            'duration': video_dur,
            'index': video_idx,
            'current_status': current_status,
            'file_name': video_file_name,
            'file_name_list': file_name_list
        }

        return json.dumps(ret_obj, indent=2)

'''
class DLNAService(Resource):

    def __init__(self, ac: ActionController):
        super().__init__()
        self.ac = ac

    def render_GET(self, request):
        request_command = self.get_arg_value(request, b'command')
        if request_command == 'status':
            return self.get_dlna_status().encode('utf-8')
        elif request_command == 'pause':
            self.ac.device.pause()
        elif request_command == 'play':
            self.ac.play()
        elif request_command == 'index':
            index = int(self.get_arg_value(request, b'index'))
            self.ac.current_idx = index
            self.ac.play()
        return b''

    def get_arg_value(self, request, name: bytes):
        args = request.args[name][0].decode("utf-8")
        escapedArgs = html.escape(args)
        return escapedArgs

    def get_dlna_status(self):
        video_pos = self.ac.current_video_position
        video_dur = self.ac.current_video_duration
        video_idx = self.ac.current_idx
        video_file_path = Path(self.ac.file_list[video_idx])
        video_file_name = video_file_path.name
        current_status = self.ac.player.player_status.value
        file_name_list = [Path(f).name for f in self.ac.file_list]

        ret_obj = {
            'position': video_pos,
            'duration': video_dur,
            'index': video_idx,
            'current_status': current_status,
            'file_name': video_file_name,
            'file_name_list': file_name_list
        }

        return json.dumps(ret_obj, indent=2)
'''