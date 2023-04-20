import sys

import musicbrainzngs
from beets.dbcore import types
from beets.plugins import BeetsPlugin
from beets.ui import Subcommand
from confuse import ConfigValueError, NotFoundError

from beetsplug.exporter.beet_rating_exporter import BeetRatingExporter

from .collection import (CollectionGroup, RatingCollectionGroup,
                         RecordingCollection)
from .exporter.csv_exporter import CSVExporter
from .exporter.mb_rating_collection_exporter import MBRatingCollectionExporter
from .importer.last_fm_importer import LastFMLovedTrackImporter
from .importer.mb_rating_collection_importer import MBRatingCollectionImporter
from .matcher import RecordingMatcher
from .mb_user import MBCache
from .rating_store import RatingStore, RatingStoreExporter, RatingStoreImporter
from .track_cache import MBTrackCache
from .track_finder import LibraryTrackFinder


class RatingSyncPlugin(BeetsPlugin):
    def __init__(self):
        super().__init__()
        self.track_cache = MBTrackCache()
        self.item_types = {"rating": types.INTEGER}

        try:
            self.mb_user = self.config["mb_user"].get(str)
            self.mb_pass = self.config["mb_pass"].get(str)
            self._log.debug("Found Musicbrainz credentials.")
        except (ConfigValueError, NotFoundError):
            self._log.error("Musicbrainz credentials are invalid or missing.")
            self._log.error(
                "Please ensure both mb_user and mb_pass are set in the config file under the rating_sync section."
            )
            # TODO: Handle no MusicBrainz credentials
            sys.exit(1)

        musicbrainzngs.auth(self.mb_user, self.mb_pass)
        musicbrainzngs.set_useragent(
            "Beets-Rating-Sync", "0.1b", "https://github.com/watkins-matt/beets-rating-sync"
        )
        musicbrainzngs.set_rate_limit(limit_or_interval=1.0, new_requests=1)

        try:
            self.lastfm_user = self.config["lastfm_user"].get(str)
            self._log.debug("Found LastFM credentials.")
        except (ConfigValueError, NotFoundError):
            self.lastfm_user = None
            self._log.debug("No LastFM credentials found.")

    def commands(self):
        ratingsync = Subcommand(
            "ratingsync", help="Synchronizes ratings with MusicBrainz."
        )
        ratingsync.func = self.rating_sync  # type: ignore

        newratingsync = Subcommand(
            "newratingsync", help="Synchronizes ratings with provided sources."
        )
        newratingsync.func = self.new_rating_sync  # type: ignore
        return [ratingsync, newratingsync]

    # This function executes the following steps:
    # Create the rating store
    # Import from the ratings.csv file if present in the Beets directory
    # Import from the MusicBrainz user collection
    # Import the LastFM loved tracks
    # Export to MusicBrainz
    # Export to Beets
    # Export to CSV
    def new_rating_sync(self, lib, opts, args):
        mb_cache = MBCache()
        track_finder = LibraryTrackFinder(lib, False, self.track_cache)
        rating_store = RatingStore()
        importers: list[RatingStoreImporter] = []
        exporters: list[RatingStoreExporter] = []

        if self.lastfm_user:
            last_import = LastFMLovedTrackImporter(
                self.lastfm_user, mb_cache.get_default_dir(), 4, track_finder
            )
            importers.append(last_import)

        if self.mb_user:
            mb_user = mb_cache.get_user(self.mb_user, self.mb_pass)
            mb_import = MBRatingCollectionImporter(mb_user, mb_cache, track_finder)
            mb_exporter = MBRatingCollectionExporter(mb_user)
            beet_exporter = BeetRatingExporter(lib)
            importers.append(mb_import)
            # exporters.append(mb_exporter)
            exporters.append(CSVExporter(mb_cache.get_rating_cache_path()))
            exporters.append(beet_exporter)

        for importer in importers:
            print("Importing from %s" % (type(importer).__name__))
            importer.import_songs(rating_store)

        for exporter in exporters:
            exporter.export_songs(rating_store)

    def sync_collection(self, lib, collection: RecordingCollection, rating: int):
        """Syncs a specific collection with beets"""

        found_count = 0
        missing_count = 0

        matcher = RecordingMatcher(lib, self._log)

        for recording in collection.all_recordings:
            song = matcher.match(recording)

            if song:
                self._log.debug("Found song: {0}", recording.title)
                song["rating"] = int(rating)
                song.store()
                found_count += 1

            else:
                self._log.info(
                    "Missing Song: {0} --- {1}", recording.artist, recording.title
                )
                missing_count += 1

        return (found_count, missing_count)

    def rating_sync(self, lib, opts, args):
        self._log.info("Loading MusicBrainz collections, please wait...")

        cg = CollectionGroup()
        rg = RatingCollectionGroup(cg)

        # Only sync with LastFM if a user is set
        if self.lastfm_user is not None:
            self._log.info("Syncing Last.fm loved tracks, please wait...")
            importer = LastFMLovedTrackImporter(
                self.lastfm_user,
                MBCache().get_default_dir(),
                4,
                LibraryTrackFinder(lib, False, self.track_cache),
            )
            for track in list(importer.loved_tracks.values()):
                rg.add_rating(track.mbid, track.title, 4)

            rg.save()
            self._log.info("Synced Last.fm with MusicBrainz.")

        self._log.info("Now syncing MusicBrainz collections...")

        found = 0
        missing = 0

        for rating in range(1, 6):
            collection = rg.get_rating_collection(rating)
            coll_found, coll_missing = self.sync_collection(lib, collection, rating)

            found += coll_found
            missing += coll_missing

        self._log.info("Synced {0} song(s). Missing {1} song(s).", found, missing)
        self.track_cache.save()
