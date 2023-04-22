from ..mb_user import MBCache, MBRecordingCollection, MBUser
from ..rating_store import RatingStore, RatingStoreImporter
from ..track_finder import LibraryTrackFinder


class MBRatingCollectionImporter(RatingStoreImporter):
    RATING_SET = "mb"

    def __init__(
        self, user: MBUser, cache: MBCache, library_finder: LibraryTrackFinder
    ):
        self.user = user
        self.cache = cache
        self.library_finder = library_finder

    def import_songs(self, rating_store: RatingStore):
        collection_names = ["1 Star", "2 Star", "3 Star", "4 Star", "5 Star"]

        # The numeric rating is based on the order of the collection_names, starting
        # at 1. collection_names on the line above must be ordered from 1 to the
        # highest rating or this loop will fail.
        for numeric_rating, name in enumerate(collection_names, start=1):
            if self.user.has_collection(name):
                collection = self.user.get_collection(name)

                if collection.entity_type == "recording":
                    rec_collection = self.cache.get_recording_collection(
                        collection.name, collection.mbid
                    )
                    self.import_recording_collection(
                        rec_collection, numeric_rating, rating_store
                    )

    def import_recording_collection(
        self,
        collection: MBRecordingCollection,
        rating: int,
        rating_store: RatingStore,
        overwrite=False,
    ):
        """Loads ratings from a specific rating collection, using the specific number
        as the rating. If overwrite is True, existing ratings will be overwritten."""
        recordings = collection.recordings
        for recording in recordings:
            rec_info = self.library_finder.findByRecording(recording)

            if rec_info:
                rec_info.rating = rating
                rating_store.add_rating(
                    rec_info, self.RATING_SET, overwrite,
                )
            else:
                # Todo: Make this a debug log.
                # Todo: Handle edge case where the MBID changed due to merge. We need to
                # look up the MBID in Musicbrainz to get the new MBID
                print(
                    f"import_recording_collection: Could not find recording {recording.title} -- [{recording.mbid}]"
                )
                print(
                    "import_recording_collection: The track may not be in your library"
                    + ", or the MBID may be missing from the file metadata."
                )

    def get_rating_collection(self, rating: int):
        """Gets a specific rating collection corresponding to a certain number."""
        collection_names = ["1 Star", "2 Star", "3 Star", "4 Star", "5 Star"]
        return self.user.get_collection(collection_names[rating - 1])
