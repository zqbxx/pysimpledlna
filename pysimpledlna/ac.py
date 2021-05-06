import logging
import os
import signal
import time
from pathlib import Path

from pysimpledlna import Device
from pysimpledlna.ui.terminal import Player, PlayerStatus
from pysimpledlna.utils import wait_interval
from prompt_toolkit_ext.event import Event

import traceback


logger = logging.getLogger('pysimpledlna.ac')
logger.setLevel(logging.INFO)


class ActionController:

    '''
    自己实现连续播放多个文件的功能，部分DLNA设备没有实现用于连续播放的接口
    '''
    def __init__(self, file_list, device: Device, player=Player()):
        self.current_idx = 0
        self.file_list = file_list
        self.device = device

        self.current_video_position = 0
        self.current_video_duration = 0

        self.player = player

        self.end = False

        self.events = {
            'play_next': Event(),
            'play_last': Event(),
            'play': Event(),
            'video_position': Event(),
        }

        self.enable_hook = True

    def stop_device(self):
        self.device.stop_sync_remote_player_status()
        self.device.stop()
        self.end = True

    def excpetionhook(self, e: Exception):
        self.player.exception = e
        self.player.draw()

    def hook(self, type, old_value, new_value):
        if not self.enable_hook:
            return
        logger.debug('type: ' + type + ' old:' + str(old_value) + ' new:' + str(new_value))
        self.player.exception = None
        if type == 'CurrentTransportState':
            logger.debug('try play next video:')
            logger.debug('current_video_position:' + str(self.current_video_position))
            logger.debug('current_video_duration:' + str(self.current_video_duration))

            if new_value == 'STOPPED':
                self.player.player_status = PlayerStatus.STOP
            elif new_value == 'PLAYING':
                self.player.player_status = PlayerStatus.PLAY
            elif new_value == 'PAUSED_PLAYBACK':
                self.player.player_status = PlayerStatus.PAUSE

            if old_value in ['PLAYING', 'PAUSED_PLAYBACK'] and new_value == 'STOPPED':
                if self.current_video_position >= self.get_max_video_position():
                    # 只对播放文件末尾时间进行处理
                    wait_interval(self.current_video_duration, 0, self.current_video_position)

                    if self.current_idx < len(self.file_list):
                        logger.debug('play next video')
                        self.play_next()
                    else:
                        self.stop_device()
                        os.kill(signal.CTRL_C_EVENT, 0)

                else:
                    self.stop_device()
                    os.kill(signal.CTRL_C_EVENT, 0)

        elif type == 'TrackDurationInSeconds':
            self.current_video_duration = new_value
            self.player.duration = new_value
        elif type == 'RelTimeInSeconds':
            if self.current_video_position != new_value:
                self.events['video_position'].fire(self.current_video_position, new_value)
            self.current_video_position = new_value
            self.player.cur_pos = new_value
        elif type == 'UpdatePositionEnd':
            self.player.draw()

    def get_max_video_position(self):
        return self.current_video_duration - 2 * self.device.sync_remote_player_interval

    def play_next(self):
        logger.debug(f'ac.play_next, caller: {traceback.extract_stack()[-2][2]}')
        self.current_idx += 1
        self.play()
        self.events['play_next'].fire(self.current_idx)

    def play_last(self):
        self.current_idx -= 1
        self.play()
        self.events['play_last'].fire(self.current_idx)

    def play(self):
        logger.debug(f'ac.play, caller: {traceback.extract_stack()[-2][2]}')
        self.enable_hook = False

        if not self.validate_current_index():
            return

        self.player.new_player()

        file_path = self.file_list[self.current_idx]
        self.player.video_file = file_path
        self.player.duration = 0
        self.player.cur_pos = 0
        self.current_video_position = 0
        self.current_video_duration = 0
        server_file_path = self.device.add_file(file_path)

        try:
            self.device.stop()
            self.device.set_AV_transport_URI(server_file_path)
            self.device.play()
            self.player.player_status = PlayerStatus.PLAY
            self.ensure_player_is_playing()
            # 强制下一次轮询时强制更新
            if self.device.sync_thread is not None:
                self.device.sync_thread.last_status = None
        finally:
            self.events['play'].fire(self.current_idx)
            self.enable_hook = True

    def validate_current_index(self):
        logger.debug(f'current_index: {self.current_idx}')
        if self.current_idx >= len(self.file_list):
            self.current_idx = len(self.file_list) - 1
            return False

        if self.current_idx < 0:
            self.current_idx = 0
            return False

        while self.current_idx < len(self.file_list):
            file_path = Path(self.file_list[self.current_idx])
            if file_path.exists() and file_path.is_file():
                return True
            logger.debug(f'current index: {self.current_idx}, file {str(file_path.absolute())} does not exists')
            self.current_idx += 1

        return False

    def ensure_player_is_playing(self):
        for i in range(60):
            start = time.time()
            position_info = self.device.position_info()
            rt_in_sec = position_info['RelTimeInSeconds']
            if rt_in_sec >= 1:
                return
            logger.debug(f'waiting for device: {str(i)}')
            dur = time.time() - start
            if dur >= 1:
                continue
            time.sleep((1 - dur))
