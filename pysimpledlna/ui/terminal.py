from sys import stdout
import os
from enum import Enum
import shutil
from wcwidth import wcwidth


class PlayerStatus(Enum):
    # Courier New
    STOP = 'Stop'
    PLAY = 'Play'
    PAUSE = 'Pause'


class Player:

    def __init__(self):
        self._duration = 0
        self._video_file = ''
        self._video_file_path = ''
        self._video_file_name = ''
        self._player_status = PlayerStatus.STOP
        self._cur_pos = 0

        self.pause = False

    def draw(self):

        columns, lines = shutil.get_terminal_size((80, 20))

        text = '\r'
        text += self.format_time(self.cur_pos) + '/' + self.format_time(self.duration) + ' | '
        text += self.player_status.value
        text += ' current: '
        text_columns = sum(wcwidth(c) for c in text)
        remain_columns = columns - text_columns - 5
        if remain_columns > 0:
            name_columns = sum(wcwidth(c) for c in self._video_file_name)
            if name_columns <= remain_columns:
                text += self._video_file_name
                text += ' ' * (remain_columns - name_columns)
            else:
                # 剩余空间太小就不显示
                if remain_columns > 5:
                    # 截取头部和尾部显示
                    part_len = int((remain_columns-2)/2)
                    text += self._video_file_name[:part_len-1] + '..' + self._video_file_name[-part_len+1:]
                else:
                    text += ' ' * (remain_columns - name_columns)

        stdout.write(text)

    def new_player(self):
        stdout.write('\n')

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
    play_ui.video_file = 'D:/test/abcedfghijklmnopqrstuvwxyz-abcedfghijklmnopqrstuvwxyz-abcedfghijklmnopqrstuvwxyz-abcedfghijklmnopqrstuvwxyz-abcedfghijklmnopqrstuvwxyz-abcedfghijklmnopqrstuvwxyz.mkv'

    for i in range(1000):
        time.sleep(1)
        play_ui.cur_pos = i + 1
        play_ui.draw()
