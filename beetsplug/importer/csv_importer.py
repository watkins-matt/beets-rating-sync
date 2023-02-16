import csv

from ..rating_store import RatingStore, RatingStoreImporter
from ..recording import RecordingInfo


class CSVImporter(RatingStoreImporter):
    def __init__(self, file_name):
        self.file_name = file_name

    def import_songs(self, rating_store: RatingStore):

        with open(self.file_name, "r") as file:
            field_names = ["rating", "artist", "album", "title", "length", "mbid"]
            reader = csv.DictReader(file, field_names)
            next(reader)  # Need to call this to skip the header row
            line = 1

            for row in reader:
                try:
                    recording = RecordingInfo(
                        row["artist"],
                        row["album"],
                        row["title"],
                        int(row["length"]),
                        row["mbid"],
                        int(row["rating"]),
                    )
                except ValueError:
                    print(f"Error reading CSV file on line {line}. Skipping line.")
                    continue

                rating_store.add_rating(recording)
                line += 1
