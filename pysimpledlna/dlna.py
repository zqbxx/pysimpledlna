import os
import pkgutil
import socket
import threading
import urllib.request as urllibreq
from urllib.parse import urljoin, urlparse
from urllib.parse import urlparse
import xml.dom.minidom as xmldom

import requests
from twisted.internet import reactor
from twisted.web.resource import Resource
from twisted.web.server import Site
from twisted.web.static import File

from threading import Thread, Event
from enum import Enum, IntEnum, unique
import time
import traceback
import logging


SSDP_BROADCAST_ADDR = "239.255.255.250"
SSDP_BROADCAST_PORT = 1900
SSDP_BROADCAST_PARAMS = [
    "M-SEARCH * HTTP/1.1",
    f"HOST: {SSDP_BROADCAST_ADDR}:{SSDP_BROADCAST_PORT}",
    "MAN: \"ssdp:discover\"",
    "MX: 10",
    "ST: ssdp:all",
    "", ""
]
SSDP_BROADCAST_MSG = "\r\n".join(SSDP_BROADCAST_PARAMS)
UPNP_DEFAULT_SERVICE_TYPE = "urn:schemas-upnp-org:service:AVTransport:1"


class SimpleDLNAServer():

    def __init__(self, server_port):
        self.server_port = server_port
        self.root = Resource()
        self.server_ip = socket.gethostbyname(socket.gethostname())
        self.known_devices = {}
        self.is_server_started = False

    def start_server(self):
        reactor.listenTCP(self.server_port, Site(self.root))
        threading.Thread(target=reactor.run, kwargs={"installSignalHandlers": False}).start()
        self.is_server_started = True

    def stop_server(self):
        if self.is_server_started:
            reactor.stop()
            self.is_server_started = False


    def add_file_to_server(self, device, file_path):

        file_name, file_url, file_path = self.set_files(device, file_path)
        device_resource = self.root.children.get(device.device_key)

        if device_resource is None:
            device_resource = Resource()
            self.root.putChild(device.device_key.encode("utf-8"), device_resource)
        self.root.children[device.device_key.encode("utf-8")].putChild(file_name.encode("utf-8"), File(file_path))

        return file_url

    def get_device_root(self, device):
        device_root = self.root.children.get(device.device_key)
        if device_root is None:
            device_root = Resource()
            self.root.putChild(device.device_key.encode("utf-8"), device_root)
        return device_root

    def is_file_on_server(self, device, file_path):
        file_name, file_url, file_path = self.set_files(file_path)
        device_resource = self.root.children.get(device.UID)
        if device_resource is None:
            return False
        server_file = device_resource.children.get(file_name.encode("utf-8"))
        if server_file is None:
            return False
        return True

    def update_server_ip(self, target_ip, target_port=80):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((target_ip, target_port))
        self.server_ip = s.getsockname()[0]
        s.close()

    def set_files(self, device, file):

        file_path = os.path.abspath(file)
        file_name = os.path.basename(file_path)
        file_url = "http://{0}:{1}/{2}/{3}".format(self.server_ip, self.server_port, device.device_key, file_name)

        return file_name, file_url, file_path

    def parse_xml(self, url):
        try:
            content = requests.get(url).content.decode()
            domtree = xmldom.parseString(content)
            document = domtree.documentElement
            device_element = document.getElementsByTagName('device')[0]
            friendlyName = device_element.getElementsByTagName('friendlyName')[0].firstChild.data
            manufacturer = device_element.getElementsByTagName('manufacturer')[0].firstChild.data
            manufacturerURL = device_element.getElementsByTagName('manufacturerURL')[0].firstChild.data
            '''
            presentationURL = device_element.getElementsByTagName('presentationURL')[0].firstChild.data
            modelDescription = device_element.getElementsByTagName('modelDescription')[0].firstChild.data
            modelName = device_element.getElementsByTagName('modelName')[0].firstChild.data
            modelURL = device_element.getElementsByTagName('modelURL')[0].firstChild.data
            X_DLNADOC = device_element.getElementsByTagName('dlna:X_DLNADOC')[0].firstChild.data
            UDN = device_element.getElementsByTagName('UDN')[0].firstChild.data
            UID = device_element.getElementsByTagName('UID')[0].firstChild.data
            '''

            urlgroup = urlparse(url)
            device_key = urlgroup.hostname.replace('.', '_')

            if urlgroup.port:
                from builtins import str
                device_key += '__' + str(urlgroup.port)

            avtranspor_control_url = None
            rendering_control_url = None
            serviceType_elements = device_element.getElementsByTagName('serviceType')
            for serviceType_element in serviceType_elements:
                str = serviceType_element.firstChild.data
                if 'urn:schemas-upnp-org:service:AVTranspor' in str:
                    avtranspor_control_url = serviceType_element.parentNode.getElementsByTagName('controlURL')[0].firstChild.data
                elif 'urn:schemas-upnp-org:service:RenderingControl' in str:
                    rendering_control_url = serviceType_element.parentNode.getElementsByTagName('controlURL')[0].firstChild.data

            device = Device(self, location=url, host=urlparse(url).hostname
                            , friendly_name=friendlyName
                            , avtranspor_action_url=urljoin(url, avtranspor_control_url)
                            , rendering_action_url=urljoin(url, rendering_control_url)
                            , manufacturer=manufacturer
                            , manufacturer_url=manufacturerURL
                            , st=UPNP_DEFAULT_SERVICE_TYPE
                            , device_key=device_key)

            return device
        except Exception as e:
            print(e)
            return None


    def get_devices(self, timeout=10):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 4)
        s.bind((socket.gethostbyname(socket.gethostname()), SSDP_BROADCAST_PORT + 10))

        s.sendto(SSDP_BROADCAST_MSG.encode(), (SSDP_BROADCAST_ADDR, SSDP_BROADCAST_PORT))
        s.settimeout(timeout)

        while 1:

            try:
                data, addr = s.recvfrom(1024)
            except socket.timeout:
                break

            def serialize(x):
                try:
                    k, v = x.split(":", maxsplit=1)
                except ValueError:
                    pass
                else:
                    return k.lower(), v.lstrip()

            device_dict = dict(map(serialize, filter(lambda x: x.count(":") >= 1, data.decode().split("\r\n"))))

            if "AVTransport" in device_dict["st"]:
                yield self.register_device(self.parse_xml(device_dict["location"]))

    def register_device(self, device):
        if device is not None:
            self.known_devices[device.device_key] = device
        return device

    def find_device(self, location_url):
        return self.register_device(self.parse_xml(location_url))

    def send_dlna_action(self, data, device, action):

        action_data = pkgutil.get_data("pysimpledlna", "templates/action-{0}.xml".format(action)).decode("UTF-8")
        action_data = action_data.format(**data).encode("UTF-8")

        headers = {
            "Content-Type": "text/xml; charset=\"utf-8\"",
            "Content-Length": "{0}".format(len(action_data)),
            "Connection": "close",
            "SOAPACTION": "\"{0}#{1}\"".format(device.st, action)
        }

        action_url = device.avtranspor_action_url
        if action in ['GetVolume', 'SetMute', 'SetVolume']:
            action_url = device.rendering_action_url

        request = urllibreq.Request(action_url, action_data, headers)
        res = urllibreq.urlopen(request)
        return res.read().decode("utf-8")


