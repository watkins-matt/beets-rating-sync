import os
import unittest
from pathlib import Path

from beets import library

from ..credentials import init_musicbrainzngs
from ..track_finder import LibraryTrackFinder


class TestLBTrackFinder(unittest.TestCase):
    def setUp(self):
        init_musicbrainzngs()

    def test_lb_track_finder(self):
        home = str(Path.home())
        beet_path = os.getenv("BEETSDIR", default=home)
        beet_path = os.path.join(beet_path, "library.db")

        beet_lib = library.Library(path=beet_path)

        track_finder = LibraryTrackFinder(beet_lib, True, None)
        recording = track_finder.find("GTA", "All About It")
        self.assertIsNotNone(recording)
        print(recording)

        recording = track_finder.find("3LAU", "You Want More", None)
        self.assertIsNotNone(recording)
        print(recording)

        # recording = track_finder.find("Andrew Rayel", "Till The Sky Falls Down (Andrew Rayel Remix)", None)
        # self.assertIsNotNone(recording)
        # print(recording)

        # recording = track_finder.find(
        #     "Dash Berlin", "Till The Sky Falls Down (Andrew Rayel Remix)", None
        # )
        # self.assertIsNotNone(recording)
        # print(recording)

        recording = track_finder.find("Illenium", "Wouldn’t Change A Thing", None)
        self.assertIsNotNone(recording)
        print(recording)

        recording = track_finder.find("Duke Dumont", "Won’t Look Back", None)
        self.assertIsNotNone(recording)
        print(recording)

        recording = track_finder.find("Duke Dumont", "Won't Look Back", None)
        self.assertIsNotNone(recording)
        print(recording)


if __name__ == "__main__":
    unittest.main()
