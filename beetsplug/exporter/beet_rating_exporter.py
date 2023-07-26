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
        beet_existing_ratings = self.library.items(
            dbcore.query.RegexpQuery("rating", r"\d", False)
        )

        # Create a recording set for all existing rated songs in the library
        # Note that this only includes songs that have an MBID, so songs without an
        # MBID will show up in our unrated_songs set below until we add one
        existing_recording_set = {
            existing_rating["mb_trackid"]
            for existing_rating in beet_existing_ratings
            if existing_rating["mb_trackid"]
        }

        # All of the songs that are in the rating store, but not in the library
        # This will be all of the songs that are unrated and as well as songs that
        # are missing an MBID
        unrated_songs: set = rating_store.rating_set_all - existing_recording_set

        # If we find songs that are in the library, but not in the rating store,
        # usually these are songs that have been merged into another recording on Musicbrainz
        # and we still have the old MBID in the library. We need to verify that these are correctly
        # rated songs and update the MBID
        # suspect_rated_songs: set = existing_recording_set - rating_store.rating_set_all

        print(f"Found {len(unrated_songs)} unrated songs...")

        for unrated_song in unrated_songs:
            recording = rating_store.ratings.get(unrated_song, None)

            if not recording:
                print(f"Missing recording: {unrated_song} from ratings library.")
                continue

            song = matcher.match(recording)

            # We found a song and have a rating to update
            if song and recording.rating != 0:
                song["rating"] = int(recording.rating)

                # If we have an MBID, update it. This will ensure we don't have to update
                # the same song multiple times.
                if recording.mbid:
                    song["mb_trackid"] = recording.mbid

                song.store()
                found_count += 1
                print(f"Added rating: {recording.title} --- {recording.rating}")

            else:
                print(f"Missing Song: {0} --- {1}", recording.artist, recording.title)
                missing_count += 1

        return (found_count, missing_count)
