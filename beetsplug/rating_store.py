from abc import ABC, abstractmethod

from .recording import RecordingInfo


class RatingStore:
    """Acts as an in-memory representation of all of the song ratings.
    Considered the single source of truth that importers and exporters
    interact with."""

    def __init__(self):
        self.ratings = {}  # Key: mbid, Value: RecordingInfo
        self.rating_sets = {}  # Key: rating_set:str, Value: set[str]
        self.rating_set_all: set[str] = set()

    def add_rating(
        self, recording: RecordingInfo, overwrite=False, rating_set: str | None = None
    ):
        # If the recording is already present, reuse the existing rating unless
        # we specified that we should overwrite other ratings
        if recording.mbid in self.ratings and not overwrite:
            self.ratings[recording.mbid].rating = recording.rating

        self.ratings[recording.mbid] = recording
        self.rating_set_all.add(recording.mbid)

        # If a rating_set was specified, add the recording to the set,
        # creating the set if it doesn't exist
        if rating_set:
            if rating_set not in self.rating_sets:
                self.rating_sets[rating_set] = set()
            self.rating_sets[rating_set].add(recording.mbid)

    def get_missing_ratings_for_set(self, rating_set: str) -> set[str]:
        return (
            self.rating_set_all - self.rating_sets[rating_set]
            if rating_set in self.rating_sets
            else self.rating_set_all
        )


class RatingStoreImporter(ABC):
    @abstractmethod
    def import_songs(self, rating_store: RatingStore):
        pass


class RatingStoreExporter(ABC):
    @abstractmethod
    def export_songs(self, rating_store: RatingStore):
        pass
