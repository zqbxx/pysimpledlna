import argparse
import json
import time
import signal
import logging

from pysimpledlna.ui.playlist import PlayListEditor

logging.basicConfig(  # filename=,
    format='%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s',
    datefmt='%H:%M:%S',
    level=logging.INFO,
    handlers=[
        # logging.StreamHandler(),
        logging.FileHandler('log.txt'),
    ], )

logger = logging.getLogger('pysimpledlna.cli')
logger.setLevel(logging.INFO)


import os
from pysimpledlna import SimpleDLNAServer, Device
from pysimpledlna.ac import ActionController
from pysimpledlna.utils import (
    get_playlist_dir, get_user_data_dir, get_free_tcp_port, get_setting_file_path)
from pysimpledlna.entity import Playlist, Settings

_DLNA_SERVER_PORT = get_free_tcp_port()
settings = Settings(get_setting_file_path())
_DLNA_SERVER = SimpleDLNAServer(
    server_port=_DLNA_SERVER_PORT,
    is_enable_ssl=settings.get_enable_ssl(),
    cert_file=settings.get_cert_file(),
    key_file=settings.get_key_file()
)


def main():

    parser = argparse.ArgumentParser()
    wrap_parser_exit(parser)

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

    args = parser.parse_args()
    try:
        _DLNA_SERVER.start_server()
        args.func(args)
    finally:
        _DLNA_SERVER.stop_server()


def wrap_parser_exit(parser: argparse.ArgumentParser):
    exit_func = parser.exit

    def exit(status=0, message=None):
        _DLNA_SERVER.stop_server()
        exit_func(status, message)

    parser.exit = exit


def create_default_device_parser(subparsers):
    command = 'config'
    parser = subparsers.add_parser(command, help='设置参数')
    parser.add_argument('-u', '--url', dest='url', required=False, type=str, default=None, help='默认DLNA设备地址')
    parser.add_argument('-es', '--enable-ssl', dest='enable_ssl', required=False, type=str, default=None, choices=['True', 'true', 'False', 'false', ], help='是否启用SSL')
    parser.add_argument('-p', '--print', dest='print_opts', required=False, default=False, action='store_true', help='是否输出配置信息')
    parser.add_argument('-cert', '--cert-file', dest='cert_file', required=False, default=None, help='用于https的公钥')
    parser.add_argument('-key', '--key-file', dest='key_file', required=False, default=None, help='用于https的私钥')
    parser.set_defaults(func=default)
    return command, parser


def create_list_parser(subparsers):
    command = 'list'
    parser = subparsers.add_parser(command, help='查找DLNA设备')
    parser.add_argument('-t', '--timeout', dest='timeout', required=False, default=5, type=int, help='timeout')
    parser.add_argument('-m', '--max', dest='max', required=False, default=99999, type=int, help='查找DLNA设备的最大数量')
    parser.set_defaults(func=list_device)
    return command, parser


def create_play_parser(subparsers):
    command = 'play'
    parser = subparsers.add_parser(command, help='play a video')
    parser.add_argument('-i', '--input', dest='input', required=True, type=str, nargs='+',  help='视频文件')
    group = parser.add_mutually_exclusive_group()

    group.add_argument('-u', '--url', dest='url', type=str, help='dlna device url')
    group.add_argument('-a', '--auto-select', dest='auto_selected', action='store_true', default=False, help='自动选择第一台设备作为播放设备')
    parser.set_defaults(func=play)
    return command, parser


def create_playlist_parser(subparsers):
    command = 'playlist'
    return command, subparsers.add_parser(command, help='play a video')


def create_playlist_create_parser(subparsers):
    command = 'create'
    parser = subparsers.add_parser(command, help='create playlist')
    parser.add_argument('-n', '--name', dest='name', required=True, type=str, help='播放列表名字')
    parser.add_argument('-i', '--input', dest='input', required=True, type=str, nargs='+', help='包含目标文件的目录')
    parser.add_argument('-f', '--filter', dest='filter', required=False, type=str, help='文件过滤器')
    parser.add_argument('-sh', '--skip-head', dest='skip_head', required=False, type=int, default=0, help='跳过片头时间')
    parser.add_argument('-st', '--skip-tail', dest='skip_tail', required=False, type=int, default=0, help='跳过片尾时间')
    parser.set_defaults(func=playlist_create)

    return command, parser


def create_playlist_delete_parser(subparsers):
    command = 'delete'
    parser = subparsers.add_parser(command, help='create playlist')
    parser.add_argument('-n', '--name', dest='name', required=True, type=str, help='播放列表名字')
    parser.set_defaults(func=playlist_delete)

    return command, parser


