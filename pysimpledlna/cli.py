import argparse
import json
import sys
import time
import signal
import logging
import logging.config
import traceback
from typing import List, Tuple
from pathlib import Path

from pysimpledlna.ui.playlist import PlayListEditor


import os
from pysimpledlna import SimpleDLNAServer, Device
from pysimpledlna.ac import ActionController
from pysimpledlna.utils import (
    get_playlist_dir, get_user_data_dir, get_free_tcp_port, get_setting_file_path, is_tcp_port_occupied, get_abs_path,
    get_history_file_path, is_in_prompt_mode, is_in_nuitka, start_subprocess, get_log_file_path, get_log_file_dir)
from pysimpledlna.entity import LocalFilePlaylist, Settings, LocalTempFilePlaylist, PlayListWrapper, Playlist, \
    DeviceList

_DLNA_SERVER_PORT = get_free_tcp_port()
settings = Settings(get_setting_file_path())
_DLNA_SERVER = SimpleDLNAServer(
    server_port=_DLNA_SERVER_PORT,
    is_enable_ssl=settings.get_enable_ssl(),
    cert_file=settings.get_cert_file(),
    key_file=settings.get_key_file()
)

NO_SERVER_ACTION = []


def main():
    init_logger()
    logger = get_logger()

    for action in [config,
                   list_device,
                   playlist_create,
                   playlist_delete,
                   playlist_list,
                   playlist_refresh,
                   playlist_update,
                   playlist_view,
                   playlist_rename,]:
        NO_SERVER_ACTION.append(action)

    parser = argparse.ArgumentParser()
    wrap_parser_exit(parser)

    create_args(parser)

    args = parser.parse_args()
    logger.info(args)

    if not hasattr(args, 'func'):
        from prompt_toolkit_ext import PromptArgumentParser, run_prompt, LimitSizeFileHistory
        from prompt_toolkit_ext.completer import ArgParserCompleter
        from prompt_toolkit_ext.lexer import ArgParseLexer
        prompt_argparser = PromptArgumentParser()
        subparsers = create_args(prompt_argparser)
        create_quit_parser(subparsers)
        history = LimitSizeFileHistory(get_history_file_path(), 100)
        from prompt_toolkit.lexers import PygmentsLexer
        try:
            print('=' * 80)
            print('pysimpledlna v0.5.4', '投屏工具')
            print('用户数据目录：', get_user_data_dir())
            print('日志文件：', get_log_file_path())
            print('=' * 80)
            run_prompt(prompt_parser=prompt_argparser,
                       prompt_history=history,
                       prompt_completer=ArgParserCompleter(prompt_argparser),
                       prompt_lexer=PygmentsLexer(ArgParseLexer))
        except KeyboardInterrupt:
            quit_prog()
        except Exception as e:
            logger.info(traceback.format_exc())
            print(e)
        return

    need_server_started = args.func not in NO_SERVER_ACTION
    try:
        if need_server_started:
            default_port = settings.get_default_port()
            try_cnt = 0
            while is_tcp_port_occupied(_DLNA_SERVER.server_ip, default_port):
                default_port += 1
                if default_port > 18020:
                    default_port = default_port % 20 + 18000
                try_cnt += 1
                if try_cnt >= 20:
                    print('没有可用的端口：', default_port)
                    sys.exit()
            settings.set_default_port(default_port)
            settings.write()
            _DLNA_SERVER.server_port = default_port
            _DLNA_SERVER.start_server()
        args.func(args)
    finally:
        if need_server_started:
            _DLNA_SERVER.stop_server()


def create_quit_parser(subparsers):
    parser = subparsers.add_parser('quit', help='退出程序')
    parser.set_defaults(func=quit_prog)