class Device():

    REMOTE_PLAYER_PLAYING = 'PLAYING'
    REMOTE_PLAYER_PAUSED = 'PAUSED_PLAYBACK'
    REMOTE_PLAYER_STOPPED = 'STOPPED'

    def __init__(self, dlna_server: SimpleDLNAServer
                 , location, host, friendly_name
                 , avtranspor_action_url, rendering_action_url
                 , manufacturer , manufacturer_url, st, device_key
                 , sync_remote_player_interval=1
                 , positionhook=None, transportstatehook=None):

        self.dlna_server = dlna_server

        self.location = location
        self.host = host
        self.friendly_name = friendly_name
        self.avtranspor_action_url = avtranspor_action_url
        self.rendering_action_url = rendering_action_url
        self.manufacturer = manufacturer
        self.manufacturer_url = manufacturer_url
        self.st = st
        self.device_key = device_key
        self.positionhook = positionhook
        self.transportstatehook = transportstatehook
        self.sync_remote_player_interval = sync_remote_player_interval

        self.video_files = self.dlna_server.get_device_root(self)

        self.sync_thread = DlnaDeviceSyncThread(self, interval=self.sync_remote_player_interval)

    def add_file(self, file_path):
        file_name, file_url, file_path = self.dlna_server.set_files(self, file_path)
        self.video_files.putChild(file_name.encode("utf-8"), File(file_path))
        return file_url

    def remove_file(self, file_path):
        file_name, file_url, file_path = self.dlna_server.set_files(self, file_path)
        if self.video_files.children.get(file_name.encode("utf-8")) is not None:
            del self.video_files.children[file_name.encode("utf-8")]

    def set_sync_interval(self, interval):
        self.sync_remote_player_interval = interval
        self.sync_thread.interval = interval

    def set_sync_hook(self, positionhook, transportstatehook):
        self.positionhook = positionhook
        self.transportstatehook = transportstatehook

    def start_sync_remote_player_status(self):
        if self.sync_thread:
            self.sync_thread.start()
            return True
        return False

    def pause_sync_remote_player_status(self):
        if self.sync_thread:
            self.sync_thread.send_pause_event()
            return True
        return False

    def resume_sync_remote_player_status(self):
        if self.sync_thread:
            self.sync_thread.send_resume_event()
            return True
        return False

    def stop_sync_remote_player_status(self):
        if self.sync_thread:
            self.sync_thread.send_stop_event(self.__after_sync_thread_stopped)
            return True
        return False

    def __after_sync_thread_stopped(self):
        old_thread = self.sync_thread
        self.sync_thread = DlnaDeviceSyncThread(self
                                                , interval=self.sync_remote_player_interval
                                                , last_status=old_thread.last_status)

    def set_AV_transport_URI(self, files_urls):
        video_data = {
            "uri_video": files_urls,
            "type_video": os.path.splitext(files_urls)[1][1:],
        }
        video_data["metadata"] = ""
        self.dlna_server.send_dlna_action(video_data, self, "SetAVTransportURI")

    def play(self):
        self.dlna_server.send_dlna_action({}, self, "Play")

    def pause(self):
        self.dlna_server.send_dlna_action({}, self, "Pause")

    def stop(self):
        self.dlna_server.send_dlna_action({}, self, "Stop")

    def seek(self, position):
        self.dlna_server.send_dlna_action({"Target": position}, self, "Seek")

    def volume(self, volume):
        try:
            self.dlna_server.send_dlna_action({"DesiredVolume": volume}, self, "SetVolume")
        except Exception as e:
            print(e)

    def get_volume(self):
        try:
            content = self.dlna_server.send_dlna_action({}, self, "GetVolume")
            domtree = xmldom.parseString(content)
            document = domtree.documentElement
            return int(document.getElementsByTagName('CurrentVolume')[0].firstChild.data)
        except Exception as e:
            print(e)
            return -1

    def mute(self):
        try:
            self.dlna_server.send_dlna_action({}, self, "SetMute")
        except Exception as e:
            print(e)

    def unmute(self):
        self.dlna_server.mute()

    def transport_info(self):

        content = self.dlna_server.send_dlna_action({}, self, "GetTransportInfo")
        domtree = xmldom.parseString(content)
        document = domtree.documentElement

        CurrentTransportState = document.getElementsByTagName('CurrentTransportState')[0].firstChild.data
        CurrentTransportStatus = document.getElementsByTagName('CurrentTransportStatus')[0].firstChild.data
        CurrentSpeed = document.getElementsByTagName('CurrentSpeed')[0].firstChild.data

        ret_data = {
            'CurrentTransportState': CurrentTransportState,
            'CurrentTransportStatus': CurrentTransportStatus,
            'CurrentSpeed': CurrentSpeed
        }

        return ret_data

    def media_info(self):
        return self.dlna_server.send_dlna_action({}, self, "GetMediaInfo")

    def position_info(self):

        content = self.dlna_server.send_dlna_action({}, self, "GetPositionInfo")
        domtree = xmldom.parseString(content)
        document= domtree.documentElement

        # 用于查找偶尔出现的问题
        try:
            Track = document.getElementsByTagName('Track')[0].firstChild.data
            TrackDuration = document.getElementsByTagName('TrackDuration')[0].firstChild.data
            TrackMetaData = document.getElementsByTagName('TrackMetaData')[0].firstChild.data
            TrackMetaData = TrackMetaData.replace('&lt;', '<').replace('&gt;', '>')
            TrackURI = document.getElementsByTagName('TrackURI')[0].firstChild.data
            RelTime = document.getElementsByTagName('RelTime')[0].firstChild.data
            AbsTime = document.getElementsByTagName('AbsTime')[0].firstChild.data
            RelCount = document.getElementsByTagName('RelCount')[0].firstChild.data
            AbsCount = document.getElementsByTagName('AbsCount')[0].firstChild.data


            def to_seconds(t:str)->int:
                s = 0
                a = t.split(':')
                try:
                    s = int(a[0]) * 60 * 60 + int(a[1]) * 60 + int(a[2])
                except Exception as e:
                    print(e)
                return s

            ret_data = {
                'Track':Track,
                'TrackDuration': TrackDuration,
                'TrackDurationInSeconds': to_seconds(TrackDuration),
                'TrackMetaData': TrackMetaData,
                'TrackURI': TrackURI,
                'RelTime': RelTime,
                'RelTimeInSeconds': to_seconds(RelTime),
                'AbsTime': AbsTime,
                'AbsTimeInSeconds': to_seconds(AbsTime),
                'RelCount': RelCount,
                'AbsCount': AbsCount,
            }

            return ret_data
        except Exception as e:
            print(content)
            raise e


