import fnmatch
import os
import re
from unittest import TestCase

from pysimpledlna.utils import Playlist


class TestPlaylist(TestCase):

    def test_playlist(self):

        filter_str = '*.py'
        input_dirs = [os.path.abspath('../pysimpledlna'), os.path.abspath('../test')]

        plist1 = Playlist('../test/data/test.playlist', filter_str, input_dirs)
        plist1.skip_head = 5
        plist1.skip_tail = 6

        plist1.filter_files()
        plist1.current_index = 2
        plist1.current_pos = 100
        plist1.save_playlist()

        plist2 = Playlist('../test/data/test.playlist')
        plist2.load_playlist()

        assert plist1.skip_head == plist2.skip_head
        assert plist1.skip_tail == plist2.skip_tail
        files1 = plist1.file_list
        files2 = plist2.file_list
        assert len(files1) == len(files2)
        for idx, file in enumerate(files1):
            assert os.path.samefile(file, files2[idx])
        assert plist1.current_index == plist2.current_index
        assert plist1.current_pos == plist2.current_pos
        assert os.path.samefile(plist1.current_file_path, plist2.current_file_path)

    def test_reload(self):
        filter_str = '*.mp4'
        input_dirs = [os.path.abspath('./data')]

        plist1 = Playlist('../test/data/test.playlist', filter_str, input_dirs)
        plist1.skip_head = 5
        plist1.skip_tail = 6

        plist1.filter_files()
        plist1.current_index = 2
        plist1.current_pos = 100
        plist1.save_playlist()

        with open('./data/1.mp4', 'w') as f:
            f.write('1')

        with open('./data/2.mp4', 'w') as f:
            f.write('2')
        plist1.refresh_playlist()

        assert plist1.current_index == 4
        assert plist1.current_pos == 100

        plist1.current_index = 2
        os.remove('./data/1.mp4')
        os.remove('./data/2.mp4')
        plist1.refresh_playlist()

        assert plist1.current_index == 0
        assert plist1.current_pos == 0

