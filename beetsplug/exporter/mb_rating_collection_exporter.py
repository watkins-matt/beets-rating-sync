from ..collection import add_recordings_to_collection
from ..mb_user import MBUser
from ..rating_store import RatingStore, RatingStoreExporter


class MBRatingCollectionExporter(RatingStoreExporter):
    RATING_SET = "mb"

    def __init__(self, user: MBUser):
        self.user = user

    def export_songs(self, rating_store: RatingStore):
        missing_songs_by_mbid = rating_store.get_missing_ratings_for_set(
            MBRatingCollectionExporter.RATING_SET
        )
        new_recordings = [[], [], [], [], []]  # 1 star, 2 star, 3 star, 4 star, 5 star
        new_ratings: dict[str, int] = {}  # mbid -> rating

        # Build a list of recordings to add to each collection
        for song_mbid in missing_songs_by_mbid:
            if song_mbid in rating_store.ratings:
                recording = rating_store.ratings[song_mbid]
                new_recordings[recording.rating - 1].append(song_mbid)
                new_ratings[song_mbid] = recording.rating

        collection_names = ["1 Star", "2 Star", "3 Star", "4 Star", "5 Star"]

        # The numeric rating is based on the order of the collection_names, starting
        # at 1. collection_names on the line above must be ordered from 1 to the
        # highest rating or this loop will fail.
        for numeric_rating, name in enumerate(collection_names, start=1):
            if self.user.has_collection(name):
                collection = self.user.get_collection(name)

                # We found the specific recording collection for numeric_rating
                if collection.entity_type == "recording":
                    add_recordings_to_collection(
                        collection.mbid, new_recordings[numeric_rating - 1]
                    )

        # Update the musicbrainz star ratings
        self.user.submit_ratings(new_ratings)

        # Add the ratings to the mb rating set, which should now be equivalent to
        # the "all" rating set
        rating_store.rating_sets[
            MBRatingCollectionExporter.RATING_SET
        ] = rating_store.rating_set_all
