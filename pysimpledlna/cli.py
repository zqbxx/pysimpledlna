import argparse
import time
import signal
import logging
import sys
import os

from pysimpledlna import SimpleDLNAServer, Device


def main():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%H:%M:%S')
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help='命令')
    create_list_parser(subparsers)
    create_play_parser(subparsers)
    args = parser.parse_args()
    args.func(args)


def create_list_parser(subparsers):
    command = 'list'
    list_parser = subparsers.add_parser(command, help='list dlna device')
    list_parser.add_argument('-t', '--timeout', dest='timeout', required=False, default=5, type=int, help='timeout')
    list_parser.add_argument('-m', '--max', dest='max', required=False, default=99999, type=int,
                             help='maximum number of dlna device')
    list_parser.set_defaults(func=list_device)
    return 'list', list_parser


def create_play_parser(subparsers):
    command = 'play'
    play_parser = subparsers.add_parser(command, help='play a video')
    play_parser.add_argument('-i', '--input', dest='input', required=True, type=str, nargs='+',  help='video file')
    play_parser.add_argument('-u', '--url', dest='url', required=True, type=str,
                             help='dlna device url')
    play_parser.set_defaults(func=play)


def list_device(args):
    dlna_server = SimpleDLNAServer(9000)
    device_found = False
    for i, device in enumerate(dlna_server.get_devices(args.timeout)):
        print('[', i+1, ']', device.friendly_name, '@', device.location)
        device_found = True
    if not device_found:
        print('No Device available')


def play(args):

    dlna_server = SimpleDLNAServer(9000)
    url = args.url
    file_list = args.input

    if len(file_list) == 0:
        return

    device = dlna_server.parse_xml(url)
    dlna_server.register_device(device)
    dlna_server.start_server()

    ac = ActionController(file_list, device)
    device.set_sync_hook(positionhook=ac.hook, transportstatehook=ac.hook)
    device.start_sync_remote_player_status()
    ac.start_play()
    signal.signal(signal.SIGINT, signal_handler)
    try:
        while True:
            time.sleep(1)
    except:
        stop_app(device, dlna_server)


def stop_app(device: Device, dlna_server: SimpleDLNAServer):
    device.stop_sync_remote_player_status()
    device.stop()
    dlna_server.stop_server()


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
            if old_value in ['PLAYING', 'PAUSED_PLAYBACK'] and new_value == 'STOPPED':
                if self.current_video_position >= self.current_video_duration - 2 * self.device.sync_remote_player_interval:
                    # 只对播放文件末尾时间进行处理
                    if self.current_idx < len(self.file_list):
                        self.play_next()
                else:
                    stop_app(self.device, self.device.dlna_server)
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
