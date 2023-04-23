import os
import pathlib
import unittest

from beetsplug.exporter.csv_exporter import CSVExporter
from beetsplug.importer.csv_importer import CSVImporter
from beetsplug.rating_store import (RatingStore, RatingStoreExporter,
                                    RatingStoreImporter)
from beetsplug.recording import RecordingInfo


class MockMBRatingCollectionImporter(RatingStoreImporter):
    def import_songs(self, rating_store: RatingStore):
        one_last_time = RecordingInfo(
            "Alesso",
            "One Last Time",
            "One Last Time",
            240,
            "5bd67e8b-3a7a-4302-9408-5277f6c0620b",
            3,
        )

        going_dumb = RecordingInfo(
            "Alesso",
            "Going Dumb",
            "Going Dumb",
            169,
            "e7c51076-088c-4e67-9bf1-89aa85311408",
            4,
        )

        rating_store.add_rating(one_last_time, "mb", False)
        rating_store.add_rating(going_dumb, "mb", False)


class MockLastFMImporter(RatingStoreImporter):
    def import_songs(self, rating_store: RatingStore):
        one_last_time = RecordingInfo(
            "Alesso",
            "One Last Time",
            "One Last Time",
            240,
            "5bd67e8b-3a7a-4302-9408-5277f6c0620b",
            3,
        )
        test_song = RecordingInfo(
            "Cool Artist",
            "Hit Song",
            "Hit Song",
            250,
            "e7c51076-088c-4e67-9bf1-897987987",
            3,
        )
        rating_store.add_rating(one_last_time, "lastfm", False)
        rating_store.add_rating(test_song, "lastfm", False)


class TestSync(unittest.TestCase):
    def setUp(self):
        pass

    def test_sync(self):
        current_dir = pathlib.Path(__file__).parent.resolve()

        input_file = f"{current_dir}/test_ratings.csv"
        output_file = f"{current_dir}/test_rating_generated.csv"

        # Delete the output file and start from scratch
        if os.path.exists(output_file):
            os.remove(output_file)

        self.assertTrue(os.path.exists(input_file))

        rating_store = RatingStore()
        importers: list[RatingStoreImporter] = []
        exporters: list[RatingStoreExporter] = []

        csv_importer = CSVImporter(input_file)
        importers.append(csv_importer)
        importers.append(MockLastFMImporter())
        importers.append(MockMBRatingCollectionImporter())

        csv_exporter = CSVExporter(output_file)
        exporters.append(csv_exporter)

        for importer in importers:
            importer.import_songs(rating_store)

        self.assertEqual(len(rating_store.ratings), 5)
        self.assertEqual(len(rating_store.rating_sets["lastfm"]), 2)
        self.assertEqual(len(rating_store.rating_sets["mb"]), 2)
        self.assertEqual(len(rating_store.rating_set_all), 5)

        # There should be 3 missing ratings in Musicbrainz
        self.assertEqual(len(rating_store.get_missing_ratings_for_set("mb")), 3)
        self.assertEqual(len(rating_store.get_missing_ratings_for_set("lastfm")), 3)

        for exporter in exporters:
            exporter.export_songs(rating_store)

        self.assertTrue(os.path.exists(output_file))

        # The file should have 6 lines including the header
        with open(output_file, "r") as file:
            self.assertEqual(len(file.readlines()), 6)
