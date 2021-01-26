import logging
import os
import signal
import time

from pysimpledlna import Device
from pysimpledlna.ui.terminal import Player, PlayerStatus


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

        self.player = Player()

    def start_play(self):
        self.play_next()

    def stop_device(self):
        self.device.stop_sync_remote_player_status()
        self.device.stop()

    def hook(self, type, old_value, new_value):

        logging.debug('type: ' + type + ' old:' + str(old_value) + ' new:' + str(new_value))

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
                if self.current_video_position >= self.current_video_duration - 2 * self.device.sync_remote_player_interval:
                    # 只对播放文件末尾时间进行处理

                    left_time = self.current_video_duration - self.current_video_position
                    if left_time > 0:
                        logging.debug('wait ' + str(left_time) + ' s')
                        time.sleep(left_time)

                    if self.current_idx < len(self.file_list):
                        logging.debug('play next video')
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
            self.current_video_position = new_value
            self.player.cur_pos = new_value
        elif type == 'UpdatePositionEnd':
            self.player.draw()

    def play_next(self):
        file_path = self.file_list[self.current_idx]
        self.player.video_file = file_path
        self.player.duration = 0
        self.player.cur_pos = 0
        server_file_path = self.device.add_file(file_path)
        self.device.set_AV_transport_URI(server_file_path)
        self.device.play()
        self.ensure_player_is_playing()
        self.player.player_status = PlayerStatus.PLAY
        self.current_idx += 1

    def ensure_player_is_playing(self):

        transportstatehook = self.device.transportstatehook
        positionhook = self.device.positionhook
        self.device.transportstatehook = None
        self.device.positionhook = None

        try:
            for i in range(60):
                start = time.time()
                transport_info = self.device.transport_info()
                player_status = transport_info['CurrentTransportState']
                if player_status == 'PLAYING':
                    return
                dur = time.time() - start
                time.sleep((1 - dur))
        finally:
            self.device.transportstatehook = transportstatehook
            self.device.positionhook = positionhook
