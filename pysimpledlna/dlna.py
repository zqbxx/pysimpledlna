import os
import pkgutil
import socket
import threading
import urllib.request as urllibreq
from enum import Enum
from http.server import HTTPServer
from pathlib import Path
from socketserver import ThreadingTCPServer
from struct import pack
from typing import TypeVar, Callable, List, Dict
from urllib.parse import urljoin
from urllib.parse import urlparse
import xml.dom.minidom as xmldom

import requests
import time
import traceback
import logging

from bottle import ServerAdapter, Bottle, static_file, request, abort

from pysimpledlna.utils import (
    get_element_data_by_tag_name, get_element_by_tag_name,
    to_seconds, wait_interval, random_str)

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

_Resource = TypeVar("_Resource", bound="Resource")

logger = logging.getLogger('pysimpledlna.dlna')
logger.setLevel(logging.INFO)


class SimpleDLNAServer():

    def __init__(self,
                 server_port: int = 8000,
                 is_enable_ssl: bool = False,
                 cert_file: str = './server.crt',
                 key_file: str = './server.key'):
        self.server_port = server_port
        self.root = DLNARootRootResource(self)
        self.app = Bottle()
        self.server = None
        self.server_ip = socket.gethostbyname(socket.gethostname())
        self.known_devices:Dict[str, Device] = {}
        self.is_server_started = False
        self.is_ssl_enabled = is_enable_ssl
        self.cert_file = cert_file
        self.key_file = key_file
        self.device_count = 0

    def start_server(self):
        init_event = threading.Event()
        threading.Thread(target=self._run_server, args=(init_event, )).start()
        init_event.wait()
        self.is_server_started = True

    def _run_server(self, init_event: threading.Event):

        self.server = SSLCherootAdapter(
            host=self.server_ip,
            port=self.server_port,
            cert_file=self.cert_file,
            key_file=self.key_file,
            enable_ssl=self.is_ssl_enabled,
            init_event=init_event,
            dlna_server=self)

        #self.app.route(self.root.get_route_str(), self.root.get_method(), self.root.get_render())
        self.app.route(**self.root.get_route_params())
        self.app.run(quiet=True, server=self.server)

    def stop_server(self):
        if self.is_server_started:
            self.app.close()
            self.server.close()
            self.is_server_started = False

    def get_device_root(self, device) -> _Resource:
        device_root = self.root.get(device.device_key, None)
        if device_root is None:
            device_root = Resource()
            self.root[device.device_key] = device_root
        return device_root

    def get_server_file_path(self, device, key: str):
        if self.is_ssl_enabled:
            file_url = "https://{0}:{1}/device/{2}/{3}".format(self.server_ip, self.server_port, device.device_key, key)
        else:
            file_url = "http://{0}:{1}/device/{2}/{3}".format(self.server_ip, self.server_port, device.device_key, key)
        return file_url

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
            device_key = random_str(8) + str(self.device_count)
            self.device_count += 1

            avtranspor_control_url = None
            rendering_control_url = None
            serviceType_elements = device_element.getElementsByTagName('serviceType')
            for serviceType_element in serviceType_elements:
                urn_data = serviceType_element.firstChild.data
                if 'urn:schemas-upnp-org:service:AVTranspor' in urn_data:
                    avtranspor_control_url = serviceType_element.parentNode.getElementsByTagName('controlURL')[0].firstChild.data
                elif 'urn:schemas-upnp-org:service:RenderingControl' in urn_data:
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

    def get_devices(self, timeout=10*2, disable_notify=False):
        if disable_notify:
            yield from self._from_recv(timeout)
        else:
            timeout = timeout / 2
            yield from self._from_recv(timeout)
            yield from self._from_notify(timeout)

    def _from_recv(self, timeout):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 4)
        s.bind((socket.gethostbyname(socket.gethostname()), SSDP_BROADCAST_PORT + 10))
        s.sendto(SSDP_BROADCAST_MSG.encode(), (SSDP_BROADCAST_ADDR, SSDP_BROADCAST_PORT))
        s.settimeout(timeout)
        while 1:

            try:
                data, addr = s.recvfrom(1024)
            except socket.timeout:
                try:
                    s.close()
                finally:
                    pass
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
                device = self.register_device(self.parse_xml(device_dict["location"]))
                if device is not None:
                    yield device

    def _from_notify(self, timeout):
        receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        receiver.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 4)
        receiver.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        receiver.bind(('', SSDP_BROADCAST_PORT))
        mreq = pack('4sl', socket.inet_aton(SSDP_BROADCAST_ADDR), socket.INADDR_ANY)
        receiver.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        receiver.settimeout(timeout)
        sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

        start = time.time()
        while 1:

            try:
                data, addr = receiver.recvfrom(1024)
                current = time.time()
                if current - start > timeout:
                    break
            except socket.timeout:
                try:
                    receiver.close()
                finally:
                    pass
                break

            def serialize(x):
                try:
                    k, v = x.split(":", maxsplit=1)
                except ValueError:
                    pass
                else:
                    return k.lower(), v.lstrip()

            (host, port) = addr
            header = data.decode()
            lines = header.split('\r\n')
            cmd = lines[0].split(' ')
            lines = [x.replace(': ', ':', 1) for x in lines[1:]]
            lines = [x for x in lines if len(x) > 0]

            headers = [x.split(':', 1) for x in lines]
            headers = dict([(x[0].lower(), x[1]) for x in headers])
            device_dict = None
            if cmd[0] == 'NOTIFY' and cmd[1] == '*':
                device_dict = self._notify_received(headers)

            if device_dict is None or 'location' not in device_dict or 'st' not in device_dict:
                continue

            if "AVTransport" in device_dict["st"]:
                device = self.register_device(self.parse_xml(device_dict["location"]))
                if device is not None:
                    yield device

    def _notify_received(self, headers:Dict[str, str])->Dict[str, str]:
        if headers['nts'] == 'ssdp:alive':
            if 'cache-control' not in headers:
                headers['cache-control'] = 'max-age=1800'

            default_fields_name = ["usn", "nt", "location", "server",
                                       "cache-control", "host", "nts"]
            default_header = {}
            for field in default_fields_name:
                default_header[field] = headers.pop(field, "")
            if 'nt' in default_header:
                default_header['st'] = default_header['nt']
            else:
                return None
            return default_header
        elif headers['nts'] == 'ssdp:byebye':
            #TODO 处理下线
            return None
        else:
            return None

    def register_device(self, device):
        if device is not None:
            for kd in self.known_devices.values():
                if kd.location == device.location:
                    return None
            self.known_devices[device.device_key] = device
        return device

    def find_device(self, location_url):
        device = self.parse_xml(location_url)
        self.register_device(device)
        return device

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
        p_file_path = Path(file_path)
        # TODO 随机文件名作为配置项
        #file_key = p_file_path.name
        file_key = random_str() + p_file_path.suffix
        self.video_files[file_key] = p_file_path
        file_url = self.dlna_server.get_server_file_path(self, file_key)
        return file_url
    '''
    def remove_file(self, file_path):
        file_name, file_url, file_path = self.dlna_server.set_files(self, file_path)
        if self.video_files.children.get(file_name.encode("utf-8")) is not None:
            del self.video_files.children[file_name.encode("utf-8")]
    '''
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