def create_args(parser):
    subparsers = parser.add_subparsers(help='DLAN Server')
    _, list_parser = create_default_device_parser(subparsers)
    wrap_parser_exit(list_parser)
    _, list_parser = create_list_parser(subparsers)
    wrap_parser_exit(list_parser)
    _, play_parser = create_play_parser(subparsers)
    wrap_parser_exit(play_parser)
    _, playlist_parser = create_playlist_parser(subparsers)
    playlist_subparsers = playlist_parser.add_subparsers(help='playlist')
    wrap_parser_exit(playlist_parser)
    _, playlist_create_parser = create_playlist_create_parser(playlist_subparsers)
    wrap_parser_exit(playlist_create_parser)
    _, playlist_delete_parser = create_playlist_delete_parser(playlist_subparsers)
    wrap_parser_exit(playlist_delete_parser)
    _, playlist_play_parser = create_playlist_play_parser(playlist_subparsers)
    wrap_parser_exit(playlist_play_parser)
    _, playlist_list_parser = create_playlist_list_parser(playlist_subparsers)
    wrap_parser_exit(playlist_list_parser)
    _, playlist_refresh_parser = create_playlist_refresh_parser(playlist_subparsers)
    wrap_parser_exit(playlist_refresh_parser)
    _, playlist_update_parser = create_playlist_update_parser(playlist_subparsers)
    wrap_parser_exit(playlist_update_parser)
    _, playlist_view_parser = create_playlist_view_parser(playlist_subparsers)
    wrap_parser_exit(playlist_view_parser)
    _, playlist_rename_parser = create_playlist_rename_parser(playlist_subparsers)
    wrap_parser_exit(playlist_rename_parser)
    return subparsers


def wrap_parser_exit(parser: argparse.ArgumentParser):
    exit_func = parser.exit
    func = parser.get_default('func')

    def exit(status=0, message=None):
        if func not in NO_SERVER_ACTION:
            _DLNA_SERVER.stop_server()
        exit_func(status, message)

    parser.exit = exit


def create_default_device_parser(subparsers):
    command = 'config'
    parser = subparsers.add_parser(command, help='设置参数')
    parser.add_argument('-u', '--url', dest='url', required=False, type=str, default=None, help='默认DLNA设备地址，多个地址用[;]分隔')
    parser.add_argument('-es', '--enable-ssl', dest='enable_ssl', required=False, type=str, default=None, choices=['True', 'true', 'False', 'false', ], help='是否启用SSL')
    parser.add_argument('-p', '--print', dest='print_opts', required=False, default=False, action='store_true', help='是否输出配置信息')
    parser.add_argument('-cert', '--cert-file', dest='cert_file', required=False, default=None, help='用于https的公钥')
    parser.add_argument('-key', '--key-file', dest='key_file', required=False, default=None, help='用于https的私钥')
    parser.set_defaults(func=config)
    return command, parser


def create_list_parser(subparsers):
    command = 'list'
    parser = subparsers.add_parser(command, help='查找DLNA设备')
    parser.add_argument('-t', '--timeout', dest='timeout', required=False, default=20, type=int, help='超时时间')
    parser.add_argument('-m', '--max', dest='max', required=False, default=99999, type=int, help='查找DLNA设备的最大数量')
    parser.add_argument('-dn', '--disable-notify', dest='disable_notify', required=False, default=False, action='store_true', help='不接收notify')
    parser.set_defaults(func=list_device)
    return command, parser


def create_play_parser(subparsers):
    command = 'play'
    parser = subparsers.add_parser(command, help='播放视频')
    parser.add_argument('-i', '--input', dest='input', required=True, type=str, nargs='+',  help='视频文件')
    group = parser.add_mutually_exclusive_group()

    group.add_argument('-u', '--url', dest='url', type=str, help='DLNA设备地址')
    group.add_argument('-a', '--auto-select', dest='auto_selected', action='store_true', default=False, help='自动选择第一台设备作为播放设备')
    parser.set_defaults(func=play)
    return command, parser


def create_playlist_parser(subparsers):
    command = 'playlist'
    return command, subparsers.add_parser(command, help='播放播放列表')


def create_playlist_create_parser(subparsers):
    command = 'create'
    parser = subparsers.add_parser(command, help='创建播放列表')
    parser.add_argument('-n', '--name', dest='name', required=True, type=str, help='播放列表名字')
    parser.add_argument('-i', '--input', dest='input', required=True, type=str, nargs='+', help='包含目标文件的目录')
    parser.add_argument('-f', '--filter', dest='filter', required=False, type=str, help='文件过滤器')
    parser.add_argument('-sh', '--skip-head', dest='skip_head', required=False, type=int, default=0, help='跳过片头时间')
    parser.add_argument('-st', '--skip-tail', dest='skip_tail', required=False, type=int, default=0, help='跳过片尾时间')
    parser.set_defaults(func=playlist_create)

    return command, parser


