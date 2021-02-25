from prompt_toolkit.input import Input
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.output import ColorDepth, Output
from prompt_toolkit.formatted_text import (
    HTML,
    AnyFormattedText,
    to_formatted_text,
)
from typing import TextIO

from prompt_toolkit.styles import BaseStyle

from prompt_toolkit_ext.progress import ProgressModel, Progress
from prompt_toolkit_ext.widgets import RadioList
from prompt_toolkit.layout.dimension import AnyDimension, D
from prompt_toolkit.formatted_text.utils import fragment_list_width
from pysimpledlna.ui.terminal import PlayerStatus
from prompt_toolkit.shortcuts.progress_bar.formatters import Formatter, Text
import abc
import os

from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import Box
from typing import Optional, Sequence, Tuple


class PlayListPlayer(Progress):

    def __init__(self,
                 playlist_part: RadioList,
                 top_text: Tuple[str] = None,
                 title: AnyFormattedText = None,
                 formatters: Optional[Sequence[Formatter]] = [Text(' ')],
                 bottom_toolbar: AnyFormattedText = None, style: Optional[BaseStyle] = None,
                 file: Optional[TextIO] = None,
                 color_depth: Optional[ColorDepth] = None, output: Optional[Output] = None,
                 input: Optional[Input] = None,
                 ) -> None:
        super().__init__(title, formatters, bottom_toolbar, style, None, file, color_depth, output, input)
        self.left_part = None
        self.right_part = None
        self.playlist_part: RadioList = playlist_part
        self.top_text: Tuple[str] = top_text

    def create_model(
        self,
        remove_when_done: bool = False,
    ) -> "ProgressModel":
        model = PlayerModel(self, remove_when_done=remove_when_done)
        self.models.append(model)
        return model

    def create_content(self, progress_controls):
        self.right_part = super().create_content(progress_controls)
        self.left_part = Box(self.playlist_part, height=10, width=30)

        parts = []
        if self.top_text is not None:
            parts.append(Window(FormattedTextControl(self.top_text),
                                height=len(self.top_text), style="reverse"))
        parts.append(Window(height=1, char="-"))
        parts.append(VSplit([self.left_part, Window(width=1, char="|"), self.right_part]))
        parts.append(Window(height=1, char="-"))

        body = HSplit(parts)
        return body

    def create_key_bindings(self):

        kb = KeyBindings()

        @kb.add("a")
        def _(event):
            event.app.layout.focus(self.get_left_part())

        @kb.add("b")
        def _(event):
            event.app.layout.focus(self.get_right_part())

        @kb.add('p')
        def _(event):
            player_model: PlayerModel = self.models[0]
            if player_model.cur_status == PlayerStatus.PAUSE:
                player_model.cur_status = PlayerStatus.PLAY
            elif player_model.cur_status == PlayerStatus.PLAY:
                player_model.cur_status = PlayerStatus.PAUSE

        @kb.add("q")
        def _(event):
            player_model: PlayerModel = self.models[0]
            player_model.cur_status = PlayerStatus.STOP
            " Quit application. "
            self.exit()

        self.key_bindings = kb

    def get_left_part(self):
        return self.left_part

    def get_right_part(self):
        return self.right_part
        

class PlayerModel(ProgressModel):

    def __init__(
        self,
        progress: Progress,
        remove_when_done: bool = False
    ) -> None:

        super(PlayerModel, self).__init__(
            progress=progress,
            remove_when_done=remove_when_done,
        )

        self._duration = 0
        self._cur_pos = 0
        self._player_status = PlayerStatus.STOP
        self._video_file = ''
        self._video_file_path = ''
        self._video_file_name = ''

        self._exception: Exception = None

    def draw(self):
        self.completed()

    def completed(self) -> None:
        self.progress.invalidate()

    def new_player(self):
        pass

    @property
    def exception(self):
        return self._exception

    @exception.setter
    def exception(self, e: Exception):
        self._exception = e

    @property
    def duration(self):
        return self._duration

    @property
    def cur_pos(self):
        return self._cur_pos

    @duration.setter
    def duration(self, duration):
        self._duration = duration

    @cur_pos.setter
    def cur_pos(self, cur_pos):
        self._cur_pos = cur_pos

    @property
    def player_status(self) -> PlayerStatus:
        return self._player_status

    @player_status.setter
    def player_status(self, player_status: PlayerStatus):
        self._player_status = player_status

    @property
    def video_file(self):
        return self._video_file

    @video_file.setter
    def video_file(self, video_file):
        self._video_file = video_file
        self._video_file_path, self._video_file_name = os.path.split(self.video_file)


class VideoBaseFormatter(Formatter):

    def get_width(self, progress_bar: "Progress") -> AnyDimension:
        all_values = [
            self.get_render_text(c)
            for c in progress_bar.models if isinstance(c, PlayerModel)
        ]
        if all_values:
            max_widths = max(fragment_list_width(to_formatted_text(v, '')) for v in all_values)
            return max_widths
        return 0

    @abc.abstractmethod
    def get_render_text(self, player: "PlayerModel"):
        pass


class VideoPositionFormatter(VideoBaseFormatter):

    def format(
        self,
        progress_bar: "Progress",
        progress: "PlayerModel",
        width: int,
    ) -> AnyFormattedText:
        if not isinstance(progress, PlayerModel):
            return ''
        player: PlayerModel = progress
        text = self.get_render_text(player)
        return HTML("<video-position>{text}</video-position>").format(
            text=text
        )

    def get_render_text(self, player: "PlayerModel"):

        def get_h_m_s(t):
            m, s = divmod(t, 60)
            h, m = divmod(m, 60)
            return "%02d:%02d:%02d" % (h, m, s)

        text = get_h_m_s(player.cur_pos) + '/' + get_h_m_s(player.duration)
        return text


class VideoControlFormatter(VideoBaseFormatter):

    def format(
        self,
        progress_bar: "Progress",
        progress: "PlayerModel",
        width: int,
    ) -> AnyFormattedText:
        if not isinstance(progress, PlayerModel):
            return ''
        player: PlayerModel = progress
        return HTML("<video-control>{text}</video-control>").format(
            text=self.get_render_text(player)
        )

    def get_width(self, progress_bar: "Progress"):
        return D.exact(5)

    def get_render_text(self, player: "PlayerModel"):
        return player.player_status.value


class VideoFileFormatter(VideoBaseFormatter):

    def format(
        self,
        progress_bar: "Progress",
        progress: "PlayerModel",
        width: int,
    ) -> AnyFormattedText:
        if not isinstance(progress, PlayerModel):
            return ''
        player: PlayerModel = progress
        return HTML("<video-file>{text}</video-file>").format(
            text=self.get_render_text(player)
        )

    def get_render_text(self, player: "PlayerModel"):
        return player.video_file
