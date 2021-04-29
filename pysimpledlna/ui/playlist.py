import threading
import time
from queue import Queue, Empty

from prompt_toolkit import Application
from prompt_toolkit.filters import Condition
from prompt_toolkit.input import Input
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.bindings.focus import focus_next
from prompt_toolkit.layout import CompletionsMenu, Layout
from prompt_toolkit.lexers import DynamicLexer, PygmentsLexer
from prompt_toolkit.output import ColorDepth, Output
from prompt_toolkit.formatted_text import (
    HTML,
    AnyFormattedText,
    to_formatted_text
)
from typing import TextIO, List

from prompt_toolkit.styles import BaseStyle, Style

from prompt_toolkit_ext.progress import ProgressModel, Progress
from prompt_toolkit_ext.widgets import RadioList
from prompt_toolkit_ext.event import KeyEvent
from prompt_toolkit.layout.dimension import AnyDimension, D, Dimension
from prompt_toolkit.formatted_text.utils import fragment_list_width

from pysimpledlna.ui.terminal import PlayerStatus
from prompt_toolkit.shortcuts.progress_bar.formatters import Formatter, Text
import abc
import os

from prompt_toolkit.layout.containers import HSplit, VSplit, Window, ConditionalContainer, WindowAlign, Float
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import Box, Label, SearchToolbar, TextArea, Dialog, Button, MenuContainer, MenuItem
from typing import Optional, Sequence, Tuple
import logging

from pysimpledlna.entity import Playlist