def create_playlist_play_parser(subparsers):
    command = 'play'
    parser = subparsers.add_parser(command, help='播放播放列表中的文件')
    parser.add_argument('-n', '--name', dest='name', required=True, type=str, help='播放列表名字')
    group = parser.add_mutually_exclusive_group()

    group.add_argument('-u', '--url', dest='url', type=str, help='dlna设备地址')
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
    parser = subparsers.add_parser(command, help='更新播放列表')
    parser.add_argument('-n', '--name', dest='name', required=True, type=str, help='播放列表名字')
    parser.set_defaults(func=playlist_view)
    return command, parser


def default(args):
    dlna_server = _DLNA_SERVER
    setting_file_path = get_setting_file_path()
    settings = Settings(setting_file_path)

    if args.url is not None:
        settings.set_default_device(args.url)

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
    for i, device in enumerate(dlna_server.get_devices(args.timeout)):
        print('[', i+1, ']', device.friendly_name, '@', device.location)
        device_found = True
        if (i+1) >= max_number:
            break
    if not device_found:
        print('没有找到设备')


def play(args):

    dlna_server = _DLNA_SERVER

    device: Device = None
    if args.auto_selected:
        for i, d in enumerate(dlna_server.get_devices(5)):
            device = d
            break
    else:
        url = args.url
        if url is None:
            settings = Settings(get_setting_file_path())
            default_device_url = settings.get_default_device()
            device = dlna_server.find_device(default_device_url)
        else:
            device = dlna_server.parse_xml(url)

    if device is None:
        print('没有找到DLNA设备')
        return

    dlna_server.register_device(device)

    file_list = args.input
    if len(file_list) == 0:
        return

    ac = ActionController(file_list, device)
    device.set_sync_hook(positionhook=ac.hook, transportstatehook=ac.hook, exceptionhook=ac.excpetionhook)
    device.start_sync_remote_player_status()
    ac.play()
    signal.signal(signal.SIGINT, signal_handler)
    try:
        while True:
            time.sleep(1)
    except:
        stop_device(device)
        dlna_server.stop_server()


