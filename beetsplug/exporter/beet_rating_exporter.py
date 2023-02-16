from logging import getLogger

from ..matcher import RecordingMatcher
from ..rating_store import RatingStore, RatingStoreExporter


class BeetRatingExporter(RatingStoreExporter):
    def __init__(self, library):
        self.library = library

    def export_songs(self, rating_store: RatingStore):
        found_count = 0
        missing_count = 0

        recordings = sorted(rating_store.ratings, key=lambda k: k.rating, reverse=True)
        matcher = RecordingMatcher(self.library, getLogger("beets"))

        for recording in recordings:
            song = matcher.match(recording)

            if song and recording.rating != 0:
                # self._log.debug("Found song: {0}", recording.title)
                song["rating"] = int(recording.rating)
                song.store()
                found_count += 1

            else:
                # self._log.info(
                #     "Missing Song: {0} --- {1}", recording.artist, recording.title
                # )
                missing_count += 1

        return (found_count, missing_count)
