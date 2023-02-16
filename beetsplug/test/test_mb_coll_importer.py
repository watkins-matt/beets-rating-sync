import os
import time
import unittest
from pathlib import Path

from beets import library

from ..credentials import load_musicbrainz_credentials
from ..importer.mb_rating_collection_importer import MBRatingCollectionImporter
from ..mb_user import RATE_LIMIT_CALLS, MBCache
from ..rating_store import RatingStore
from ..track_cache import MBTrackCache
from ..track_finder import LibraryTrackFinder


class TestMBCollectionImporter(unittest.TestCase):
    def setUp(self):
        username, password = load_musicbrainz_credentials()
        self.cache = MBCache(".")
        self.user = self.cache.get_user(username, password)

    def test_mb_collection_importer(self):
        home = str(Path.home())
        beet_path = os.getenv("BEETSDIR", default=home)
        beet_path = os.path.join(beet_path, "library.db")

        self.assertTrue(
            os.path.exists(beet_path), f"Beets library does not exist at {beet_path}"
        )

        beet_lib = library.Library(beet_path)
        cache = MBTrackCache()
        track_finder = LibraryTrackFinder(beet_lib, True, cache)

        start = time.perf_counter()
        importer = MBRatingCollectionImporter(self.user, self.cache, track_finder)
        store = RatingStore()
        importer.import_songs(store)
        end = time.perf_counter()

        runtime = end - start
        global RATE_LIMIT_CALLS
        print(f"Runtime: {runtime}s with {RATE_LIMIT_CALLS} rate limited calls")

        # Make sure that the amount of ratings are greater than zero
        self.assertGreater(len(store.ratings), 0)
        cache.save()