def create_playlist_delete_parser(subparsers):
    command = 'delete'
    parser = subparsers.add_parser(command, help='删除播放列表')
    parser.add_argument('-n', '--name', dest='name', required=True, type=str, help='播放列表名字')
    parser.set_defaults(func=playlist_delete)

    return command, parser


def create_playlist_play_parser(subparsers):
    command = 'play'
    parser = subparsers.add_parser(command, help='播放播放列表中的文件')
    parser.add_argument('-n', '--name', dest='name', required=False, type=str, help='播放列表名字')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-u', '--url', dest='url', type=str, help='DLNA设备地址')
    group.add_argument('-a', '--auto-select', dest='auto_selected', action='store_true', default=False,
                       help='自动选择第一台设备作为播放设备')
    parser.set_defaults(func=playlist_play)

    return command, parser


def create_playlist_list_parser(subparsers):
    command = 'list'
    parser = subparsers.add_parser(command, help='列出所有播放列表')
    parser.set_defaults(func=playlist_list)

    return command, parser


def create_playlist_refresh_parser(subparsers):
    command = 'refresh'
    parser = subparsers.add_parser(command, help='刷新播放列表')
    parser.add_argument('-n', '--name', dest='name', required=True, type=str, help='播放列表名字')
    parser.set_defaults(func=playlist_refresh)
    return command, parser


def create_playlist_update_parser(subparsers):
    command = 'update'
    parser = subparsers.add_parser(command, help='更新播放列表')
    parser.add_argument('-n', '--name', dest='name', required=True, type=str, help='播放列表名字')
    parser.add_argument('-vi', '--video-index', dest='video_index', required=False, type=int, default=-1, help='当前视频序号，从0开始')
    parser.add_argument('-vp', '--video-position', dest='video_pos', required=False, type=int, default=-1, help='当前视频播放位置，单位：秒')
    parser.add_argument('-sh', '--skip-head', dest='skip_head', required=False, type=int, default=-1, help='跳过片头时间')
    parser.add_argument('-st', '--skip-tail', dest='skip_tail', required=False, type=int, default=-1, help='跳过片尾时间')
    parser.set_defaults(func=playlist_update)
    return command, parser


def create_playlist_view_parser(subparsers):
    command = 'view'
    parser = subparsers.add_parser(command, help='查看播放列表')
    parser.add_argument('-n', '--name', dest='name', required=True, type=str, help='播放列表名字')
    parser.set_defaults(func=playlist_view)
    return command, parser


def create_playlist_rename_parser(subparsers):
    command = 'rename'
    parser = subparsers.add_parser(command, help='重命名播放列表')
    parser.add_argument('-on', '--old-name', dest='old_name', required=True, type=str, help='旧播放列表名字')
    parser.add_argument('-nn', '--new-name', dest='new_name', required=True, type=str, help='新播放列表名字')
    parser.set_defaults(func=playlist_rename)
    return command, parser


def config(args):
    setting_file_path = get_setting_file_path()
    settings = Settings(setting_file_path)

    if args.url is not None:
        settings.set_default_devices(args.url)

    if args.enable_ssl is not None:
        enable_ssl = (args.enable_ssl == 'True' or args.enable_ssl == 'true')
        settings.set_enable_ssl(enable_ssl)

    if args.cert_file is not None:
        settings.set_cert_file(args.cert_file)

    if args.key_file is not None:
        settings.set_key_file(args.key_file)

    settings.write()
    print(f'配置文件: {setting_file_path}')

    if args.print_opts:
        print(json.dumps(settings.d, indent=2))


def list_device(args):
    dlna_server = _DLNA_SERVER
    device_found = False
    max_number = args.max
    disable_notify = args.disable_notify
    for i, device in enumerate(dlna_server.get_devices(args.timeout, disable_notify=disable_notify)):
        print('[', i+1, ']', device.friendly_name, '@', device.location)
        device_found = True
        if (i+1) >= max_number:
            break
    if not device_found:
        print('没有找到设备')


def play(args):

    user_dir = get_user_data_dir()
    playlist_dir = get_playlist_dir(user_dir, 'playlist')
    playlist_path = get_playlist_file_path_by_name(playlist_dir, '临时列表')
    if os.path.exists(playlist_path):
        os.remove(playlist_path)

    temp_playlist = LocalTempFilePlaylist(playlist_path)
    temp_playlist.media_list = args.input
    temp_playlist.save_playlist(force=True)

    setattr(args, 'name', '临时列表')
    delattr(args, 'input')

    playlist_play(args)


