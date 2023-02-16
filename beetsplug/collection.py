import math

import musicbrainzngs

from .recording import RecordingInfo


def star_to_hundred_rating(rating: int):
    """
    Convert star rating from (0 to 5) to (0 to 100)
    """
    rating = 0 if rating < 0 else rating
    rating = 5 if rating > 5 else rating

    return math.floor(rating * 20)


class RatingCollectionGroup:
    """A group of collections that specifically are used to store user ratings.
    There is one collection for each rating from 1 to 5."""

    def __init__(self, collection_group):
        self.collection_group = collection_group
        self.rating_collections = []
        self.rating_collection_index = {}
        self.ratings = {}
        self.load(collection_group)

    def load(self, collection_group):
        """Loads all of the rating collections from the collection group."""
        self.rating_collections.clear()
        self.rating_collection_index.clear()

        collection_names = ["1 Star", "2 Star", "3 Star", "4 Star", "5 Star"]

        # The numeric rating is based on the order of the collection_names, starting
        # at 1. collection_names on the line above must be ordered from 1 to the
        # highest rating or this loop will fail.
        for numeric_rating, name in enumerate(collection_names, start=1):
            if collection_group.has_collection(name):
                collection = collection_group.get_collection(name)
                self.rating_collections.append(collection_group.get_collection(name))
                self.rating_collection_index[name] = collection
                self.load_ratings(collection, numeric_rating)

    def load_ratings(self, collection, rating: int, overwrite=False):
        """Loads ratings from a specific rating collection, using the specific number
        as the rating. If overwrite is True, existing ratings will be overwritten."""
        recordings = collection.recordings
        for recording in recordings:
            if recording.mbid not in self.ratings or overwrite:
                self.ratings[recording.mbid] = star_to_hundred_rating(rating)

    def get_rating_collection(self, rating: int):
        """Gets a specific rating collection corresponding to a certain number."""
        collection_names = ["1 Star", "2 Star", "3 Star", "4 Star", "5 Star"]
        return self.rating_collection_index[collection_names[rating - 1]]

    def add_rating(self, mbid: str, title: str, rating: int, overwrite=False):
        if mbid not in self.ratings or overwrite:
            rating_collection = self.get_rating_collection(rating)
            rating_collection.add_recording(mbid, title)

    def save(self):
        """Saves all of the user ratings to their specified collection and updates
        the musicbrainz star ratings"""
        for collection in self.rating_collections:
            collection.save()

        musicbrainzngs.submit_ratings(recording_ratings=self.ratings)


class CollectionGroup:
    """Represents all of the collections for a specific user."""

    def __init__(self):
        # self.user = user
        self.all_collections: list[RecordingCollection] = []
        self.collection_index: dict[str, RecordingCollection] = {}
        self.update()

    def update(self):
        """Pulls all of the collections from the server and
        updates the CollectionGroup with them."""
        # Ensure that if update is called multiple times,
        # we only store one copy of the collections
        self.all_collections.clear()
        results = musicbrainzngs.get_collections()
        collection_list = results["collection-list"]

        for collection in collection_list:
            # Note that we are only dealing with recording collections at this time
            if collection["entity-type"] == "recording":
                newCollection = RecordingCollection(
                    collection["name"], collection["id"]
                )
                self.all_collections.append(newCollection)
                self.collection_index[newCollection.name] = newCollection

        return self.all_collections

    @property
    def all(self):
        """Get all of the collections in the CollectionGroup."""
        return self.all_collections

    def has_collection(self, name: str) -> bool:
        """Checks to see if a specific named collection exists."""
        return name in self.collection_index

    def get_collection(self, name: str):
        """Gets a specific collection by name."""
        return self.collection_index[name]


class RecordingCollection:
    """A MusicBrainz collection, in this case specifically a recording collection."""

    def __repr__(self) -> str:
        return (
            f"Collection: {self.name}"
            f" [Size {len(self.all_recordings)}] -> {self.mbid} )"
        )

    def __init__(self, name: str, mbid: str):
        self.name = name
        self.mbid = mbid
        self.all_recordings: list[RecordingInfo] = []
        self.new_recording_mbids: list[str] = []
        self.load()
        # TODO: Need to check the collection type somewhere,
        # this may not be a recording collection

    def load(self):
        """Loads all of the recordings from the collection and stores them in all_recordings
        as Recording objects with the mbid, title, and length."""
        # Clear recordings since we are starting from scratch
        self.all_recordings.clear()
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

                recording = RecordingInfo(
                    "", "", item["title"], int(length), item["id"]
                )
                self.all_recordings.append(recording)

            recording_list = musicbrainzngs.get_recordings_in_collection(
                self.mbid, limit=100, offset=offset
            )["collection"]["recording-list"]

        return self.all_recordings

    def save(self):
        """Saves any newly added recordings to the server. It will not do anything if no
        recordings were added."""
        # Don't save if nothing has changed
        if len(self.new_recording_mbids) > 0:
            add_recordings_to_collection(self.mbid, self.new_recording_mbids)
            self.new_recording_mbids.clear()

    def add_recording(self, mbid: str, title: str):
        """Adds a recording to the collection. The collection will not be updated until
        the save function is called."""
        self.all_recordings.append(RecordingInfo("", "", title, 0, mbid))
        self.new_recording_mbids.append(mbid)

    @property
    def recordings(self):
        return self.all_recordings


def add_recordings_to_collection(collection, recordings_to_add=[]):
    if len(recordings_to_add) >= 50:
        first_part = recordings_to_add[:50]
        assert len(first_part) == 50
        second_part = recordings_to_add[50:]
        assert len(first_part) + len(second_part) == len(recordings_to_add)

        recording_list = ";".join(first_part)

        musicbrainzngs.musicbrainz._do_mb_put(  # type: ignore
            "collection/%s/recordings/%s" % (collection, recording_list)
        )
        return add_recordings_to_collection(collection, second_part)

    recording_list = ";".join(recordings_to_add)
    return musicbrainzngs.musicbrainz._do_mb_put(  # type: ignore
        "collection/%s/recordings/%s" % (collection, recording_list)
    )


def remove_recordings_from_collection(collection, recordings_to_add=[]):
    # TODO: Break the array into chunks if it's greater than size 400
    if len(recordings_to_add) >= 400:
        raise ValueError("Cannot remove more than 400 recordings at a time.")

    recording_list = ";".join(recordings_to_add)
    return musicbrainzngs.musicbrainz._do_mb_delete(  # type: ignore
        "collection/%s/recordings/%s" % (collection, recording_list)
    )
