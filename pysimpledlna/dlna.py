import os
import pkgutil
import socket
import threading
import urllib.request as urllibreq
from urllib.parse import urljoin
from urllib.parse import urlparse
import xml.dom.minidom as xmldom

import requests
from twisted.internet import reactor
from twisted.web.resource import Resource
from twisted.web.server import Site
from twisted.web.static import File

from threading import Thread, Event
import time
import traceback
import logging
from pysimpledlna.utils import (
    get_element_data_by_tag_name, get_element_by_tag_name,
    to_seconds, wait_interval,
    ThreadStatus)


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

logger = logging.getLogger('pysimpledlna.dlna')
logger.setLevel(logging.INFO)

class SimpleDLNAServer():

    def __init__(self, server_port):
        self.server_port = server_port
        self.root = Resource()
        self.server_ip = socket.gethostbyname(socket.gethostname())
        self.known_devices = {}
        self.is_server_started = False

    def start_server(self):
        reactor.listenTCP(self.server_port, Site(self.root), interface="0.0.0.0")
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
            device_element = get_element_by_tag_name(document, 'device')
            friendlyName = get_element_data_by_tag_name(device_element, 'friendlyName')
            manufacturer = get_element_data_by_tag_name(device_element, 'manufacturer')
            manufacturerURL = get_element_data_by_tag_name(device_element, 'manufacturerURL')
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
        content = res.read().decode("utf-8")
        return content


class Device():

    REMOTE_PLAYER_PLAYING = 'PLAYING'
    REMOTE_PLAYER_PAUSED = 'PAUSED_PLAYBACK'
    REMOTE_PLAYER_STOPPED = 'STOPPED'

    def __init__(self, dlna_server: SimpleDLNAServer
                 , location, host, friendly_name
                 , avtranspor_action_url, rendering_action_url
                 , manufacturer , manufacturer_url, st, device_key
                 , sync_remote_player_interval=1
                 , positionhook=None, transportstatehook=None, exceptionhook=None):

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
        self.exceptionhook = exceptionhook
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

    def set_sync_hook(self, positionhook, transportstatehook, exceptionhook):
        self.positionhook = positionhook
        self.transportstatehook = transportstatehook
        self.exceptionhook = exceptionhook

    def start_sync_remote_player_status(self):
        if self.sync_thread:
            self.sync_thread.start()
            return True
        return False

    def pause_sync_remote_player_status(self):
        if self.sync_thread:
            self.sync_thread.pause()
            return True
        return False

    def resume_sync_remote_player_status(self):
        if self.sync_thread:
            self.sync_thread.resume()
            return True
        return False

    def stop_sync_remote_player_status(self):
        if self.sync_thread:
            self.sync_thread.stop(self.__after_sync_thread_stopped)
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
            return int(get_element_data_by_tag_name(document, 'CurrentVolume', default=-1))
        except Exception as e:
            print(e)
            return -1

    def mute(self):
        try:
            self.dlna_server.send_dlna_action({}, self, "SetMute")
        except Exception as e:
            print(e)

    def unmute(self):
        self.mute()

    def transport_info(self):

        content = self.dlna_server.send_dlna_action({}, self, "GetTransportInfo")
        domtree = xmldom.parseString(content)
        document = domtree.documentElement

        CurrentTransportState = get_element_data_by_tag_name(document, 'CurrentTransportState')
        CurrentTransportStatus = get_element_data_by_tag_name(document, 'CurrentTransportStatus')
        CurrentSpeed = get_element_data_by_tag_name(document, 'CurrentSpeed')

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
            Track = get_element_data_by_tag_name(document, 'Track', 0, '')
            TrackDuration = get_element_data_by_tag_name(document, 'TrackDuration', 0, '')
            TrackMetaData = get_element_data_by_tag_name(document, 'TrackMetaData', 0, '')
            TrackMetaData = TrackMetaData.replace('&lt;', '<').replace('&gt;', '>')
            TrackURI = get_element_data_by_tag_name(document, 'TrackURI', 0, '')
            RelTime = get_element_data_by_tag_name(document, 'RelTime', 0, '00:00:00')
            AbsTime = get_element_data_by_tag_name(document, 'AbsTime', 0, '00:00:00')
            RelCount = get_element_data_by_tag_name(document, 'RelCount', 0, 0)
            AbsCount = get_element_data_by_tag_name(document, 'AbsCount', 0, 0)

            ret_data = {
                'Track': Track,
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
            raise e


class StatusException(Exception):

    def __init__(self, err_msg):
        self.err_msg = {'message': err_msg}
        self.err_msg_detail = err_msg
        Exception.__init__(self, self.err_msg, self.err_msg_detail)


class EasyThread(threading.Thread):

    def __init__(self, *args, **kwargs):
        super(EasyThread, self).__init__(*args, **kwargs)

        self.__flag = threading.Event() # The flag used to pause the thread
        self.__flag.set() # Set to True
        self.__running = threading.Event() # Used to stop the thread identification
        self.__running.set() # Set running to True
        self.__current_status = ThreadStatus.STOPPED

        self.stophook = None


    def run(self):
        try:
            while self.__running.isSet():
                logger.debug('thread waiting...')
                self.__flag.wait() # return immediately when it is True, block until the internal flag is True when it is False
                logger.debug('thread running...')
                self.__current_status = ThreadStatus.RUNNING
                self.do_it()
            logger.debug('thread end')
        finally:
            if self.stophook is not None:
                logger.debug('call thread stop callback')
                self.stophook()
            self.__current_status = ThreadStatus.STOPPED

    def pause(self):
        logger.debug('set thread to pause')
        self.__current_status = ThreadStatus.PAUSED
        self.__flag.clear() # Set to False to block the thread

    def resume(self):
        logger.debug('set thread to resume')
        self.__flag.set() # Set to True, let the thread stop blocking

    def stop(self, stophook=None):
        logger.debug('set thread to stop')
        self.stophook = stophook
        self.__flag.set() # Resume the thread from the suspended state, if it is already suspended
        self.__running.clear() # Set to False

    def do_it(self):
        pass


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
        except Exception as e:
            # 播放器的异常，不处理，可能是尚未准备就绪
            if self.device.exceptionhook is not None:
                self.device.exceptionhook(e)
            #traceback.print_exc()
            if self.count < 5:
                # 第一次播放时远程播放器可能无法获得position_info
                # 停止播放并重启
                try:
                    self.device.stop()
                    self.count = 0
                    time.sleep(1)
                    self.device.play()
                except Exception as e:
                    self.device.exceptionhook(e)
            else:
                self.wait_interval(start, time.time())
            return

        transportstatehook = self.device.transportstatehook
        positionhook = self.device.positionhook

        logger.debug('-------start-------------')

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

        logger.debug('-------end-------------')
        self.last_status = {
            'transport_info': transport_info,
            'position_info': position_info
        }
        self.count += 1
        wait_interval(self.interval, start, time.time())
