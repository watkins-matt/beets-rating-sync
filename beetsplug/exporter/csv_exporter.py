import csv

from ..rating_store import RatingStore, RatingStoreExporter


class CSVExporter(RatingStoreExporter):
    def __init__(self, file_name):
        self.file_name = file_name  # type: ignore

    def export_songs(self, rating_store: RatingStore):
        # We sort by rating, then artist, then album, then title
        # Note that we want the ratings to be descending but everything else
        # ascending, hence why we use -k.rating
        recordings = sorted(
            rating_store.ratings.values(),
            key=lambda k: (-k.rating, k.artist, k.album, k.title),
        )

        with open(self.file_name, "w") as output_file:
            field_names = ["rating", "artist", "album", "title", "length", "mbid"]
            csv_writer = csv.DictWriter(output_file, fieldnames=field_names)
            csv_writer.writeheader()

            for recording in recordings:
                csv_writer.writerow(
                    {
                        "rating": recording.rating,
                        "artist": recording.artist,
                        "album": recording.album,
                        "title": recording.title,
                        "length": recording.length,
                        "mbid": recording.mbid,
                    }
                )
