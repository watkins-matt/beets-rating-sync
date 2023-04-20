from logging import getLogger

from beets import dbcore

from ..matcher import RecordingMatcher
from ..rating_store import RatingStore, RatingStoreExporter


class BeetRatingExporter(RatingStoreExporter):
    def __init__(self, library):
        self.library = library

    def export_songs(self, rating_store: RatingStore):
        found_count = 0
        missing_count = 0

        matcher = RecordingMatcher(self.library, getLogger("beets"))

        # Find all of the existing ratings in the library
        beet_existing_ratings = self.library.items(dbcore.query.RegexpQuery("rating", r"\d"))

        # Create a set of all of the existing ratings
        existing_recording_set = {existing_rating["mb_trackid"] for existing_rating in
                                  beet_existing_ratings if existing_rating["mb_trackid"]}
        unrated_songs: set = existing_recording_set - rating_store.rating_set_all
        print(f"Found {len(unrated_songs)} unrated songs..")

        for unrated_song in unrated_songs:
            recording = rating_store.ratings.get(unrated_song, None)

            if not recording:
                print(f"Missing recording: {unrated_song} from ratings library.")
                continue

            print(f"Attempting to add song rating: {recording}")
            song = matcher.match(recording)

            # We found a song and have a rating to update
            if song and recording.rating != 0:

                # Only update if necessary
                existing_rating = song.get("rating", 0)
                if existing_rating != recording.rating:
                    song["rating"] = int(recording.rating)
                    song.store()
                    found_count += 1
                    print(f"Found song: {recording.title} --- {recording.rating}")

            else:
                # self._log.info(
                #     "Missing Song: {0} --- {1}", recording.artist, recording.title
                # )
                missing_count += 1

        return (found_count, missing_count)
