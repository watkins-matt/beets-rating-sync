from abc import ABC, abstractmethod

from .recording import RecordingInfo


class Conflict:
    def __init__(self, mbid: str):
        self.mbid = mbid
        self.sources: dict[str, int] = {}  # Key: rating_set:str, Value: rating:int


class RatingStore:
    """Acts as an in-memory representation of all of the song ratings.
    Considered the single source of truth that importers and exporters
    interact with."""

    def __init__(self):
        self.ratings: dict[str, RecordingInfo] = {}  # Key: mbid, Value: RecordingInfo
        self.rating_sets: dict[
            str, set[str]
        ] = {}  # Key: rating_set:str, Value: set[str]
        self.rating_set_all: set[str] = set()
        self.conflicts: dict[str, Conflict] = {}  # Key: mbid, Value: Conflict

    def add_rating(self, recording: RecordingInfo, rating_set: str, overwrite=False):
        # If the recording is already present, reuse the existing rating unless
        # we specified that we should overwrite other ratings
        if recording.mbid in self.ratings:
            # Only overwrite if we specified that we should overwrite other ratings
            if overwrite:
                self.ratings[recording.mbid].rating = recording.rating
        # This rating doesn't exist, add it to the ratings dictionary
        else:
            self.ratings[recording.mbid] = recording

        # Add the recording to the rating set including all ratings
        self.rating_set_all.add(recording.mbid)

        # If a rating_set was specified, add the recording to the set,
        # creating the set if it doesn't exist
        if rating_set:
            # Need to create the set
            if rating_set not in self.rating_sets:
                self.rating_sets[rating_set] = set()

            # Add this rating set as a source so we can check for conflicts
            self.ratings[recording.mbid].sources[rating_set] = recording.rating
            # Add the recording to the rating set so we can compare for differences
            self.rating_sets[rating_set].add(recording.mbid)

        # Filter out LastFM source and get the remaining sources
        non_lastfm_ratings = {
            source: rating
            for source, rating in self.ratings[recording.mbid].sources.items()
            if source != "lastfm"
        }

        # Get all of the ratings from the non last-fm sources
        all_ratings = non_lastfm_ratings.values()

        # Check to see if there is any difference in the non last-fm sources
        # This means that there is a conflict between the sources
        if len(all_ratings) > 1 and max(all_ratings) != min(all_ratings):
            # This is the first conflict for this recording, create it
            if recording.mbid not in self.conflicts:
                self.conflicts[recording.mbid] = Conflict(recording.mbid)

            # Add the conflicting recording to the conflict
            self.conflicts[recording.mbid].sources = self.ratings[
                recording.mbid
            ].sources

            print(
                f"Conflict found in {rating_set}: "
                f"{recording.artist} -- {recording.title} "
                f"New:{recording.rating} Existing:{self.ratings[recording.mbid].rating}"
            )

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
