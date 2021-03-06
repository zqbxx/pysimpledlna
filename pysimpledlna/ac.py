import logging
import os
import signal
import time

from pysimpledlna import Device
from pysimpledlna.ui.terminal import Player, PlayerStatus
from pysimpledlna.utils import wait_interval
from prompt_toolkit_ext.event import Event

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

    def stop_device(self):
        self.device.stop_sync_remote_player_status()
        self.device.stop()
        self.end = True

    def excpetionhook(self, e: Exception):
        self.player.exception = e
        self.player.draw()

    def hook(self, type, old_value, new_value):

        logging.debug('type: ' + type + ' old:' + str(old_value) + ' new:' + str(new_value))
        self.player.exception = None
        if type == 'CurrentTransportState':
            logging.debug('try play next video:')
            logging.debug('current_video_position:' + str(self.current_video_position))
            logging.debug('current_video_duration:' + str(self.current_video_duration))

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
                        logging.debug('play next video')
                        self.player.new_player()
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
        self.current_idx += 1
        self.play()
        self.events['play_next'].fire(self.current_idx)

    def play_last(self):
        self.current_idx -= 1
        self.play()
        self.events['play_last'].fire(self.current_idx)

    def play(self):

        if self.current_idx >= len(self.file_list):
            self.current_idx = len(self.file_list) - 1
            return

        if self.current_idx < 0:
            self.current_idx = 0
            return

        self.player.new_player()

        file_path = self.file_list[self.current_idx]
        self.player.video_file = file_path
        self.player.duration = 0
        self.player.cur_pos = 0
        server_file_path = self.device.add_file(file_path)

        positionhook, transportstatehook, exceptionhook = self._remove_hooks()

        try:
            self.device.stop()
            self.device.set_AV_transport_URI(server_file_path)
            self.device.play()
            self.ensure_player_is_playing()
            self.player.player_status = PlayerStatus.PLAY
        finally:
            self._restore_hooks(exceptionhook, positionhook, transportstatehook)
            self.events['play'].fire(self.current_idx)

    def ensure_player_is_playing(self):

        positionhook, transportstatehook, exceptionhook = self._remove_hooks()

        try:
            for i in range(60):
                start = time.time()
                position_info = self.device.position_info()
                rt_in_sec = position_info['RelTimeInSeconds']
                if rt_in_sec >= 1:
                    return
                '''
                transport_info = self.device.transport_info()
                player_status = transport_info['CurrentTransportState']
                if player_status == 'PLAYING':
                    return
                '''
                dur = time.time() - start
                time.sleep((1 - dur))
        finally:
            self._restore_hooks(exceptionhook, positionhook, transportstatehook)

    def _remove_hooks(self):
        transportstatehook = self.device.transportstatehook
        positionhook = self.device.positionhook
        exceptionhook = self.device.exceptionhook
        self.device.transportstatehook = None
        self.device.positionhook = None
        self.device.exceptionhook = None
        return positionhook, transportstatehook, exceptionhook

    def _restore_hooks(self, exceptionhook, positionhook, transportstatehook):
        self.device.transportstatehook = transportstatehook
        self.device.positionhook = positionhook
        self.device.exceptionhook = exceptionhook
