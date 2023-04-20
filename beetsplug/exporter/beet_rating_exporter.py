from logging import getLogger

from ..matcher import RecordingMatcher
from ..rating_store import RatingStore, RatingStoreExporter


class BeetRatingExporter(RatingStoreExporter):
    def __init__(self, library):
        self.library = library

    def export_songs(self, rating_store: RatingStore):
        found_count = 0
        missing_count = 0

        recordings = sorted(rating_store.ratings.values(), key=lambda k: k.rating, reverse=True)
        matcher = RecordingMatcher(self.library, getLogger("beets"))

        for recording in recordings:
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
