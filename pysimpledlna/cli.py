import argparse
import time
import signal
import logging
import os

from pysimpledlna import SimpleDLNAServer, Device


_DLNA_SERVER = SimpleDLNAServer(9000)
_DLNA_SERVER.start_server()


def main():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%H:%M:%S')
    parser = argparse.ArgumentParser()
    wrap_parser_exit(parser)
    subparsers = parser.add_subparsers(help='命令')
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
    list_parser = subparsers.add_parser(command, help='list dlna device')
    list_parser.add_argument('-t', '--timeout', dest='timeout', required=False, default=5, type=int, help='timeout')
    list_parser.add_argument('-m', '--max', dest='max', required=False, default=99999, type=int,
                             help='maximum number of dlna device')
    list_parser.set_defaults(func=list_device)
    return command, list_parser


def create_play_parser(subparsers):
    command = 'play'
    play_parser = subparsers.add_parser(command, help='play a video')
    play_parser.add_argument('-i', '--input', dest='input', required=True, type=str, nargs='+',  help='video file')
    play_parser.add_argument('-u', '--url', dest='url', required=True, type=str,
                             help='dlna device url')
    play_parser.set_defaults(func=play)
    return command, play_parser


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
    url = args.url
    file_list = args.input

    if len(file_list) == 0:
        return

    device = dlna_server.parse_xml(url)
    dlna_server.register_device(device)

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


class ActionController:

    '''
    自己实现连续播放多个文件的功能，部分DLNA设备没有实现用于连续播放的接口
    '''
    def __init__(self, file_list, device: Device):
        self.current_idx = 0
        self.file_list = file_list
        self.device = device

        self.current_video_position = 0
        self.current_video_duration = 0

    def start_play(self):
        self.play_next()

    def hook(self, type, old_value, new_value):

        logging.debug('type: ' + type + ' old:' + str(old_value) + ' new:' + str(new_value))

        if type == 'CurrentTransportState':
            logging.debug('try play next video:')
            logging.debug('current_video_position:' + str(self.current_video_position))
            logging.debug('current_video_duration:' + str(self.current_video_duration))
            if old_value in ['PLAYING', 'PAUSED_PLAYBACK'] and new_value == 'STOPPED':
                if self.current_video_position >= self.current_video_duration - 3 * self.device.sync_remote_player_interval:
                    # 只对播放文件末尾时间进行处理
                    if self.current_idx < len(self.file_list):
                        logging.debug('play next video')
                        self.play_next()
                else:
                    stop_device(self.device)
                    os.kill(signal.CTRL_C_EVENT, 0)

        elif type == 'TrackDurationInSeconds':
            self.current_video_duration = new_value
        elif type == 'RelTimeInSeconds':
            self.current_video_position = new_value

    def play_next(self):
        file_path = self.file_list[self.current_idx]
        server_file_path = self.device.add_file(file_path)
        self.device.set_AV_transport_URI(server_file_path)
        self.device.play()
        self.current_idx += 1


if __name__ == "__main__":
    main()