class PlayListPlayer(Progress):

    def __init__(self,
                 playlist_part: RadioList,
                 top_text: Tuple[str] = None,
                 title: AnyFormattedText = None,
                 formatters: Optional[Sequence[Formatter]] = None,
                 bottom_toolbar: AnyFormattedText = None,
                 style: Optional[BaseStyle] = None,
                 file: Optional[TextIO] = None,
                 color_depth: Optional[ColorDepth] = None,
                 output: Optional[Output] = None,
                 input: Optional[Input] = None,
                 ) -> None:

        super().__init__(title, formatters, bottom_toolbar, style, None, file, color_depth, output, input)
        self.bottom_part = None
        self.top_part = None
        self.progress_controls_part = None
        self.player_controls_part = None
        self.player_controls_keybindings = None
        self.player_controls_cp = None
        self.playlist_part: RadioList = playlist_part
        self.top_text: Tuple[str] = top_text

        self.player_events = {
            'quit': KeyEvent('q'),
            'focus_playlist': KeyEvent('n'),
            'focus_controller': KeyEvent('m'),
        }

        self.controller_events = {
            'forward': KeyEvent('right'),
            'backward': KeyEvent('left'),
            'next': KeyEvent('pagedown'),
            'last': KeyEvent('pageup'),
            'pause': KeyEvent('p'),
        }

        self.pressed_key = ''
        self.pressed_key_cnt = 0
        self.min_key_press_interval = 0.05
        self.last_key_press_time = time.time()

        self.event_queue = Queue()
        self.event_thread = None

    def is_accept_key_press(self):
        return (time.time() - self.last_key_press_time) > self.min_key_press_interval

    def _get_pressed_key_str(self):
        if self.pressed_key_cnt == 0:
            return 'Status: '
        return f'Status: [{self.pressed_key}] [+{str(self.pressed_key_cnt)}]'

    def create_model(
        self,
        remove_when_done: bool = False,
    ) -> "ProgressModel":
        model = PlayerModel(self, remove_when_done=remove_when_done)
        self.models.append(model)
        return model

    def create_content(self, progress_controls):

        self.progress_controls_part = super().create_content(progress_controls)
        self.player_controls_cp = FormattedTextControl(
                ' ',
                key_bindings=self.player_controls_keybindings,
                focusable=True,
            )

        self.player_controls_part = HSplit([
            VSplit([
                Label(text="[PgUp] 上一个"),
                Label(text="[<-] 后退"),
                Label(text="[p] 暂停/播放"),
                Label(text="[->] 前进"),
                Label(text="[PgDn] 下一个"),
                Window(
                    self.player_controls_cp,
                    height=1,
                    dont_extend_width=True,
                    dont_extend_height=True,
                ),
            ]),
            Label(text=self._get_pressed_key_str, style="class:bottom-toolbar"),
        ])

        self.top_part = HSplit([
            self.progress_controls_part,
            Window(height=1, char="-", style="class:line"),
            self.player_controls_part,
        ])

        self.bottom_part = Box(self.playlist_part, height=Dimension(), width=Dimension())

        parts = []
        if self.top_text is not None:
            parts.append(Window(FormattedTextControl(self.top_text),
                                height=len(self.top_text), style="reverse"))
        parts.append(HSplit([self.top_part, Window(height=1, char="-"), self.bottom_part], width=Dimension()))
        body = VSplit(parts)
        return body

    def create_ui(self):
        super().create_ui()
        self.event_thread = threading.Thread(target=self.execute_key, daemon=True)
        self.event_thread.start()

    def create_key_bindings(self):

        player_kb = KeyBindings()

        @player_kb.add(self.player_events['quit'].key)
        def _(event):
            self.exit()
            for model in self.models:
                model.player_status = PlayerStatus.STOP
            self.player_events['quit'].fire(event)

        @player_kb.add(self.player_events['focus_playlist'].key)
        def _(event):
            self.app.layout.focus(self.bottom_part)
            self.player_events['focus_playlist'].fire(event)

        @player_kb.add(self.player_events['focus_controller'].key)
        def _(event):
            self.app.layout.focus(self.player_controls_cp)
            self.player_events['focus_controller'].fire(event)

        self.key_bindings = player_kb

        player_controller_kb = KeyBindings()

        @player_controller_kb.add(self.controller_events['forward'].key)
        def _(event):
            if not self.is_accept_key_press():
                return
            self.last_key_press_time = time.time()
            key = self.controller_events['forward'].key
            self.event_queue.put([key, event])

        @player_controller_kb.add(self.controller_events['backward'].key)
        def _(event):
            if not self.is_accept_key_press():
                return
            self.last_key_press_time = time.time()
            key = self.controller_events['backward'].key
            self.event_queue.put([key, event])

        @player_controller_kb.add(self.controller_events['next'].key)
        def _(event):
            if not self.is_accept_key_press():
                return
            self.last_key_press_time = time.time()
            key = self.controller_events['next'].key
            self.event_queue.put([key, event])

        @player_controller_kb.add(self.controller_events['last'].key)
        def _(event):
            if not self.is_accept_key_press():
                return
            self.last_key_press_time = time.time()
            key = self.controller_events['last'].key
            self.event_queue.put([key, event])

        @player_controller_kb.add(self.controller_events['pause'].key)
        def _(event):
            self.controller_events['pause'].fire(event)

        self.player_controls_keybindings = player_controller_kb

    def execute_key(self):

        seek_queue = []
        switch_queue = []

        seek_key_map = {
            "left": 'backward',
            'right': 'forward',
        }

        switch_key_map = {
            'pagedown': 'next',
            'pageup': 'last',
        }

        def get_next_event():
            try:
                next_val = self.event_queue.get(block=False, timeout=0)
                return next_val[0], next_val[1]
            except Empty:
                return None, None

        def add_key_to_local_queue(local_queue: List, key, name, event):

            def set_key_cnt():
                if key in switch_key_map:
                    self.pressed_key_cnt = len(local_queue)
                elif key in seek_key_map:
                    self.pressed_key_cnt = len(local_queue) * 10

            if len(local_queue) > 0:
                last_key = local_queue[-1][0]
                # 不相同的key，抵消一个
                if last_key != key:
                    local_queue.pop()
                    logging.debug(f'key changed: {key}, old, {last_key}, queue len {len(local_queue)}')
                    set_key_cnt()
                    return
            local_queue.append([key, event])
            logging.debug(f'queue append: {key}, queue len {len(local_queue)}')
            self.pressed_key = name.capitalize()
            set_key_cnt()

        def clear_local_queue(local_queue: List):
            local_queue.clear()
            logging.debug(f'queue cleared')
            self.pressed_key = ''
            self.pressed_key_cnt = 0

        def execute_queue(local_queue: List):
            if len(local_queue) == 0:
                return

            _key, _event = local_queue[-1]

            if _key in seek_key_map:
                _event_name = seek_key_map[_key]
            elif _key in switch_key_map:
                _event_name = switch_key_map[_key]
            else:
                return

            cnt = len(local_queue)

            if cnt > 0:

                try:
                    self.controller_events[_event_name].fire(_event, len(local_queue))
                finally:
                    clear_local_queue(local_queue)

        while True:
            start = time.time()
            key, event = get_next_event()

            seek_queue_has_data = len(seek_queue) > 0
            switch_queue_has_data = len(switch_queue) > 0
            is_empty_key = key is None and event is None
            if not is_empty_key:
                is_seek_key = key in seek_key_map
                is_switch_key = key in switch_key_map

            if is_empty_key:  # 按键中断

                if seek_queue_has_data:
                    execute_queue(seek_queue)
                if switch_queue_has_data:
                    logging.debug('execute switch queue')
                    execute_queue(switch_queue)

            elif is_seek_key:

                execute_queue(switch_queue)
                add_key_to_local_queue(seek_queue, key, seek_key_map[key], event)

            elif is_switch_key:
                # 切换视频时忽略跳转时间
                seek_queue.clear()
                add_key_to_local_queue(switch_queue, key, switch_key_map[key], event)

            if not self.app.is_running:
                break

            # 处理连续按键，不等待
            if self.event_queue.qsize() > 0:
                continue

            end = time.time()
            dur = end - start
            left_time = 0.8 - dur
            # 在一段时间内查看是否有新按键，有则进行处理，没有则等待直到时间耗尽
            for i in range(int(left_time*20)):
                time.sleep(0.05)
                if self.event_queue.qsize() > 0:
                    break

    def get_bottom_part(self):
        return self.bottom_part

    def get_top_part(self):
        return self.top_part


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