def playlist_create(args):
    play_list_file = get_playlist_file_path(args)
    input_dirs: [] = args.input
    filename_filter: str = args.filter
    pl = LocalFilePlaylist(play_list_file, _filter=filename_filter, input=input_dirs)
    pl.skip_head = args.skip_head
    pl.skip_tail = args.skip_tail
    pl.filter_files()
    pl.save_playlist()

    print('播放列表已保存:' + play_list_file)


def playlist_delete(args):
    play_list_file = get_playlist_file_path(args)
    if not os.path.exists(play_list_file):
        print('播放列表[' + args.name + ']['+ play_list_file + ']不存在')
        return
    if os.path.isfile(play_list_file):
        os.remove(play_list_file)
        print('播放列表[' + args.name + ']['+ play_list_file + ']已删除')
        return
    print('播放列表不是文件，无法删除[' + args.name + ']['+ play_list_file + ']')


def playlist_list(args):
    user_dir = get_user_data_dir()
    play_list_dir = get_playlist_dir(user_dir, 'playlist')
    play_list = [os.path.splitext(f)[0] for f in os.listdir(play_list_dir) if os.path.isfile(os.path.join(play_list_dir, f)) and f.endswith('.playlist')]

    print('播放列表目录：', play_list_dir)

    if len(play_list) == 0:
        print('没有播放列表')

    for i, pl in enumerate(play_list):
        print('[' + str(i) + ']', pl)