class Resource(dict):

    def get_route_str(self)->str:
        ...

    def get_method(self)->str:
        ...

    def get_render(self) -> Callable:
        ...

    def get_route_params(self):
        params = dict()
        params['path'] = self.get_route_str()
        params['method'] = self.get_method()
        params['callback'] = self.get_render()
        return params


class DefaultResource(Resource):

    def __init__(self, route_str: str, method: List[str]) -> None:
        super().__init__()
        self.route_str = route_str
        self.method = method
        self.render = None

    def get_route_str(self) -> str:
        return self.route_str

    def get_method(self) -> List[str]:
        return self.method

    def get_render(self) -> Callable:
        return self.render


class DLNARootRootResource(DefaultResource):

    def __init__(self, server: SimpleDLNAServer) -> None:
        super().__init__('/device/<device_key>/<filename>', ['POST', 'GET'])
        self.server = server
        self.render = self.render_request

    def render_request(self, device_key, filename):
        ip = request.environ.get('REMOTE_ADDR')
        device: Device = self.server.known_devices[device_key]
        if device.host == ip:
            file_path: Path = self[device_key][filename]
            return static_file(file_path.name, root=str(file_path.parent))
        return abort(404, "No such file.")


class SSLCherootAdapter(ServerAdapter):

    def __init__(self, host='127.0.0.1', port=8080, **options):
        super().__init__(host, port, **options)
        self.server = None

    def run(self, handler):
        from cheroot import wsgi
        from cheroot.ssl.builtin import BuiltinSSLAdapter
        import ssl

        self.server = wsgi.Server((self.host, self.port), handler)

        cert_file = self.options.get('cert_file', None)
        key_file = self.options.get('key_file', None)
        enable_ssl = self.options.get('enable_ssl', False)

        p_cert_file = Path(cert_file)
        p_key_file = Path(key_file)

        if p_cert_file.exists() and p_key_file.exists() and enable_ssl:
            self.server.ssl_adapter = BuiltinSSLAdapter(str(p_cert_file.absolute()), str(p_key_file.absolute()))

            # By default, the server will allow negotiations with extremely old protocols
            # that are susceptible to attacks, so we only allow TLSv1.2
            self.server.ssl_adapter.context.options |= ssl.OP_NO_TLSv1
            self.server.ssl_adapter.context.options |= ssl.OP_NO_TLSv1_1
        else:
            dlna_server: SimpleDLNAServer = self.options.get('dlna_server')
            dlna_server.is_ssl_enabled = False

        self.server.prepare()

        # 必须在self.server被赋值后触发初始化完成时间
        # 这里在开启循环前触发，保证服务器已经启动
        init_event: threading.Event = self.options.get('init_event', None)
        if init_event is not None:
            init_event.set()

        self.server.serve()

    def close(self):
        self.server.stop()


