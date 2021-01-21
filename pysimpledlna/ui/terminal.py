from sys import stdout
import os
from enum import Enum

from prompt_toolkit.key_binding import KeyBindings


class PlayerStatus(Enum):
    # Courier New
    STOP = '■'
    PLAY = '►'
    PAUSE = '═'


class Player:

    def __init__(self):
        self._duration = 0
        self._video_file = ''
        self._video_file_path = ''
        self._video_file_name = ''
        self._player_status = PlayerStatus.STOP
        self._cur_pos = 0

    def draw(self):
        text = '\r'
        text += self.format_time(self.cur_pos) + '/' + self.format_time(self.duration) + ' | '
        text += self.player_status.value
        text += ' current: ' + self._video_file_name
        stdout.write(text)

    def format_time(self, seconds) -> str:
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return "%02d:%02d:%02d" % (h, m, s)

    @property
    def duration(self):
        return self._duration

    @duration.setter
    def duration(self, duration):
        self._duration = duration

    @property
    def video_file(self):
        return self._video_file

    @video_file.setter
    def video_file(self, video_file):
        self._video_file = video_file
        self._video_file_path, self._video_file_name = os.path.split(self.video_file)

    @property
    def cur_pos(self):
        return self._cur_pos

    @cur_pos.setter
    def cur_pos(self, cur_pos):
        self._cur_pos = cur_pos

    @property
    def player_status(self) -> PlayerStatus:
        return self._player_status

    @player_status.setter
    def player_status(self, player_status: PlayerStatus):
        self._player_status = player_status


if __name__ == '__main__':
    import time
    play_ui = Player()
    play_ui.duration = 1000
    play_ui.video_file = 'D:/test/test.mkv'
    for i in range(1000):
        time.sleep(1)
        play_ui.cur_pos = i +1
        play_ui.draw()