def playlist_play(args):

    logger = get_logger()

    if is_in_prompt_mode(args):
        try:
            cmd = list()
            cwd = '.'
            if not is_in_nuitka():
                cmd = ['python', os.path.join(os.path.split(os.path.abspath(__file__))[0], 'cli.py')]
                cwd = str(Path(os.path.join(os.path.split(os.path.abspath(__file__))[0])).parent)
            else:
                cmd = [str(get_abs_path('pysimpledlna.exe')), ]
                cwd = str(get_abs_path())

            for arg in args.prompt_args:
                cmd.append(arg)
            print('启动目录：', cwd)
            print('启动命令：', ' '.join(cmd))
            process = start_subprocess(cmd, cwd)
            print('新进程ID：' + str(process.pid))
        except:
            traceback.print_exc()
        return

    from pysimpledlna.ui.playlist import (
        PlayListPlayer, PlayerModel,
        VideoPositionFormatter, VideoControlFormatter, VideoFileFormatter)
    from pysimpledlna.utils import format_time
    from prompt_toolkit_ext.widgets import RadioList
    from prompt_toolkit.shortcuts.progress_bar.formatters import Text
    from pysimpledlna.ui.terminal import PlayerStatus
    from prompt_toolkit.patch_stdout import patch_stdout
    from prompt_toolkit import HTML
    from prompt_toolkit_ext.event import KeyEvent

    dlna_server = _DLNA_SERVER
    user_dir = get_user_data_dir()
    play_list_dir = get_playlist_dir(user_dir, 'playlist')

    device: Device = None
    if args.auto_selected:
        for i, d in enumerate(dlna_server.get_devices(5)):
            device = d
            break
    else:
        url = args.url
        if url is None:
            if url is None:
                settings = Settings(get_setting_file_path())
                default_device_urls: List[str] = settings.get_default_devices()
                for default_device_url in default_device_urls:
                    device = dlna_server.find_device(default_device_url)
                    if device is not None:
                        default_device_urls.remove(default_device_url)
                        default_device_urls.insert(0, default_device_url)
                        settings.write()
                        break

        else:
            device = dlna_server.parse_xml(url)
    if device is None:
        print('No Device available')
        return

    device = dlna_server.register_device(device)

    play_list = PlayListWrapper()
    play_list.start_play = True

    # 初始化播放列表
    if not hasattr(args, 'name') or args.name is None:
        play_list.start_play = False
        all_playlist_path = os.listdir(play_list_dir)
        if len(all_playlist_path) == 0:
            logger.info('没有播放列表')
            return
        setattr(args, 'name', Path(all_playlist_path[0]).stem)

    play_list_file = get_playlist_file_path(args)
    if not os.path.exists(play_list_file):
        logger.info('播放列表[' + args.name + '][' + play_list_file + ']不存在')
        return

    play_list.playlist = Playlist.get_playlist(play_list_file)
    play_list.playlist.load_playlist()
    play_list.set_vo(play_list.playlist)

    device_list: DeviceList = DeviceList([device], 0)

    player = PlayListPlayer(play_list, [('', '')], device_list)

    player_model: PlayerModel = player.create_model()
    ac = ActionController(play_list, device, player_model)

    # 设置内部播放列表
    def _setup_inner_playlist(new_play_list: Playlist):
        play_list.playlist = new_play_list
        ac.current_idx = play_list.playlist.current_index
        play_list.playlist_init_index = play_list.playlist.current_index
        play_list.playlist_init_position = play_list.playlist.current_pos

    # 设置视图播放列表
    def _setup_view_playlist(new_play_list: Playlist):
        play_list.set_vo(new_play_list)
        player.update_playlist_part()

    # 设置播放列表
    def _setup_playlist(new_play_list: Playlist):
        _setup_inner_playlist(new_play_list)
        _setup_view_playlist(new_play_list)

    _setup_playlist(play_list.playlist)

    # 获得所有播放列表的路径和名字
    def _get_playlist_list() -> List[Tuple[str, str]]:
        playlist_list_dir = get_playlist_dir(user_dir, 'playlist')
        playlist_list = [(os.path.join(playlist_list_dir, f), os.path.splitext(f)[0]) for f in
                         os.listdir(playlist_list_dir) if
                         os.path.isfile(os.path.join(playlist_list_dir, f)) and f.endswith('.playlist')]
        return playlist_list

    def _setup_playlist_list(selected_name):
        playlist_list = _get_playlist_list()
        player.playlistlist_part.values = playlist_list
        for index, playlist in enumerate(playlist_list):
            playlist_name = playlist[1]
            if playlist_name == selected_name:
                player.playlistlist_part.set_checked_index(index)
                break

    _setup_playlist_list(args.name)

    def _get_playlist_filename_by_name(playlist_name):
        _play_list_file = get_playlist_file_path_by_name(play_list_dir, playlist_name)
        _play_list = LocalFilePlaylist(_play_list_file)
        _play_list.load_playlist()
        return _play_list

    # 切换播放列表
    def _playlist_selected(old_value, new_value):
        old_file_path = old_value[0]
        old_file_name = old_value[1]

        new_file_path = new_value[0]
        new_file_name = new_value[1]

        def samefile(old_file_path, new_file_path):
            o_exists = os.path.exists(old_file_path)
            n_exists = os.path.exists(new_file_path)
            if not o_exists and n_exists:
                return False
            if not o_exists and not n_exists:
                return True
            if o_exists and not n_exists:
                return False
            return os.path.samefile(old_file_path, new_file_path)

        if samefile(old_file_path, new_file_path):
            return

        new_playlist = Playlist.get_playlist(new_file_path)
        _setup_playlist_list(new_playlist.get_playlist_name())
        _setup_view_playlist(new_playlist)
        return

    # 切换视频
    def _video_selected(old_value, new_value):

        if not play_list.start_play:
            play_list.start_play = True
            old_file_path = get_user_data_dir()
            old_file_name = Path(old_file_path).name
        else:
            old_file_path = old_value[0]
            old_file_name = old_value[1]

        new_file_path = new_value[0]
        new_file_name = new_value[1]

        # 视图显示的播放列表与内部播放列表不一致时
        # 先将内部播放列表设置为视图播放列表
        # 然后递归调用进行播放
        if not play_list.is_sync():
            current_file_path = play_list.playlist.media_list[play_list.playlist.current_index]
            play_list.playlist.save_playlist(force=True)
            new_playlist = Playlist.get_playlist(play_list.get_view_playlist_path())
            _setup_inner_playlist(new_playlist)
            return _video_selected([current_file_path, Path(current_file_path).name], new_value)

        if os.path.samefile(old_file_path, new_file_path) \
                and ac.player.player_status in [PlayerStatus.PLAY, PlayerStatus.PAUSE] \
                and os.path.samefile(new_file_path, ac.local_file_path):
            if ac.player.player_status == PlayerStatus.PAUSE:
                ac.play()
            return True

        if not os.path.samefile(old_file_path, new_file_path) \
                or not os.path.samefile(new_file_path, ac.local_file_path):
            selected_index = player.playlist_part.get_selected_index()

            ac.current_idx = selected_index
            ac.play()
        else:
            play_list.playlist.load_playlist()
            _setup_playlist(play_list.playlist)
            ac.play()

    # 初始化web ui
    from pysimpledlna.web import WebRoot, DLNAService

    web_root = WebRoot(ac, get_abs_path(Path('./webroot')), 0)
    dlna_service = DLNAService(ac,
                               play_list=play_list,
                               playlist_accessor=_get_playlist_list,
                               switch_playlist=_playlist_selected,
                               switch_video=_video_selected)
    dlna_server.app.route(**web_root.get_route_params())
    dlna_server.app.route(**dlna_service.get_route_params())
    player.webcontrol_url = web_root.get_player_page_url()
    player.create_key_bindings()
    player.create_ui()

    # 事件处理
    # 刷新dlna设备列表
    def _refresh_device_list(event: KeyEvent):

        import threading
        from threading import Timer

        def do_refresh():

            if player.is_refresh_dlna_render:
                return

            player.is_refresh_dlna_render = True
            loading_char = ['▏', '▎', '▍', '▌', '▋', '▊', '▉']

            def update_title(index):
                player.dlna_render_part.title = 'DLNA显示器 ' + loading_char[index % 7]
                if player.is_refresh_dlna_render:
                    t = Timer(0.5, update_title, args=[(index+1) % 7])
                    t.start()
                else:
                    player.dlna_render_part.title = 'DLNA显示器'

            update_title(0)

            def find_device_by_location(devices: List[Device], location: str):
                for device in devices:
                    if device.location == location:
                        return device
                return None

            try:
                old_device_list = device_list.device_list
                result: List[Device] = list()
                for device in dlna_server.get_devices(60):
                    known_device = dlna_server.register_device(device)
                    result.append(known_device)

                # 根据已知的设备地址查询遗漏的设备
                for known_device in dlna_server.known_devices.values():
                    d = find_device_by_location(result, known_device.location)
                    if d is None:
                        new_device = dlna_server.find_device(known_device.location)
                        if new_device is not None:
                            result.append(known_device)

                device_list.device_list = result

                # 设置当前使用的设备
                selected_device = old_device_list[device_list.selected_index]
                result = device_list.set_selected_index(selected_device)
                if result == -1:
                    device_list.selected_index = 0

                player.update_dlna_render_part()
            finally:
                player.is_refresh_dlna_render = False
                player.dlna_render_part.title = 'DLNA显示器'

        threading.Thread(target=do_refresh, daemon=True).start()

    # 切换dlna设备
    def _dlna_device_selected(old_value, new_value):
        old_device_key = old_value[0]
        new_device_key = new_value[0]
        if old_device_key == new_device_key:
            return
        old_device = device_list.get_device_by_device_key(old_device_key)
        new_device = device_list.get_device_by_device_key(new_device_key)

        start_play = True
        if old_device.sync_thread is None or old_device.sync_thread.last_status is None \
                or old_device.sync_thread.last_status.get('transport_info') is None:
            start_play = False
        else:
            current_transport_state = old_device.sync_thread.last_status['transport_info']['CurrentTransportState']
            if current_transport_state != 'PLAYING':
                start_play = False

        device_list.set_selected_index(new_device)
        positionhook, transportstatehook, exceptionhook = old_device.positionhook, old_device.transportstatehook, old_device.exceptionhook
        old_device.set_sync_hook(None, None, None)
        old_device.stop()
        old_device.stop_sync_remote_player_status()

        play_list.playlist.save_playlist(force=True)

        ac.init_ac(new_device)
        _setup_inner_playlist(play_list.playlist)
        if start_play:
            ac.play()

        new_device.set_sync_hook(positionhook, transportstatehook, exceptionhook)
        new_device.start_sync_remote_player_status()

    # 更新播放列表选中项位置，如果视图被切换则不进行更新视频列表内容
    def _update_list_ui(current_index):
        if play_list.is_sync():
            player.playlist_part.current_value = player.playlist_part.values[current_index][0]

    # 视频进度向前
    def _forward(event, times):
        target_position = ac.current_video_position + 10 * times
        if ac.current_video_duration == 0:
            time_str = format_time(target_position)
            ac.device.seek(time_str)
            return
        if target_position >= ac.get_max_video_position():
            target_position = ac.get_max_video_position() - 10
        time_str = format_time(target_position)
        ac.device.seek(time_str)

    # 视频进度向后
    def _backward(event, times):
        target_position = ac.current_video_position - 10 * times
        if target_position <= 0:
            target_position = 1
        time_str = format_time(target_position)
        ac.device.seek(time_str)

    # 播放下一个视频
    def _next(event, times):
        ac.current_idx += times
        if ac.current_idx >= len(play_list.playlist.media_list):
            ac.current_idx = len(play_list.playlist.media_list) - 1
        ac.play()

    # 播放上一个视频
    def _last(event, times):
        ac.current_idx -= times
        if ac.current_idx < 0:
            ac.current_idx = 0
        ac.play()

    # 设置播放列表中当前视频的索引
    def _update_playlist_index(current_index):
        play_list.playlist.current_index = current_index
        play_list.playlist.save_playlist(force=True)

    # 更新播放列表当前文件长度
    def _update_current_video_duration(o_position, n_position):
        if play_list.playlist.current_duration != ac.current_video_duration and ac.current_video_duration != 0:
            play_list.playlist.current_duration = ac.current_video_duration
            play_list.playlist.save_playlist(force=True)

    # 设置播放列表中当前视频的播放位置
    def _update_playlist_video_position(o_position, n_position):
        play_list.playlist.current_pos = n_position
        play_list.playlist.save_playlist()

    # 使用新的索引和播放位置强制保存播放列表
    def _save_playlist(current_index, current_position):
        play_list.playlist.current_index = current_index
        play_list.playlist.current_pos = current_position
        play_list.playlist.save_playlist(force=True)

    # 根据播放列表配置跳过片头
    def _skip_head(current_index):
        
        logger.debug('==start==')
        logger.debug(f'cur index: {current_index}')
        logger.debug(f"position_in_playlist: {play_list.playlist_init_position}")
        logger.debug(f'current_video_position: {ac.current_video_position}')
        logger.debug(f'seek to {format_time(play_list.playlist.skip_head)}')
        logger.debug('== end ==')

        if play_list.playlist_init_position > 0 and play_list.playlist_init_index == ac.current_idx:
            if play_list.playlist_init_position > ac.current_video_position:
                resume_position = play_list.playlist_init_position - 5
                if resume_position < 0:
                    resume_position = 0
                time_str = format_time(resume_position)
                ac.device.seek(time_str)
                play_list.playlist.current_pos = play_list.playlist_init_position
                play_list.playlist.save_playlist(force=True)
                play_list.playlist_init_position = -1
        elif play_list.playlist.skip_head > 0:
            time.sleep(0.5)
            time_str = format_time(play_list.playlist.skip_head)
            ac.device.seek(time_str)
            play_list.playlist.current_pos = play_list.playlist.skip_head
            play_list.playlist.save_playlist(force=True)

    # 根据播放列表配置跳过片尾
    def _skip_tail(o_position, n_position):
        if play_list.playlist.skip_tail == 0:
            return
        end = ac.get_max_video_position() - play_list.playlist.skip_tail
        if n_position >= end and end > 0:
            ac.play_next()

    # 退出
    def _quit():
        if ac.is_occupied:
            ac.device.stop_sync_remote_player_status()
            # 其他程序占用投屏时，退出时不发送结束投屏命令
            #ac.device.stop()
            ac.end = True
        else:
            ac.stop_device()

    # 加入事件监听
    player.playlist_part.check_event += _video_selected
    player.playlistlist_part.check_event += _playlist_selected
    player.dlna_render_radio.check_event += _dlna_device_selected

    # TODO 事件没有被调用，待查
    player.player_events['quit'] += _quit

    player.player_events['refresh_dlna_render'] += _refresh_device_list
    player.controller_events['pause'] += \
        lambda e: ac.resume() if player_model.player_status == PlayerStatus.PAUSE else ac.pause()
    player.controller_events['last'] += _last
    player.controller_events['next'] += _next
    player.controller_events['forward'] += _forward
    player.controller_events['backward'] += _backward
    ac.events['play'] += _skip_head
    ac.events['video_position'] += _skip_tail
    ac.events['play'] += _update_list_ui
    ac.events['play'] += _update_playlist_index
    ac.events['video_position'] += _update_current_video_duration
    ac.events['video_position'] += _update_playlist_video_position
    ac.events['stop'] += _save_playlist
    ac.events['resume'] += _update_list_ui
    ac.events['resume'] += _update_playlist_index
    device.set_sync_hook(positionhook=ac.hook, transportstatehook=ac.hook, exceptionhook=ac.excpetionhook)

    # 开始同步状态
    device.start_sync_remote_player_status()

    with patch_stdout():
        
        if play_list.start_play:
            ac.play()

        try:
            while True:
                if ac.end or not player.app.is_running:
                    play_list.playlist.current_pos = ac.current_video_position
                    play_list.playlist.current_index = ac.current_idx
                    play_list.playlist.save_playlist(force=True)
                    break
                time.sleep(0.5)

        finally:
            # 事件无法触发，暂时在这里调用
            _quit()
            player.clear()