class PlayListEditor:
    
    def __init__(self, playlist: Playlist, editable=False) -> None:
        self.playlist: Playlist = playlist
        self.editable = False
        self.text_field = None
        self.application = None
        self.key_bindings = None
        self.layout = None
        self.play_info_dialog = None
        self.skip_info_dialog = None
        self.show_status_bar = True
        self.focus_index = 0

    def run(self):
        if self.application is not None:
            self.application.run()

    def is_show_status_bar(self):
        return self.show_status_bar

    def create_key_bindings(self):
        kb = KeyBindings()

        @kb.add('c-q')
        def _(event):
            self.exit()

        kb.add("tab")(focus_next)

        self.key_bindings = kb

    def create_content(self):

        # 文本编辑器
        text_editor = self.create_text_editor()

        # 播放列表属性编辑器
        property_editor = self.create_property_editor()

        body = HSplit(
            [
                HSplit([
                    property_editor,
                    Label(' '),
                    Window(height=1, char="-", style="class:line"),
                    text_editor,
                ], height=D(), ),
                ConditionalContainer(
                    content=VSplit(
                        [
                            Window(
                                FormattedTextControl(self.get_statusbar_text), style="class:status"
                            ),
                            Window(
                                FormattedTextControl(self.get_statusbar_right_text),
                                style="class:status.right",
                                width=9,
                                align=WindowAlign.RIGHT,
                            ),
                        ],
                        height=1,
                    ),
                    filter=Condition(lambda: self.is_show_status_bar()),
                ),
            ])

        self.create_key_bindings()

        root_container = MenuContainer(
            body=body,
            menu_items=[
                MenuItem(
                    "File",
                    children=[
                        MenuItem("Exit", handler=self.exit),
                    ],
                ),
            ],
            floats=[
                Float(
                    xcursor=True,
                    ycursor=True,
                    content=CompletionsMenu(max_height=16, scroll_offset=1),
                ),
            ],
            key_bindings=self.key_bindings,
        )

        style = Style.from_dict(
            {
                "status": "reverse",
                "shadow": "bg:#440044",
            }
        )

        self.layout = Layout(root_container, focused_element=self.text_field)

        self.application = Application(
            layout=self.layout,
            enable_page_navigation_bindings=True,
            style=style,
            mouse_support=True,
            full_screen=True,
        )

    def create_property_editor(self):

        current_file_path = self.playlist.file_list[self.playlist.current_index]
        _, current_file_name = os.path.split(current_file_path)

        self.play_info_dialog = Dialog(modal=False, title="播放记录", body=HSplit([
                Label(''),
                Label(' 播放文件'),
                Button(
                    f'{current_file_name}',
                ),
                Label(' 播放位置'),
                Button(
                    f'{self.playlist.current_pos}',
                ),
                Label(''),
            ], width=38, padding=1))
        self.skip_info_dialog = Dialog(modal=False, title="设置", body=HSplit([
                Label(''),
                Label(' 跳过片头'),
                Button(
                    f'{self.playlist.skip_head}',
                ),
                Label(' 跳过片尾'),
                Button(
                    f'{self.playlist.skip_tail}',
                ),
                Label(''),
            ], width=38, padding=1))

        left_window = VSplit([
            self.play_info_dialog,
            self.skip_info_dialog,
        ], width=40, padding=2)
        return left_window

    def create_text_editor(self):
        search_toolbar = SearchToolbar()
        text = ''
        for file_path in self.playlist.file_list:
            text += file_path + '\n'
        self.text_field = TextArea(
            text=text,
            read_only=True,
            #lexer=DynamicLexer(
            #    lambda: PygmentsLexer.from_filename(
            #        ApplicationState.current_path or ".txt", sync_from_start=False
            #    )
            #),
            scrollbar=True,
            line_numbers=True,
            search_field=search_toolbar,
        )
        text_editor = HSplit(
            [
                self.text_field,
                search_toolbar
            ]
        )
        return text_editor

    def exit(self):
        if self.application.is_running:
            self.application.exit()

    def get_statusbar_text(self):
        return " Press ctrl-q to exit. "

    def get_statusbar_right_text(self):
        return " {}:{}  ".format(
            self.text_field.document.cursor_position_row + 1,
            self.text_field.document.cursor_position_col + 1,
        )