def playlist_create(args):
    play_list_file = get_playlist_file_path(args)
    input_dirs: [] = args.input
    filename_filter: str = args.filter
    pl = Playlist(play_list_file, filter=filename_filter, input=input_dirs)
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

    from pysimpledlna.ui.playlist import (
        PlayListPlayer, PlayerModel,
        VideoPositionFormatter, VideoControlFormatter, VideoFileFormatter)
    from pysimpledlna.utils import format_time
    from prompt_toolkit_ext.widgets import RadioList
    from prompt_toolkit.shortcuts.progress_bar.formatters import Text
    from pysimpledlna.ui.terminal import PlayerStatus
    from prompt_toolkit.patch_stdout import patch_stdout
    from prompt_toolkit import HTML

    dlna_server = _DLNA_SERVER

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
                default_device_url = settings.get_default_device()
                device = dlna_server.find_device(default_device_url)
        else:
            device = dlna_server.parse_xml(url)
    if device is None:
        print('No Device available')
        return

    dlna_server.register_device(device)

    play_list_file = get_playlist_file_path(args)
    if not os.path.exists(play_list_file):
        logger.info('播放列表[' + args.name + '][' + play_list_file + ']不存在')
        return

    play_list = Playlist(play_list_file)
    play_list.load_playlist()
    file_list = play_list.file_list
    playlist_values = [(f, os.path.split(f)[1]) for f in file_list]
    playlist_contents = RadioList(values=playlist_values)

    player = PlayListPlayer(playlist_contents)
    player_model: PlayerModel = player.create_model()
    ac = ActionController(file_list, device, player_model)

    def _item_checked(old_value, new_value):
        old_file_path = old_value[0]
        old_file_name = old_value[1]

        new_file_path = new_value[0]
        new_file_name = new_value[1]

        if os.path.samefile(old_file_path, new_file_path):
            return True

        selected_index = playlist_contents.get_selected_index()

        ac.current_idx = selected_index
        ac.play()

    def _update_list_ui(current_index):
        playlist_contents.current_value = playlist_contents.values[current_index][0]

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

    def _backward(event, times):
        target_position = ac.current_video_position - 10 * times
        if target_position <= 0:
            target_position = 1
        time_str = format_time(target_position)
        ac.device.seek(time_str)

    def _next(event, times):
        ac.current_idx += times
        if ac.current_idx >= len(playlist_contents.values):
            ac.current_idx = len(playlist_contents.values) - 1
        ac.play()

    def _last(event, times):
        ac.current_idx -= times
        if ac.current_idx < 0:
            ac.current_idx = 0
        ac.play()

    def _update_playlist_index(current_index):
        play_list.current_index = current_index
        play_list._current_pos = 0
        play_list.save_playlist(force=True)

    def _update_playlist_video_position(o_position, n_position):
        play_list.current_pos = n_position
        play_list.save_playlist()

    playlist_contents.check_event += _item_checked

    player.create_key_bindings()
    player.create_ui()

    player.player_events['quit'] += lambda e: ac.stop_device()
    player.controller_events['pause'] += \
        lambda e: ac.device.play() if player_model.player_status == PlayerStatus.PAUSE else ac.device.pause()
    player.controller_events['last'] += _last
    player.controller_events['next'] += _next
    player.controller_events['forward'] += _forward
    player.controller_events['backward'] += _backward

    ac.events['play'] += _update_list_ui
    ac.events['play'] += _update_playlist_index
    ac.events['video_position'] += _update_playlist_video_position

    device.set_sync_hook(positionhook=ac.hook, transportstatehook=ac.hook, exceptionhook=ac.excpetionhook)
    device.start_sync_remote_player_status()

    playlist_contents.set_checked_index(play_list.current_index)
    ac.current_idx = play_list.current_index
    position_in_playlist = dict()
    position_in_playlist['current_pos'] = play_list.current_pos
    position_in_playlist['current_index'] = play_list.current_index

    def _skip_head(current_index):
        
        logger.debug('==start==')
        logger.debug(f'cur index: {current_index}')
        logger.debug(f"position_in_playlist: {position_in_playlist['current_pos']}")
        logger.debug(f'current_video_position: {ac.current_video_position}')
        logger.debug(f'seek to {format_time(play_list.skip_head)}')
        logger.debug('== end ==')

        if position_in_playlist['current_pos'] > 0 and position_in_playlist['current_index'] == ac.current_idx:
            if position_in_playlist['current_pos'] > ac.current_video_position:
                time_str = format_time(position_in_playlist['current_pos'])
                ac.device.seek(time_str)
                play_list.current_pos = position_in_playlist['current_pos']
                play_list.save_playlist(force=True)
                position_in_playlist['current_pos'] = -1
        elif play_list.skip_head > 0:
            time.sleep(0.5)
            time_str = format_time(play_list.skip_head)
            ac.device.seek(time_str)
            play_list.current_pos = play_list.skip_head
            play_list.save_playlist(force=True)

    ac.events['play'] += _skip_head

    def _skip_tail(o_position, n_position):
        if play_list.skip_tail == 0:
            return
        end = ac.get_max_video_position() - play_list.skip_tail
        if n_position >= end and end > 0:
            ac.play_next()

    ac.events['video_position'] += _skip_tail

    with patch_stdout():
        ac.play()

        try:
            while True:
                if ac.end or not player.app.is_running:
                    play_list.current_pos = ac.current_video_position
                    play_list.current_index = ac.current_idx
                    play_list.save_playlist(force=True)
                    break
                time.sleep(0.5)

        finally:
            device.stop_sync_remote_player_status()
            dlna_server.stop_server()
            player.clear()


def playlist_refresh(args):
    play_list_file = get_playlist_file_path(args)
    if not os.path.exists(play_list_file):
        logger.info('播放列表[' + args.name + '][' + play_list_file + ']不存在')
        return

    play_list = Playlist(play_list_file)
    play_list.load_playlist()
    play_list.refresh_playlist()
    print(f'播放列表{args.name}刷新完成')


def playlist_update(args):
    play_list_file = get_playlist_file_path(args)
    if not os.path.exists(play_list_file):
        logger.info('播放列表[' + args.name + '][' + play_list_file + ']不存在')
        return

    play_list = Playlist(play_list_file)
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
    play_list_file = get_playlist_file_path(args)
    if not os.path.exists(play_list_file):
        logger.info('播放列表[' + args.name + '][' + play_list_file + ']不存在')
        return

    play_list = Playlist(play_list_file)
    play_list.load_playlist()

    editor = PlayListEditor(play_list)
    editor.create_content()
    editor.run()


def get_playlist_file_path(args):
    user_dir = get_user_data_dir()
    play_list_dir = get_playlist_dir(user_dir, 'playlist')
    play_list_name = args.name
    play_list_file = os.path.join(play_list_dir, play_list_name + '.playlist')
    return play_list_file


def stop_device(device: Device):
    device.stop_sync_remote_player_status()
    device.stop()


def signal_handler(signal, frame):
    raise ServiceExit


class ServiceExit(Exception):
    pass


if __name__ == "__main__":
    main()