def playlist_refresh(args):
    logger = get_logger()
    play_list_file = get_playlist_file_path(args)
    if not os.path.exists(play_list_file):
        logger.info('播放列表[' + args.name + '][' + play_list_file + ']不存在')
        return

    play_list = LocalFilePlaylist(play_list_file)
    play_list.load_playlist()
    play_list.refresh_playlist()
    print(f'播放列表{args.name}刷新完成')


def playlist_update(args):
    logger = get_logger()
    play_list_file = get_playlist_file_path(args)
    if not os.path.exists(play_list_file):
        logger.info('播放列表[' + args.name + '][' + play_list_file + ']不存在')
        return

    play_list = LocalFilePlaylist(play_list_file)
    play_list.load_playlist()

    if args.skip_head > -1:
        play_list.skip_head = args.skip_head
    if args.skip_tail > -1:
        play_list.skip_tail = args.skip_tail
    if args.video_index > -1:
        play_list.current_index = args.video_index
    if args.video_pos > -1:
        play_list.current_pos = args.video_pos
    play_list.save_playlist(force=True)
    print(f'播放列表{args.name}更新完成')


def playlist_view(args):
    logger = get_logger()
    play_list_file = get_playlist_file_path(args)
    if not os.path.exists(play_list_file):
        logger.info('播放列表[' + args.name + '][' + play_list_file + ']不存在')
        return

    play_list = LocalFilePlaylist(play_list_file)
    play_list.load_playlist()

    editor = PlayListEditor(play_list)
    editor.create_content()
    editor.run()


