import argparse
import time
import signal
import logging
import os
import re
import fnmatch
from pysimpledlna import SimpleDLNAServer, Device
from pysimpledlna.ac import ActionController
from pysimpledlna.utils import (
    Playlist, get_playlist_dir, get_user_data_dir, get_free_tcp_port
)


_DLNA_SERVER_PORT = get_free_tcp_port()
_DLNA_SERVER = SimpleDLNAServer(_DLNA_SERVER_PORT)
_DLNA_SERVER.start_server()


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

    args = parser.parse_args()
    try:
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

    group.add_argument('-u', '--url', dest='url', type=str,
                             help='dlna device url')
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
    parser.add_argument('-n', '--name', dest='name', required=True, type=str, help='playlist name')
    parser.set_defaults(func=playlist_delete)

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
