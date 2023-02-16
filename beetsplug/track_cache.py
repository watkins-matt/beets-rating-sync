import csv
import os
from pathlib import Path

from .normalize import first_artist, normalize
from .recording import RecordingInfo


class MBTrackCache:
    def __init__(self, cache_file_path=None):
        # Create a default path if it doesn't exist
        # Should be $BEETSDIR/.mbcache/tracks.csv or ~/.mbcache/tracks.csv
        if cache_file_path is None:
            home = str(Path.home())
            beet_path = os.getenv("BEETSDIR", default=home)
            cache_file_path = os.path.join(beet_path, ".mbcache", "tracks.csv")

        self.cache_file_path = cache_file_path
        self.cache, self.mbidCache = self.__load_cache(cache_file_path)

    def __load_cache(self, path):
        cache = {}
        mbidCache = {}

        # Cache file doesn't exist
        if not os.path.exists(path):
            return cache

        with open(path, newline="") as cache_file:
            field_names = ["mbid", "artist", "title", "album", "length"]
            reader = csv.DictReader(cache_file, fieldnames=field_names)

            for row in reader:
                # Skip if this is the header row
                if row["mbid"] == "mbid":
                    continue

                recording = RecordingInfo(
                    row["artist"],
                    row["album"],
                    row["title"],
                    int(row["length"]),
                    row["mbid"],
                )

                key = self.build_key(recording)
                cache[key] = recording
                mbidCache[row["mbid"]] = recording

        return cache, mbidCache

    def save(self, path=None):
        # Don't write empty files
        if len(self.cache.keys()) == 0:
            return

        # Use the default path location if it isn't provided
        if not path:
            path = self.cache_file_path

        with open(path, "w", newline="") as cache_file:
            field_names = ["mbid", "artist", "title", "album", "length"]
            writer = csv.DictWriter(cache_file, fieldnames=field_names)
            writer.writeheader()

            recordings = list(self.cache.values())
            recordings = sorted(recordings, key=lambda x: x.artist)

            for recording in recordings:
                writer.writerow(
                    {
                        "mbid": recording.mbid,
                        "artist": recording.artist,
                        "title": recording.title,
                        "album": recording.album,
                        "length": recording.length,
                    }
                )

    # Note that the key is artist:title
    # We do not specify the album because it isn't always available
    def build_key(self, info: RecordingInfo) -> str:
        artist = first_artist(info.artist)
        title = normalize(info.title)

        key = f"{artist}:{title}"
        key = key.lower()
        return key

    def add(self, info: RecordingInfo):
        key = self.build_key(info)
        self.cache[key] = info

    def get(
        self, artist: str, title: str, album: str | None = None
    ) -> RecordingInfo | None:
        key = self.build_key(RecordingInfo(artist, album, title, 0, ""))
        result = self.cache.get(key, None)
        return result

    def getByMBID(self, mbid: str) -> RecordingInfo | None:
        return self.mbidCache.get(mbid, None)
