import argparse
import time
import signal

from pysimpledlna import SimpleDLNAServer


def main():
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
    play_parser.add_argument('-i', '--input', dest='input', required=True, type=str, help='video file')
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
    file_path = args.input
    device = dlna_server.parse_xml(url)
    dlna_server.register_device(device)
    dlna_server.start_server()
    file_url = dlna_server.add_file_to_server(device, file_path)
    device.set_AV_transport_URI(file_url)
    device.play()
    device.set_sync_hook(positionhook=positionhook, transportstatehook=positionhook)
    device.start_sync_remote_player_status()
    signal.signal(signal.SIGINT, signal_handler)
    try:
        while True:
            time.sleep(1)
    except ServiceExit:
        device.stop_sync_remote_player_status()
        dlna_server.stop_server()


def signal_handler(signal, frame):
    raise ServiceExit


class ServiceExit(Exception):
    pass


def positionhook(type, old_value, new_value):
    print('type: ', type, ' old:', old_value, ' new:', new_value)

if __name__ == "__main__":
    main()
