import csv
import os
from pathlib import Path

import musicbrainzngs

from .credentials import contact, user_agent, version
from .recording import MBRecording

LOG_RATE_LIMIT_CALLS = True
RATE_LIMIT_CALLS = 0


def log_rate_limited_call(name):
    global LOG_RATE_LIMIT_CALLS
    global RATE_LIMIT_CALLS

    if LOG_RATE_LIMIT_CALLS:
        RATE_LIMIT_CALLS += 1
        print(f"{RATE_LIMIT_CALLS}. Rate limited call: {name}")


class MBCache:
    def __init__(self, base_path=None, folder_name=".mbcache"):
        if not base_path:
            base_path = self.get_default_dir()

        self.path = os.path.join(base_path, folder_name)

        if not os.path.exists(self.path):
            os.mkdir(self.path)

    def get_default_dir(self):
        home = str(Path.home())  # type: ignore
        beet_path = os.getenv("BEETSDIR", default=home)
        return beet_path

    def get_rating_cache_path(self):
        return os.path.join(self.path, "ratings.csv")

    def get_user(self, user, password):
        cache_path = self.get_user_cache_path(user)
        return MBUser(user, password, cache_path)

    def get_recording_collection(self, name, mbid):
        cache_path = self.get_collection_cache_path(mbid)
        return MBRecordingCollection(name, mbid, cache_path)

    def get_track_cache_path(self):
        return os.path.join(self.path, "tracks.csv")

    def get_user_cache_path(self, user):
        return os.path.join(self.path, f"user-{user}.csv")

    def get_collection_cache_path(self, mbid):
        return os.path.join(self.path, f"coll-{mbid}.csv")


class MBCollection:
    """Represents a generic collection on Musicbrainz. The entity_type field
    specifies the type of entity that the collection contains."""

    def __init__(self, name, mbid, entity_type):
        self.name = name
        self.mbid = mbid
        self.entity_type = entity_type


class MBRecordingCollection(MBCollection):
    """Represents a specific collection of recordings on Musicbrainz."""

    def __init__(self, name, mbid, cache_path):
        super().__init__(name, mbid, "recording")
        self.cache_path = cache_path
        self.recordings: list[MBRecording] = []
        self.load(cache_path)

    @staticmethod
    def from_mbcollection(collection: MBCollection, cache_path):
        return MBRecordingCollection(collection.name, collection.mbid, cache_path)

    def __repr__(self):
        return (
            f"RecordingCollection: {self.name} [{len(self.recordings)}] -> {self.mbid}"
        )

    def load(self, cache_path=None):
        # If a specific cache path is provided, use that. Otherwise, use the default
        if not cache_path:
            cache_path = self.cache_path

        if os.path.exists(cache_path):
            self.load_cache(cache_path)
        else:
            self.load_from_musicbrainz()

    def load_cache(self, cache_path):
        try:
            with open(self.cache_path, "r") as f:
                reader = csv.DictReader(f, fieldnames=["title", "length", "mbid"])
                next(reader)  # Need to call this to skip the header row

                for row in reader:
                    self.recordings.append(
                        MBRecording(row["title"], int(row["length"]), row["mbid"])
                    )

        except IOError:
            # If there were issues loading the cache, reload and recache from Musicbrainz.
            print(
                f"MBRecordingCollection.load_cache: Unable to load collection from {cache_path}."
            )
            print("Reloading and recaching from Musicbrainz.")
            self.load_from_musicbrainz()

        # Note that there may be some cases where the recording collection cache loaded successfully
        # but is empty because the collection itself is empty.
        # Prior versions attempted to reload from MusicBrainz in this case,
        # but that incurs a rate limited call. Triggering a refresh must be done manually
        # using MBRecordingCollection.load_from_musicbrainz() which will also refresh the cache.
        if len(self.recordings) == 0:
            pass
            # print(
            #     f"Warning: Recording collection '{self.name}' is empty." +
            #     "This may not be an error if the collection itself is actually empty."
            # )

    def load_from_musicbrainz(self):
        self.recordings.clear()

        log_rate_limited_call("get_recordings_in_collection")
        result = musicbrainzngs.get_recordings_in_collection(self.mbid, limit=100)

        recording_list = result["collection"]["recording-list"]
        count = result["collection"]["recording-count"]
        offset = 0

        while len(recording_list) > 0 and offset < count:
            offset += len(recording_list)

            for item in recording_list:
                length = item.get("length", None)
                if length is None:
                    print(
                        f"Warning: Recording '{item['title']}' is missing length information."
                    )
                    length = 0
                else:
                    length = int(length) / 1000

                recording = MBRecording(item["title"], int(length), item["id"])
                self.recordings.append(recording)

            log_rate_limited_call("get_recordings_in_collection")
            recording_list = musicbrainzngs.get_recordings_in_collection(
                self.mbid, limit=100, offset=offset
            )["collection"]["recording-list"]

        self.save_cache()

    def save_cache(self):
        field_names = ["title", "length", "mbid"]

        with open(self.cache_path, "w") as f:
            writer = csv.DictWriter(f, field_names)
            writer.writeheader()

            for recording in self.recordings:
                writer.writerow(
                    {
                        "title": recording.title,
                        "length": recording.length,
                        "mbid": recording.mbid,
                    }
                )


