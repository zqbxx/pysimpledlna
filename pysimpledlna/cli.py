import argparse

from pysimpledlna import SimpleDLNAServer


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help='命令')
    command, list_parser = create_list_parser(subparsers)
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


def list_device(args):
    dlna_server = SimpleDLNAServer(9000)
    device_found = False
    for i, device in enumerate(dlna_server.get_devices(args.timeout)):
        print('[', i+1, ']', device.friendly_name, '@', device.location)
        device_found = True
    if not device_found:
        print('No Device available')


if __name__ == "__main__":
    main()