try:
    @unique
    class ThreadStatus(Enum):
        STOPPED = 1
        RUNNING = 2
        PAUSED = 3
except ValueError as e:
    print(e)


class StatusException(Exception):

    def __init__(self, err_msg):
        self.err_msg = {'message': err_msg}
        self.err_msg_detail = err_msg
        Exception.__init__(self, self.err_msg, self.err_msg_detail)


class EasyThread(Thread):

    def __init__(self):
        Thread.__init__(self)
        self.stopEvent = Event()
        self.pauseEvent = Event()
        self.__current_status = ThreadStatus.STOPPED
        self.stophook = None

    def run(self):

        self.__current_status = ThreadStatus.RUNNING
        try:
            while True:

                if self.pauseEvent.is_set():
                    self.__wait_for_notify()

                if self.stopEvent.is_set():
                    self.__stop_thread()
                    break

                self.do_it()

            if self.stophook is not None:
                self.stophook()
        finally:
            self.__current_status = ThreadStatus.STOPPED

    def do_it(self):
        pass

    def __wait_for_notify(self):
        self.__current_status = ThreadStatus.PAUSED
        self.pauseEvent.clear()
        self.pauseEvent.wait()
        self.pauseEvent.clear()
        self.__current_status = ThreadStatus.RUNNING

    def __stop_thread(self):
        self.stopEvent.clear()
        self.__current_status = ThreadStatus.STOPPED

    def send_pause_event(self):
        if self.__current_status == ThreadStatus.RUNNING:
            self.pauseEvent.set()
        else:
            raise StatusException('当前线程处于' + self.__current_status.name + '状态，无法暂停')

    def send_resume_event(self):
        if self.__current_status == ThreadStatus.PAUSED:
            self.pauseEvent.set()
        else:
            raise StatusException('当前线程处于' + self.__current_status.name + '状态，无法恢复')

    def send_stop_event(self, stophook=None):
        if self.__current_status != ThreadStatus.STOPPED:
            self.stophook = stophook
            self.stopEvent.set()