class MBUser:
    authenticated = False

    def __init__(self, user, password, cache_path):
        self.user = user
        self.cache_path = cache_path
        self.collection_index: dict[str, MBCollection] = {}
        self.collections: list[MBCollection] = []

        # Authenticate with MusicBrainz regardless of whether we are using the cache
        self.authenticate(user, password)

        # Attempt to load from the cache, otherwise MusicBrainz
        self.load(cache_path)

    def authenticate(self, user, password, reauthenticate=False):
        # If we are already authenticated, don't do it again unless necessary
        if MBUser.authenticated and not reauthenticate:
            return

        try:
            musicbrainzngs.set_useragent(user_agent, version, contact)
            musicbrainzngs.set_rate_limit(limit_or_interval=1.0, new_requests=1)
            # The below line only should be enabled while debugging authentication.
            # Under normal circumstances only one auth call is made.
            # log_rate_limited_call("auth")
            musicbrainzngs.auth(user, password)
            MBUser.authenticated = True
        except (musicbrainzngs.AuthenticationError):
            print("Error: Unable to authenticate with MusicBrainz.")
            MBUser.authenticated = False

    def load(self, cache_path):
        if os.path.exists(cache_path):
            self.load_cache(cache_path)
        else:
            self.load_from_musicbrainz()

    def load_cache(self, cache_path):
        try:
            with open(self.cache_path, "r") as f:
                reader = csv.DictReader(f, fieldnames=["name", "mbid", "type"])
                next(reader)  # Need to call this to skip the header row

                for row in reader:
                    collection = MBCollection(row["name"], row["mbid"], row["type"])
                    self.collections.append(collection)
                    self.collection_index[collection.name] = collection
        except IOError:
            # If the cache file doesn't exist, load data from MusicBrainz
            print(f"Error: Unable to load user cache for user '{self.user}'")
            print(f"from cache file at '{cache_path}'.")
            print("Reloading data from MusicBrainz and recaching.")

        # There were no collections loaded from the csv file, so try to load from MusicBrainz
        if len(self.collections) == 0:
            self.load_from_musicbrainz()

    def load_from_musicbrainz(self):
        # Ensure that if update is called multiple times,
        # we only store one copy of the collections
        self.collections.clear()  # type: ignore

        log_rate_limited_call("get_collections")
        results = musicbrainzngs.get_collections()

        collection_list = results["collection-list"]

        for collection_item in collection_list:
            collection = MBCollection(
                collection_item["name"],
                collection_item["id"],
                collection_item["entity-type"],
            )
            self.collections.append(collection)
            self.collection_index[collection.name] = collection

        # Write everything out to the cache
        self.save_cache(self.cache_path)

    def save_cache(self, cache_path):
        field_names = ["name", "mbid", "type"]

        with open(cache_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=field_names)
            writer.writeheader()

            for collection in self.collections:
                writer.writerow(
                    {
                        "name": collection.name,
                        "mbid": collection.mbid,
                        "type": collection.entity_type,
                    }
                )

    def has_collection(self, name: str) -> bool:
        """Checks to see if a specific named collection exists."""
        return name in self.collection_index

    def get_collection(self, name: str):
        """Gets a specific collection by name."""
        return self.collection_index[name]

    def submit_ratings(self, ratings: dict[str, int]):
        musicbrainzngs.submit_ratings(recording_ratings=ratings)
