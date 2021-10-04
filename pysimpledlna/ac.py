import logging
import os
import signal
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from pysimpledlna import Device
from pysimpledlna.entity import PlayListWrapper
from pysimpledlna.ui.terminal import Player, PlayerStatus
from pysimpledlna.utils import wait_interval, format_time
from prompt_toolkit_ext.event import Event

import traceback


def get_logger():
    return logging.getLogger('pysimpledlna.ac')

class ActionController:

    '''
    自己实现连续播放多个文件的功能，部分DLNA设备没有实现用于连续播放的接口
    '''
    def __init__(self, play_list: PlayListWrapper, device: Device, player=Player()):
        self.logger = get_logger()
        self.play_list: PlayListWrapper = play_list
        self.player = player
        self.init_ac(device)
        self.events = {
            'play_next': Event(),
            'play_last': Event(),
            'play': Event(),
            'stop': Event(),
            'resume': Event(),
            'video_position': Event(),
        }

    def init_ac(self, device:Device):
        self.current_idx = 0
        self.device = device

        self.current_video_position = 0
        self.current_video_duration = 0
        self.last_video_duration = -1
        self.last_video_position = -1
        self.last_idx = 0

        self.local_file_path = ''  #: 当前正在投屏的文件本地地址
        self.server_file_path = ''  #: 当前正在投屏的文件本地地址对应的web地址
        self.dlna_render_file_path = ''  #: dlna显示器正在播放的文件地址
        self.is_occupied = False  #: 投屏是否被其他程序占用
        self.end = False
        self.enable_hook = True

    def stop_device(self):
        self.device.stop_sync_remote_player_status()
        self.device.stop()
        self.end = True

    def excpetionhook(self, e: Exception):
        self.player.exception = e
        self.player.draw()

    def hook(self, type, old_value, new_value):

        logger = self.logger

        if not self.enable_hook:
            return
        logger.debug('type: ' + type + ' old:' + str(old_value) + ' new:' + str(new_value))
        self.player.exception = None
        if type == 'CurrentTransportState':
            if self.is_occupied:
                return
            logger.debug('try play next video:')
            logger.debug('current_video_position:' + str(self.current_video_position))
            logger.debug('current_video_duration:' + str(self.current_video_duration))

            if new_value == 'STOPPED':
                if self.player.player_status != PlayerStatus.STOP:
                    self.player.player_status = PlayerStatus.STOP
                    self.events['stop'].fire(self.current_idx, self.current_video_position)
                self.player.player_status = PlayerStatus.STOP
            elif new_value == 'PLAYING':
                self.player.player_status = PlayerStatus.PLAY
            elif new_value == 'PAUSED_PLAYBACK':
                self.player.player_status = PlayerStatus.PAUSE

            if old_value in ['PLAYING', 'PAUSED_PLAYBACK'] and new_value == 'STOPPED':
                if self.current_video_position >= self.get_max_video_position():
                    # 只对播放文件末尾时间进行处理
                    wait_interval(self.current_video_duration, 0, self.current_video_position)

                    if self.current_idx < len(self.play_list.playlist.media_list):
                        logger.debug('play next video')
                        self.play_next()
                    else:
                        self.stop_device()
                        os.kill(signal.CTRL_C_EVENT, 0)

                #else:
                #    self.stop_device()
                #    os.kill(signal.CTRL_C_EVENT, 0)
        elif type == 'TrackURI':
            self.dlna_render_file_path = new_value
            if self._test_occupied():
                self.is_occupied = True
                # 其他设备进行投屏，本机设置为停止
                if self.player.player_status != PlayerStatus.STOP:
                    self.player.player_status = PlayerStatus.STOP
                    self.current_idx = self.last_idx
                    # 使用上一个视频的位置和时长，避免nuitka编译后导致的问题
                    self.current_video_position = self.last_video_position
                    self.current_video_duration = self.last_video_duration
                    self.player.cur_pos = self.current_video_position
                    self.events['stop'].fire(self.current_idx, self.current_video_position)
                    self.last_video_duration = -1
                    self.last_video_position = -1
            else:
                self.is_occupied = False

        elif type == 'TrackDurationInSeconds':
            if self.is_occupied:
                return
            if self.player.player_status == PlayerStatus.STOP:
                return
            # 记录上一个视频的长度
            # nuitka编译后TrackURI, TrackDurationInSeconds, RelTimeInSeconds调用顺序改变导致
            # 其他程序占用dlna播放器后先更新视频长度和位置信息
            # 造成播放列表保存播放为位置错误
            if self.last_video_duration != self.current_video_duration:
                self.last_video_duration = self.current_video_duration
            self.current_video_duration = new_value
            self.player.duration = new_value
        elif type == 'RelTimeInSeconds':
            if self.is_occupied:
                return
            if self.player.player_status == PlayerStatus.STOP or self.player.player_status == PlayerStatus.PAUSE:
                return
            if self.current_video_position != new_value:
                self.events['video_position'].fire(self.current_video_position, new_value)
            # 记录上一次轮询位置，仅记录大于10秒的位置
            # nuitka编译后TrackURI, TrackDurationInSeconds, RelTimeInSeconds调用顺序改变导致
            # 其他程序占用dlna播放器后先更新视频长度和位置信息
            # 造成播放列表保存播放为位置错误
            if self.current_video_position > 10:
                self.last_video_position = self.current_video_position
                self.last_idx = self.current_idx
            self.current_video_position = new_value
            self.player.cur_pos = new_value
        elif type == 'UpdatePositionEnd':
            self.player.draw()

    def _test_occupied(self):
        url = self.dlna_render_file_path
        parsed_url = urlparse(url)
        params = parse_qs(parsed_url.query)
        if 'serverid' in params:
            server_id = params['serverid']
            return server_id == self.device.dlna_server.server_id
        return True

    def get_max_video_position(self):
        return self.current_video_duration - 2 * self.device.sync_remote_player_interval

    def play_next(self):
        self.logger.debug(f'ac.play_next, caller: {traceback.extract_stack()[-2][2]}')
        self.current_idx += 1
        self.play()
        self.events['play_next'].fire(self.current_idx)

    def play_last(self):
        self.current_idx -= 1
        self.play()
        self.events['play_last'].fire(self.current_idx)

    def prepare_play(self):

        if not self.validate_current_index():
            return

        self.player.new_player()

        self.local_file_path = self.play_list.playlist.media_list[self.current_idx]
        self.player.video_file = self.local_file_path
        self.player.duration = 0
        self.player.cur_pos = 0
        self.current_video_position = 0
        self.current_video_duration = 0
        self.server_file_path = self.device.add_file(self.local_file_path)

        self.device.stop()
        self.device.set_AV_transport_URI(self.server_file_path)

    def play(self):
        self.logger.debug(f'ac.play, caller: {traceback.extract_stack()[-2][2]}')
        self.enable_hook = False

        if not self.validate_current_index():
            return

        try:
            self.prepare_play()
            self.device.play()
            self.player.player_status = PlayerStatus.PLAY
            self.ensure_player_is_playing()
            # 强制下一次轮询时强制更新
            if self.device.sync_thread is not None:
                self.device.sync_thread.last_status = None
        finally:
            self.events['play'].fire(self.current_idx)
            self.enable_hook = True

    def resume(self, stop=False, seek_to: int = 0, ):
        self.enable_hook = False
        try:
            time_str = format_time(self.current_video_position)
            if seek_to > 0:
                time_str = format_time(seek_to)
                self.current_video_position = seek_to

            if stop:
                self.device.stop()
                self.device.set_AV_transport_URI(self.server_file_path)

            self.device.play()
            self.player.player_status = PlayerStatus.PLAY
            self.ensure_player_is_playing()
            if seek_to > 0:
                self.device.seek(time_str)
            # 强制下一次轮询时强制更新
            if self.device.sync_thread is not None:
                self.device.sync_thread.last_status = None
        finally:
            self.events['resume'].fire(self.current_idx)
            self.enable_hook = True

    def pause(self):
        self.device.pause()
        self.player.player_status = PlayerStatus.PAUSE

    def stop(self):
        if self.player.player_status != PlayerStatus.STOP:
            self.player.player_status = PlayerStatus.STOP
            self.events['stop'].fire(self.current_idx, self.current_video_position)
            self.device.stop()

    def validate_current_index(self):
        logger = self.logger
        logger.debug(f'current_index: {self.current_idx}')
        if self.current_idx >= len(self.play_list.playlist.media_list):
            self.current_idx = len(self.play_list.playlist.media_list) - 1
            return False

        if self.current_idx < 0:
            self.current_idx = 0
            return False

        while self.current_idx < len(self.play_list.playlist.media_list):
            file_path = Path(self.play_list.playlist.media_list[self.current_idx])
            if file_path.exists() and file_path.is_file():
                return True
            logger.debug(f'current index: {self.current_idx}, file {str(file_path.absolute())} does not exists')
            self.current_idx += 1

        return False

    def ensure_player_is_playing(self):
        # 视频通过网络加载需要时间，必须确保播放器已经缓存完成并开始播放
        # 否则，seek会失败
        rt_in_sec = -1
        is_playing = False
        time_changed = False
        is_same_file = False
        for i in range(20):
            start = time.time()
            position_info = self.device.position_info()
            is_same_file = self.server_file_path == position_info['TrackURI']
            if rt_in_sec == -1:
                rt_in_sec = position_info['RelTimeInSeconds']
            elif position_info['RelTimeInSeconds'] != rt_in_sec:
                time_changed = True

            transport_info = self.device.transport_info()
            current_status = transport_info['CurrentTransportState']
            if current_status == 'PAUSED_PLAYBACK' or 'PLAYING':
                is_playing = True

            if is_playing and time_changed and is_same_file:
                return

            self.logger.debug(f'waiting for device: {str(i)}')
            dur = time.time() - start
            if dur >= 1:
                continue
            time.sleep((1 - dur))
