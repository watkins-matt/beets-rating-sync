import unittest

from ..normalize import (
    normalize,
    normalize_spotify_title,
    remove_feat,
    remove_quoted_text,
)


class TestNormalize(unittest.TestCase):
    def test_normalize(self):
        normalized_title = "Cool Song (Trader Joe's Remix)"

        songs = [
            "Cool Song [Trader Joe’s Remix] [Feat. John Doe]",
            "Cool Song - Trader Joe’s Remix [Feat. John Doe]",
            "Cool Song - Trader Joe’s Remix (Feat. John Doe)",
            "Cool Song (Feat. John Doe & Jane Doe) - Trader Joe’s Remix ",
        ]

        for song in songs:
            self.assertEqual(normalize(song), normalized_title.lower())

    def test_remove_quotes(self):
        songs = ["Won’t Let You Go", "Won't Let You Go"]
        expected = "Let You Go"

        for song in songs:
            self.assertEqual(remove_quoted_text(song), expected)

    def test_remove_feat(self):
        songs = {
            "My Song (feat. John Doe)": "My Song",
            "My Song (Feat. John Doe & Jane Doe)": "My Song",
            "My Song (Feat. John Doe) Version (Original Remix)": "My Song Version (Original Remix)",
            "My Song (ft. John Doe) Version (Original Remix)": "My Song Version (Original Remix)",
            "My Song (Ft. John Doe) Version (Original Remix)": "My Song Version (Original Remix)",
            "My Song (FT. John Doe) Version (Original Remix)": "My Song Version (Original Remix)",
            "My Song (with John Doe) Version (Original Remix)": "My Song Version (Original Remix)",
            "My Song (With John Doe) Version (Original Remix)": "My Song Version (Original Remix)",
        }

        for key in songs.keys():
            self.assertEqual(remove_feat(key), songs[key])

    def test_spotify_normalize(self):
        songs = {
            "Pressure - Alesso Radio Edit": "Pressure (Alesso Radio Edit)",
            "Right Now - GATTÜSO Remix": "Right Now (GATTÜSO Remix)",
            "I'm Not Alright - EDX's Dubai Skyline Remix": "I'm Not Alright (EDX's Dubai Skyline Remix)",
            "Body - PBH & Jack Shizzle Remix": "Body (PBH & Jack Shizzle Remix)",
        }

        for key in songs.keys():
            self.assertEqual(normalize_spotify_title(key), songs[key])


if __name__ == "__main__":
    unittest.main()
