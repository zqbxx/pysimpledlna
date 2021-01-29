import argparse
import time
import signal
import logging

from pysimpledlna import SimpleDLNAServer, Device
from pysimpledlna.ac import ActionController


_DLNA_SERVER = SimpleDLNAServer(9000)


def main():
    _DLNA_SERVER.start_server()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%H:%M:%S')

    parser = argparse.ArgumentParser()
    wrap_parser_exit(parser)

    subparsers = parser.add_subparsers(help='DLAN Server')
    _, list_parser = create_list_parser(subparsers)
    wrap_parser_exit(list_parser)

    _, play_parser = create_play_parser(subparsers)
    wrap_parser_exit(play_parser)

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
    group.add_argument('-a', '--auto-select', dest='auto_selected', action='store_true', default=True, help='自动选择第一台设备作为播放设备')
    parser.set_defaults(func=play)
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
        device = dlna_server.parse_xml(url)

    dlna_server.register_device(device)

    file_list = args.input
    if len(file_list) == 0:
        return

    ac = ActionController(file_list, device)
    device.set_sync_hook(positionhook=ac.hook, transportstatehook=ac.hook)
    device.start_sync_remote_player_status()
    ac.start_play()
    signal.signal(signal.SIGINT, signal_handler)
    try:
        while True:
            time.sleep(1)
    except:
        stop_device(device)
        dlna_server.stop_server()


def stop_device(device: Device):
    device.stop_sync_remote_player_status()
    device.stop()


def signal_handler(signal, frame):
    raise ServiceExit


class ServiceExit(Exception):
    pass



if __name__ == "__main__":
    main()