def playlist_rename(args):
    user_dir = get_user_data_dir()

    old_play_list_file = get_playlist_file_path_by_name(get_playlist_dir(user_dir, 'playlist'), args.old_name)
    if not os.path.exists(old_play_list_file):
        print('播放列表[' + args.old_name + '][' + old_play_list_file + ']不存在')
        return

    new_play_list_file = get_playlist_file_path_by_name(get_playlist_dir(user_dir, 'playlist'), args.new_name)
    if os.path.exists(new_play_list_file):
        print('播放列表[' + args.new_name + '][' + new_play_list_file + ']已存在')
        return

    os.rename(old_play_list_file, new_play_list_file)

    if os.path.exists(new_play_list_file):
        print('播放列表重命名成功')
    else:
        print('播放列表重命名失败')


def get_playlist_file_path(args):
    user_dir = get_user_data_dir()
    play_list_dir = get_playlist_dir(user_dir, 'playlist')
    play_list_name = args.name
    play_list_file = os.path.join(play_list_dir, play_list_name + '.playlist')
    return play_list_file


def get_playlist_file_path_by_name(play_list_dir, play_list_name):
    play_list_file = os.path.join(play_list_dir, play_list_name + '.playlist')
    return play_list_file


def stop_device(device: Device):
    device.stop_sync_remote_player_status()
    device.stop()


def quit_prog(*args):
    _DLNA_SERVER.stop_server()
    sys.exit(0)


def init_logger():
    configure = get_abs_path('./logging.json')
    log_dir = Path(get_log_file_dir())
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = get_log_file_path().replace('\\', '/')
    config_text = configure.read_text(encoding='utf-8').replace('{log_file}', log_file)
    config_dict = json.loads(config_text)
    logging.config.dictConfig(config_dict)


def get_logger():
    return logging.getLogger('pysimpledlna.cli')


if __name__ == "__main__":
    main()
