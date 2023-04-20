import os
import time
import unittest
from pathlib import Path

from beets import dbcore, library


class TestBeetRatingExporter(unittest.TestCase):
    def test_find_rated_songs(self):
        home = str(Path.home())
        beet_path = os.getenv("BEETSDIR", default=home)
        beet_path = os.path.join(beet_path, "library.db")

        beet_lib = library.Library(path=beet_path)

        start = time.perf_counter()
        songs = beet_lib.items(dbcore.query.RegexpQuery("rating", r"\d"))
        end = time.perf_counter()
        runtime = end - start

        print(f"Regex query runtime: {runtime}s")
        print(len(songs))


if __name__ == "__main__":
    unittest.main()