class DlnaDeviceSyncThread(EasyThread):

    def __init__(self, device: Device, last_status=None, interval=1):
        EasyThread.__init__(self)
        self.device = device
        self.last_status = last_status
        self.interval = interval
        self.count = 0

    def call_hook(self, func, type, old_value, new_value):
        if func is None:
            return
        try:
            if old_value is None or old_value != new_value:
                func(type, old_value, new_value)
        except:
            traceback.print_exc()

    def wait_interval(self, start, end):
        duration = end - start
        wait_seconds = self.interval - duration
        if wait_seconds > 0:
            time.sleep(wait_seconds)

    def do_it(self):

        start = time.time()
        transport_info = None
        position_info = None

        try:
            transport_info = self.device.transport_info()
            position_info = self.device.position_info()
        except:
            # 播放器的异常，不处理，可能是尚未准备就绪
            traceback.print_exc()
            if self.count < 5:
                # 第一次播放时远程播放器可能无法获得position_info
                # 停止播放并重启
                self.device.stop()
                self.count = 0
                time.sleep(1)
                self.device.play()
            else:
                self.wait_interval(start, time.time())
            return

        transportstatehook = self.device.transportstatehook
        positionhook = self.device.positionhook

        logging.debug('-------start-------------')

        if self.last_status is None:
            self.call_hook(transportstatehook, 'CurrentTransportState', None, transport_info['CurrentTransportState'])
            self.call_hook(positionhook, 'TrackURI', None, position_info['TrackURI'])
            self.call_hook(positionhook, 'TrackDurationInSeconds', None, position_info['TrackDurationInSeconds'])
            self.call_hook(positionhook, 'RelTimeInSeconds', None, position_info['RelTimeInSeconds'])

        else:
            last_position_info = self.last_status['position_info']
            last_transport_info = self.last_status['transport_info']

            if last_position_info['TrackURI'] is None and position_info['TrackURI'] is not None or position_info['TrackURI'] != last_position_info['TrackURI']:
                self.count = 0

            self.call_hook(transportstatehook, 'CurrentTransportState'
                           , last_transport_info['CurrentTransportState'], transport_info['CurrentTransportState'])
            self.call_hook(positionhook, 'TrackURI'
                           , last_position_info['TrackURI'], position_info['TrackURI'])
            self.call_hook(positionhook, 'TrackDurationInSeconds'
                           , last_position_info['TrackDurationInSeconds'], position_info['TrackDurationInSeconds'])
            self.call_hook(positionhook, 'RelTimeInSeconds'
                           , last_position_info['RelTimeInSeconds'], position_info['RelTimeInSeconds'])
            self.call_hook(positionhook, 'UpdatePositionEnd', None, 0)

        logging.debug('-------end-------------')
        self.last_status = {
            'transport_info': transport_info,
            'position_info': position_info
        }
        self.count += 1
        self.wait_interval(start, time.time())
