import csv
import os
from typing import Any

import pylast

from beets import plugins

from ..rating_store import RatingStore, RatingStoreImporter
from ..recording import RecordingInfo
from ..track_finder import MBTrackFinder


class LastFMLovedTrackImporter(RatingStoreImporter):
    def __init__(self, user_name, cache_dir: str, rating: int = 4, track_finder=None):
        # Last FM object
        self.last_fm = pylast.LastFMNetwork(api_key=plugins.LASTFM_KEY)
        # Last FM User
        self.user = self.last_fm.get_user(user_name)
        # List of the loved tracks, stored in reverse chronological order
        self.loved_tracks: dict[int, RecordingInfo] = {}
        self.unmatched_tracks: dict[int, RecordingInfo] = {}

        # The track finder that we use to identify tracks
        self.track_finder = track_finder
        # Default rating to assign to loved tracks
        self.default_rating = rating
        # Path to the cache file, given the directory
        self.cache_path = os.path.join(cache_dir, ".lastfm", f"loved-{user_name}.csv")
        self.unmatched_path = os.path.join(
            cache_dir, ".lastfm", f"unmatched-{user_name}.csv"
        )
        # The most recent (highest) timestamp of a song
        self.max_cached_timestamp = None
        self.load()

    def load(self):
        if os.path.exists(self.cache_path):
            self.load_cache(self.cache_path)

        if os.path.exists(self.unmatched_path):
            self.load_unmatched(self.unmatched_path)

        # Note that we always attempt to load from last_fm. We load recordings one by one
        # until we reach the first cached recording or the end if nothing is cached.
        # This will be fast if everything is cached already.
        self.load_from_lastfm()

    def load_cache(self, cache_path):
        try:
            with open(self.cache_path, "r") as f:
                reader = csv.DictReader(
                    f,
                    fieldnames=[
                        "artist",
                        "album",
                        "title",
                        "length",
                        "mbid",
                        "timestamp",
                    ],
                )

                try:
                    next(reader)  # Need to call this to skip the header row
                except StopIteration:
                    pass  # Empty file

                for row in reader:
                    recording = RecordingInfo(
                        row["artist"],
                        row["album"],
                        row["title"],
                        int(row["length"]),
                        row["mbid"],
                        self.default_rating,
                    )
                    timestamp = int(row["timestamp"])
                    recording.extra["lastfm_timestamp"] = timestamp
                    self.loved_tracks[timestamp] = recording

                    self.max_cached_timestamp = (
                        timestamp
                        if not self.max_cached_timestamp
                        else max(self.max_cached_timestamp, timestamp)
                    )

        except IOError:
            # If there were issues loading the cache, reload and recache from Musicbrainz.
            print(
                f"LastFMLovedTrackImporter.load_cache: Unable to load loved tracks from {cache_path}."
            )
            print("Recaching from LastFM.")

    def load_unmatched(self, cache_path):
        try:
            with open(self.unmatched_path, "r") as f:
                reader = csv.DictReader(
                    f,
                    fieldnames=[
                        "artist",
                        "title",
                        "timestamp",
                    ],
                )

                try:
                    next(reader)  # Need to call this to skip the header row
                except StopIteration:
                    pass  # Empty file

                for row in reader:
                    artist = row["artist"]
                    title = row["title"]
                    timestamp = int(row["timestamp"])

                    tf = self.track_finder if self.track_finder else MBTrackFinder()
                    recording = tf.find(artist, title)

                    if recording:
                        recording.extra["lastfm_timestamp"] = timestamp
                        self.loved_tracks[timestamp] = recording
                    else:
                        recording = RecordingInfo(
                            artist, "", title, 0, "", self.default_rating
                        )
                        recording.extra["lastfm_timestamp"] = timestamp
                        self.unmatched_tracks[timestamp] = recording
                        print(f'No match found for {artist} -- "{title}"')

                    # We still update the max cached timestamp regardless so we don't
                    # reload unmapped tracks
                    self.max_cached_timestamp = (
                        timestamp
                        if not self.max_cached_timestamp
                        else max(self.max_cached_timestamp, timestamp)
                    )

        except IOError:
            # If there were issues loading the cache, reload and recache from Musicbrainz.
            print(
                f"LastFMLovedTrackImporter.load_cache: Unable to load unmatched tracks from {cache_path}."
            )
            print("Recaching from LastFM.")

    def load_from_lastfm(self):
        # If track finder was provided, use that, otherwise the generic MBTrackFinder
        tf = self.track_finder if self.track_finder else MBTrackFinder()

        try:
            for loved_track in self.user.get_loved_tracks(limit=None, cacheable=True, stream=True):  # type: ignore
                track = loved_track.track
                timestamp = int(loved_track.timestamp)
                artist = track.get_artist().name
                title = track.get_name()
                album = None

                # If this timestamp is lower than the max, we have already loaded the rest before
                # from the cache
                if self.max_cached_timestamp and timestamp <= self.max_cached_timestamp:
                    break

                try:
                    album = track.get_album()
                    if album:
                        # If the album title is the same as the title, ignore it; we will try to
                        # search for the album title with the same name as a last resort.
                        # This avoids bad data from Last.fm where we are missing the actual
                        # album name and we need to search for it.
                        album = album.title if album.title != title else None
                # Did not find an album or Last.fm returned an error.
                # For some reason reading the album tends to fail quite often.
                # If we pass a null album to the track finder, it should still generally
                # be able to find the track, although having the album name helps.
                except (
                    pylast.WSError,
                    pylast.NetworkError,
                    pylast.MalformedResponseError,
                ):
                    # We can continue safely.
                    # We don't need to bug the user with random exceptions that
                    # don't have a negative impact.
                    pass

                recording = tf.find(
                    artist,
                    title,
                    album,
                )

                if recording:
                    recording.extra["lastfm_timestamp"] = timestamp
                    self.loved_tracks[timestamp] = recording
                else:
                    recording = RecordingInfo(
                        artist, "", title, 0, "", self.default_rating
                    )
                    recording.extra["lastfm_timestamp"] = timestamp
                    self.unmatched_tracks[timestamp] = recording
                    print(f'No match found for {artist} -- "{title}"')

        except pylast.WSError as exception:
            print("Error: %s" % exception)

        self.save_cache()
        self.save_unmatched()

    def save_cache(self):

        field_names = ["artist", "album", "title", "length", "mbid", "timestamp"]

        # Create the cache directory if necessary
        directory = os.path.dirname(self.cache_path)
        if not os.path.exists(directory):
            os.mkdir(directory)

        # Need to make sure the tracks are sorted by timestamp. They may be out of order if we
        # found tracks that were unmapped previously
        recordings = sorted(
            self.loved_tracks.values(),
            key=lambda x: x.extra["lastfm_timestamp"],
            reverse=True,
        )

        with open(self.cache_path, "w") as f:
            writer = csv.DictWriter(f, field_names)
            writer.writeheader()

            updated_timestamp = False
            for recording in recordings:
                # Assuming that tracks are sorted in descending timestamp order,
                # the first track will have the highest timestamp
                if not updated_timestamp:
                    self.max_cached_timestamp = recording.extra["lastfm_timestamp"]
                    updated_timestamp = True

                row: dict[str, Any] = {
                    "artist": recording.artist,
                    "album": recording.album,
                    "title": recording.title,
                    "length": recording.length,
                    "mbid": recording.mbid,
                    "timestamp": recording.extra["lastfm_timestamp"],
                }

                writer.writerow(row)  # type: ignore

    def save_unmatched(self):
        # Don't need to do anything if there are no unmatched tracks
        if len(self.unmatched_tracks) == 0:
            return

        # Create the cache directory if necessary
        directory = os.path.dirname(self.unmatched_path)
        if not os.path.exists(directory):
            os.mkdir(directory)

        recordings = sorted(
            self.unmatched_tracks.values(),
            key=lambda x: x.extra["lastfm_timestamp"],
            reverse=True,
        )

        field_names = ["artist", "title", "timestamp"]
        with open(self.unmatched_path, "w") as f:
            writer = csv.DictWriter(f, field_names)
            writer.writeheader()

            for recording in recordings:

                row: dict[str, Any] = {
                    "artist": recording.artist,
                    "title": recording.title,
                    "timestamp": recording.extra["lastfm_timestamp"],
                }

                writer.writerow(row)  # type: ignore

    def import_songs(self, rating_store: RatingStore):
        # Load the songs if we haven't already
        if len(self.loved_tracks) == 0:
            self.load()

        recordings = sorted(
            self.loved_tracks.values(),
            key=lambda k: (-k.rating, k.artist, k.album, k.title),
        )

        for recording in recordings:
            recording.rating = self.default_rating
            rating_store.add_rating(recording)
