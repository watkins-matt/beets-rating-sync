import sys

import musicbrainzngs
from beets.dbcore import types
from beets.plugins import BeetsPlugin
from beets.ui import Subcommand
from confuse import ConfigValueError, NotFoundError

from beetsplug.exporter.beet_rating_exporter import BeetRatingExporter

from .exporter.csv_exporter import CSVExporter
from .exporter.mb_rating_collection_exporter import MBRatingCollectionExporter
from .importer.last_fm_importer import LastFMLovedTrackImporter
from .importer.mb_rating_collection_importer import MBRatingCollectionImporter
from .mb_user import MBCache
from .rating_store import RatingStore, RatingStoreExporter, RatingStoreImporter
from .track_cache import MBTrackCache
from .track_finder import LibraryTrackFinder


class RatingSyncPlugin(BeetsPlugin):
    def __init__(self):
        super().__init__()
        self.track_cache = MBTrackCache()
        self.item_types = {"rating": types.INTEGER}

        # Check for MusicBrainz credentials
        try:
            self.mb_user = self.config["mb_user"].get(str)
            self.mb_pass = self.config["mb_pass"].get(str)
            self._log.debug("Found Musicbrainz credentials.")
        except (ConfigValueError, NotFoundError):
            self._log.error("Musicbrainz credentials are invalid or missing.")
            self._log.error(
                "Please ensure both mb_user and mb_pass are set in the "
                "config file under the rating_sync section."
            )
            # TODO: Handle no MusicBrainz credentials
            sys.exit(1)

        # Authenticate with MusicBrainz
        musicbrainzngs.auth(self.mb_user, self.mb_pass)
        musicbrainzngs.set_useragent(
            "Beets-Rating-Sync",
            "0.1b",
            "https://github.com/watkins-matt/beets-rating-sync",
        )
        musicbrainzngs.set_rate_limit(limit_or_interval=1.0, new_requests=1)

        # Check for LastFM credentials
        try:
            self.lastfm_user = self.config["lastfm_user"].get(str)
            self._log.debug("Found LastFM credentials.")
        except (ConfigValueError, NotFoundError):
            self.lastfm_user = None
            self._log.debug("No LastFM credentials found.")

    def commands(self):
        ratingsync = Subcommand(
            "ratingsync", help="Synchronizes ratings with provided sources."
        )
        ratingsync.func = self.rating_sync  # type: ignore
        return [ratingsync]

    # This function executes the following steps:
    # Create the rating store
    # Import from the ratings.csv file if present in the Beets directory
    # Import from the MusicBrainz user collection
    # Import the LastFM loved tracks
    # Export to MusicBrainz
    # Export to Beets
    # Export to CSV
    def rating_sync(self, lib, opts, args):
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
            exporters.append(mb_exporter)
            exporters.append(CSVExporter(mb_cache.get_rating_cache_path()))
            exporters.append(beet_exporter)

        for importer in importers:
            print("Importing from %s" % (type(importer).__name__))
            importer.import_songs(rating_store)

        for exporter in exporters:
            exporter.export_songs(rating_store)

        # Make sure to save the track cache
        self.track_cache.save()
