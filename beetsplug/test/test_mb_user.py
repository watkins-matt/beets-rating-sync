import os
import time
import unittest

from ..credentials import load_musicbrainz_credentials
from ..mb_user import MBCache, MBRecordingCollection, MBUser


class TestMBUser(unittest.TestCase):
    def setUp(self):
        self.user, self.password = load_musicbrainz_credentials()

    def test_mb_user_caching(self):
        mb_cache = MBCache(".")
        user_cache_path = mb_cache.get_user_cache_path(self.user)

        if os.path.exists(user_cache_path):
            os.remove(user_cache_path)

        start = time.perf_counter()
        user = MBUser(
            self.user,
            self.password,
            user_cache_path,
        )
        end = time.perf_counter()
        runtime = end - start

        self.assertEqual(user.authenticated, True)
        self.assertEqual(os.path.exists(user_cache_path), True)

        start = time.perf_counter()
        user = MBUser(
            self.user,
            self.password,
            user_cache_path,
        )
        end = time.perf_counter()
        cachedRuntime = end - start
        speedup = round(runtime / cachedRuntime)

        print(f"Initial: {runtime}s vs Cached: {cachedRuntime}s")
        print(f"Total Speedup: {speedup}x")

    def test_mb_coll_caching(self):
        mb_cache = MBCache(".")
        user_cache_path = mb_cache.get_user_cache_path(self.user)
        user = MBUser(
            self.user,
            self.password,
            user_cache_path,
        )

        collection = user.get_collection("3 Star")
        cache_path = mb_cache.get_collection_cache_path(collection.mbid)

        recording_col = MBRecordingCollection.from_mbcollection(collection, cache_path)

        # We need to start from scratch for testing purposes
        if os.path.exists(cache_path):
            os.remove(cache_path)

        start = time.perf_counter()
        recording_col.load(cache_path)
        end = time.perf_counter()
        runtime = end - start

        self.assertEqual(os.path.exists(cache_path), True)
        print("Finished first load...")

        start = time.perf_counter()
        recording_col.load(cache_path)
        end = time.perf_counter()
        cachedRuntime = end - start

        speedup = round(runtime / cachedRuntime)

        print(f"Initial: {runtime}s vs Cached: {cachedRuntime}s")
        print(f"Total Speedup: {speedup}x")


if __name__ == "__main__":
    unittest.main(module="test_mb_user")
