import argparse
import time
import signal
import logging
import os
import re
import fnmatch
import os
print(os.getenv('PYTHONPATH'))
from pysimpledlna import SimpleDLNAServer, Device
from pysimpledlna.ac import ActionController
from pysimpledlna.utils import (
    Playlist, get_playlist_dir, get_user_data_dir, get_free_tcp_port
)


_DLNA_SERVER_PORT = get_free_tcp_port()
_DLNA_SERVER = SimpleDLNAServer(_DLNA_SERVER_PORT)


def main():

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%H:%M:%S')

    parser = argparse.ArgumentParser()
    wrap_parser_exit(parser)

    subparsers = parser.add_subparsers(help='DLAN Server')
    _, list_parser = create_list_parser(subparsers)
    wrap_parser_exit(list_parser)

    _, play_parser = create_play_parser(subparsers)
    wrap_parser_exit(play_parser)

    _, playlist_parser = create_playlist_parser(subparsers)
    playlist_subparsers = playlist_parser.add_subparsers(help='playlist')
    wrap_parser_exit(playlist_parser)

    _, playlist_create_parser = create_playlist_create_parser(playlist_subparsers)
    wrap_parser_exit(playlist_create_parser)

    _, playlist_play_parser = create_playlist_play_parser(playlist_subparsers)
    wrap_parser_exit(playlist_play_parser)

    _, playlist_list_parser = create_playlist_list_parser(playlist_subparsers)
    wrap_parser_exit(playlist_play_parser)

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


def create_list_parser(subparsers):
    command = 'list'
    parser = subparsers.add_parser(command, help='list dlna device')
    parser.add_argument('-t', '--timeout', dest='timeout', required=False, default=5, type=int, help='timeout')
    parser.add_argument('-m', '--max', dest='max', required=False, default=99999, type=int,
                             help='maximum number of dlna device')
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
    parser.add_argument('-n', '--name', dest='name', required=True, type=str, help='playlist name')
    parser.add_argument('-i', '--input', dest='input', required=True, type=str, nargs='+', help='folders')
    parser.add_argument('-f', '--filter', dest='filter', required=False, type=str, help='filter')
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


def list_device(args):
    dlna_server = _DLNA_SERVER
    device_found = False
    for i, device in enumerate(dlna_server.get_devices(args.timeout)):
        print('[', i+1, ']', device.friendly_name, '@', device.location)
        device_found = True
    if not device_found:
        print('No Device available')


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
            device = None
        else:
            device = dlna_server.parse_xml(url)
    if device is None:
        print('No Device available')
        return

    dlna_server.register_device(device)

    file_list = args.input
    if len(file_list) == 0:
        return

    ac = ActionController(file_list, device)
    device.set_sync_hook(positionhook=ac.hook, transportstatehook=ac.hook, exceptionhook=ac.excpetionhook)
    device.start_sync_remote_player_status()
    ac.start_play()
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
    pattern = None
    if filename_filter is not None:
        regex = fnmatch.translate(filename_filter)
        pattern = re.compile(regex)
    files = [os.path.join(input_dir, file_name) for input_dir in input_dirs for file_name in os.listdir(input_dir)
             if pattern is not None and pattern.search(file_name) is not None]
    pl = Playlist(play_list_file)
    pl._file_list = files
    pl.save_playlist()

    logging.info('播放列表已保存:' + play_list_file)


def playlist_delete(args):
    play_list_file = get_playlist_file_path(args)
    if not os.path.exists(play_list_file):
        logging.info('播放列表[' + args.name + ']['+ play_list_file + ']不存在')
        return
    if os.path.isfile(play_list_file):
        os.remove(play_list_file)
        logging.info('播放列表[' + args.name + ']['+ play_list_file + ']已删除')
        return
    logging.info('播放列表不是文件，无法删除[' + args.name + ']['+ play_list_file + ']')


def playlist_list(args):
    user_dir = get_user_data_dir()
    play_list_dir = get_playlist_dir(user_dir, 'playlist')
    play_list = [ os.path.splitext(f)[0] for f in os.listdir(play_list_dir) if os.path.isfile(os.path.join(play_list_dir, f)) and f.endswith('.playlist')]

    print('播放列表目录：', play_list_dir)

    if len(play_list) == 0:
        print('没有播放列表')

    for i, pl in enumerate(play_list):
        print('[' + str(i) + ']', pl)


def playlist_play(args):

    from pysimpledlna.ui.playlist import (
        PlayListPlayer, PlayerModel,
        VideoPositionFormatter, VideoControlFormatter, VideoFileFormatter)
    from prompt_toolkit_ext.widgets import RadioList
    from prompt_toolkit.shortcuts.progress_bar.formatters import Text
    from pysimpledlna.ui.terminal import PlayerStatus
    from prompt_toolkit.key_binding import KeyBindings
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
            device = None
        else:
            device = dlna_server.parse_xml(url)
    if device is None:
        print('No Device available')
        return

    dlna_server.register_device(device)

    play_list_file = get_playlist_file_path(args)
    if not os.path.exists(play_list_file):
        logging.info('播放列表[' + args.name + ']['+ play_list_file + ']不存在')
        return

    play_list = Playlist(play_list_file)
    play_list.load_playlist()
    file_list = play_list.file_list
    playlist_values = [(f, os.path.split(f)[1]) for f in file_list]
    playlist_contents = RadioList(values=playlist_values)

    formatters = [
        Text(" "),
        VideoPositionFormatter(),
        Text(" | "),
        VideoControlFormatter(),
        Text(" "),
        VideoFileFormatter()
    ]
    title_toolbar = HTML('<b>[n]</b>播放列表<b>[m]</b>进度条')
    bottom_toolbar = HTML('<b>[q]</b>退出<b>[p]</b>暂停')
    player = PlayListPlayer(playlist_contents, formatters=formatters, bottom_toolbar=bottom_toolbar, title=title_toolbar)
    player_model: PlayerModel = player.create_model()
    ac = ActionController(file_list, device, player_model)

    def on(type, old_value, new_value):
        if type == 'selected':

            old_file_path = old_value[0]
            old_file_name = old_value[1]

            new_file_path = new_value[0]
            new_file_name = new_value[1]

            if os.path.samefile(old_file_path, new_file_path):
                return True

            selected_index = playlist_contents.get_selected_index()

            ac.current_idx = selected_index
            ac.play_next()
        return True

    playlist_contents.add_enter_handle(on)

    kb = KeyBindings()

    @kb.add("q")
    def _(event):
        " Quit application. "
        #event.app.exit()
        player.exit()
        player_model.player_status = PlayerStatus.STOP
        ac.stop_device()

    @kb.add("n")
    def _(event):
        event.app.layout.focus(player.get_left_part())

    @kb.add("m")
    def _(event):
        event.app.layout.focus(player.get_right_part())

    @kb.add('p')
    def _(event):
        if player_model.player_status == PlayerStatus.PAUSE:
            player_model.player_status = PlayerStatus.PLAY
        elif player_model.player_status == PlayerStatus.PLAY:
            player_model.player_status = PlayerStatus.PAUSE

    player.key_bindings = kb
    player.create_ui()

    device.set_sync_hook(positionhook=ac.hook, transportstatehook=ac.hook, exceptionhook=ac.excpetionhook)
    device.start_sync_remote_player_status()

    with patch_stdout():
        ac.start_play()

    try:
        while True:
            if ac.end:
                break
            time.sleep(0.5)
    finally:
        device.stop_sync_remote_player_status()
        dlna_server.stop_server()
        player.clear()


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