class SSLWSGIRefServer(ServerAdapter):

    def __init__(self, host='127.0.0.1', port=8080, **options):
        super().__init__(host, port, **options)
        self.srv = None

    def run(self, app):

        from wsgiref.simple_server import make_server
        from wsgiref.simple_server import WSGIRequestHandler
        import socket

        class FixedHandler(WSGIRequestHandler):

            def address_string(self):  # Prevent reverse DNS lookups please.
                return self.client_address[0]

            def log_request(*args, **kw):
                if not self.quiet:
                    return WSGIRequestHandler.log_request(*args, **kw)

        FixedHandler.protocol_version = 'HTTP/1.1'
        handler_cls = self.options.get('handler_class', FixedHandler)
        server_cls = self.options.get('server_class', ThreadingWSGIServer)

        if ':' in self.host:  # Fix wsgiref for IPv6 addresses.
            if getattr(server_cls, 'address_family') == socket.AF_INET:

                class server_cls(server_cls):
                    address_family = socket.AF_INET6

        self.srv = make_server(self.host, self.port, app, server_cls, handler_cls)
        self.port = self.srv.server_port  # update port actual port (0 means random)

        cert_file = self.options.get('cert_file', None)
        key_file = self.options.get('key_file', None)
        enable_ssl = self.options.get('enable_ssl', False)

        if cert_file is not None and key_file is not None and enable_ssl:
            p_cert_file = Path(cert_file)
            p_key_file = Path(key_file)
            if p_cert_file.exists() and p_key_file.exists():
                import ssl
                print('ssl')
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.load_cert_chain(p_cert_file.absolute(), p_key_file.absolute())
                self.srv.socket = context.wrap_socket(self.srv.socket, server_side=True)
            else:
                dlna_server: SimpleDLNAServer = self.options.get('dlna_server')
                dlna_server.is_ssl_enabled = False

        init_event: threading.Event = self.options.get('init_event', None)
        if init_event is not None:
            init_event.set()

        self.srv.serve_forever()

    def close(self):
        if self.srv is not None:
            self.srv.server_close()
            self.srv.shutdown()


class ThreadingWSGIServer(ThreadingTCPServer):

    application = None

    def server_bind(self):
        """Override server_bind to store the server name."""
        HTTPServer.server_bind(self)
        self.setup_environ()

    def setup_environ(self):
        # Set up base environment
        env = self.base_environ = {}
        env['SERVER_NAME'] = self.server_name
        env['GATEWAY_INTERFACE'] = 'CGI/1.1'
        env['SERVER_PORT'] = str(self.server_port)
        env['REMOTE_HOST']=''
        env['CONTENT_LENGTH']=''
        env['SCRIPT_NAME'] = ''

    def get_app(self):
        return self.application

    def set_app(self,application):
        self.application = application


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
            self.call_hook(positionhook, 'TrackURI', None, position_info['TrackURI'])
            self.call_hook(transportstatehook, 'CurrentTransportState', None, transport_info['CurrentTransportState'])
            self.call_hook(positionhook, 'TrackDurationInSeconds', None, position_info['TrackDurationInSeconds'])
            self.call_hook(positionhook, 'RelTimeInSeconds', None, position_info['RelTimeInSeconds'])
        else:
            last_position_info = self.last_status['position_info']
            last_transport_info = self.last_status['transport_info']

            if last_position_info['TrackURI'] is None and position_info['TrackURI'] is not None or position_info['TrackURI'] != last_position_info['TrackURI']:
                self.count = 0

            self.call_hook(positionhook, 'TrackURI'
                           , last_position_info['TrackURI'], position_info['TrackURI'])
            self.call_hook(transportstatehook, 'CurrentTransportState'
                           , last_transport_info['CurrentTransportState'], transport_info['CurrentTransportState'])
            self.call_hook(positionhook, 'TrackDurationInSeconds'
                           , last_position_info['TrackDurationInSeconds'], position_info['TrackDurationInSeconds'])
            self.call_hook(positionhook, 'RelTimeInSeconds'
                           , last_position_info['RelTimeInSeconds'], position_info['RelTimeInSeconds'])
            self.call_hook(positionhook, 'UpdatePositionEnd', None, 0)

        logger.debug('-------end-------------')

        if self.last_status is None:
            self.last_status = {}
        self.last_status['transport_info'] = transport_info
        self.last_status['position_info'] = position_info

        self.count += 1
        wait_interval(self.interval, start, time.time())


class ThreadStatus(Enum):
    STOPPED = 1
    RUNNING = 2
    PAUSED = 3