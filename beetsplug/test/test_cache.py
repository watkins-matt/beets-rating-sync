import unittest

from beetsplug.recording import RecordingInfo
from beetsplug.track_cache import MBTrackCache


class TestMBCache(unittest.TestCase):
    def test_cache(self):
        cache = MBTrackCache()
        cache.add(
            RecordingInfo(
                "Sonny Bass & Timmo Hendriks",
                "Slingshot",
                "Slingshot",
                195,
                "0089b4cf-9c65-4644-969f-ed45bb99e1e2",
            )
        )

        first = cache.get("Sonny Bass feat. Timo Hendriks", "Slingshot", "")
        self.assertIsNotNone(first)
        second = cache.get("Sonny Bass & Timo Hendriks", "Slingshot", "")
        self.assertEqual(second, first)
        third = cache.get("Sonny Bass & Timmo Hendriks", "Slingshot", "Slingshot")
        self.assertEqual(third, first)
        fourth = cache.get("Sonny Bass", "Slingshot", "Slingshot")
        self.assertEqual(fourth, first)
        fifth = cache.get("Sonny Bass", "Slingshot", "")
        self.assertEqual(fifth, first)

        cache.save()


if __name__ == "__main__":
    unittest.main()
