# pyright: reportOptionalMemberAccess=false
import unittest

from beetsplug.credentials import init_musicbrainzngs
from beetsplug.normalize import normalize
from beetsplug.track_finder import MBTrackFinder


class TestMBTrackFinder(unittest.TestCase):
    def setUp(self):
        init_musicbrainzngs()

    def test_find_by_mbid(self):
        mb = MBTrackFinder()
        result = mb.findByMBID("00a5ed6a-9bba-4e92-8716-1ec5096b26f9")
        self.assertIsNotNone(result)

        if result:
            self.assertEqual(result.artist.lower(), "Meduza".lower())
            self.assertEqual(result.title.lower(), "Paradise".lower())

    def test_track_finder_unicode(self):
        mb = MBTrackFinder()
        result = mb.find("Jason Derülo", "Want To Want Me (Speaker of the House Remix)")
        self.assertEqual(result.mbid, "90c5e939-f645-4455-91a2-c9a0e0e1c648")

        result = mb.find("Jason Derülo", "Want To Want Me (Speaker of the Hoüse Remix)")
        self.assertEqual(result.mbid, "90c5e939-f645-4455-91a2-c9a0e0e1c648")

    def test_track_finder(self):
        mb = MBTrackFinder()
        result = mb.find("Meduza", "Paradise")
        self.assertEqual(result.mbid, "00a5ed6a-9bba-4e92-8716-1ec5096b26f9")

        result = mb.find("Jonas Blue", "What I Like About You")
        self.assertEqual(result.mbid, "d4b596e4-4dab-4ae8-b6ac-f8b9c63515f4")

        result = mb.find("Joel Corry", "Head & Heart")
        self.assertEqual(result.mbid, "168c30ff-7597-471b-a4c8-31c719f4f8af")

        result = mb.find("Joel Corry", "Head & Heart", "Good Job")
        self.assertEqual(result.mbid, "168c30ff-7597-471b-a4c8-31c719f4f8af")

        result = mb.find("Jason Derulo", "Want To Want Me (Speaker of the House Remix)")
        self.assertEqual(result.mbid, "90c5e939-f645-4455-91a2-c9a0e0e1c648")

    def test_mb_search_releases(self):
        tf = MBTrackFinder()

        search_args = {
            "artist": "Joel Corry",
            "release": "",
        }

        title = "Head & Heart"

        track = tf.mb_search_releases(search_args, title)
        self.assertEqual(track.mbid, "168c30ff-7597-471b-a4c8-31c719f4f8af")

    def test_mb_search_recordings(self):
        tf = MBTrackFinder()

        search_args = {
            "artist": "Joel Corry",
            "release": "",
        }

        title = "Head & Heart"

        track = tf.mb_search_recordings(search_args, title)
        self.assertEqual(track.mbid, "168c30ff-7597-471b-a4c8-31c719f4f8af")

    def test_recording_search(self):
        title = "All About It"
        search_args = {
            "artist": "GTA",
        }

        tf = MBTrackFinder()
        result = tf.mb_search_recordings(search_args, title)
        self.assertIsNotNone(result)
        self.assertEqual(result.mbid, "c25d91a6-8dfe-4471-9909-e12577a338a8")
        self.assertEqual(result.title, title)

        title = normalize(title)
        search_args["artist"] = search_args["artist"].lower().strip()
        result = tf.mb_search_recordings(search_args, title)
        self.assertIsNotNone(result)
        self.assertEqual(result.mbid, "c25d91a6-8dfe-4471-9909-e12577a338a8")


if __name__ == "__main__":
    unittest.main()
