from logging import getLogger

import beets.library
from beets import dbcore
from thefuzz import fuzz

from .normalize import first_artist
from .recording import RecordingInfo


class RecordingMatcher:
    def __init__(self, lib, logger):
        self.lib = lib
        self.logger = logger if logger else getLogger("beets")

    def match(self, recording: RecordingInfo) -> beets.library.Item | None:
        """Finds a matching song in the library based on a recording object"""
        song = None
        songs = self.lib.items(dbcore.query.MatchQuery("mb_trackid", recording.mbid))

        if len(songs) == 1:
            song = songs.get()
        else:
            for each_song in songs:
                # Note that song will be None on the first iteration. We want
                # to match with the song with the highest track total
                if not song or (
                    (each_song.tracktotal > song.tracktotal)
                    # We don't prefer remix releases. If it's the only release
                    # it will be chosen on the first iteration because song was None
                    and (
                        "remixes" not in each_song.album.lower()
                        and "remix" not in each_song.album.lower()
                    )
                ):
                    song = each_song

        if song is None:
            # self._log.debug(
            #     "Unable to find track by MBID, searching title: {0}",
            #     recording.title,
            # )
            # Allow for a difference in lengths by +- 3 seconds
            length_lower = round(recording.length) - 3
            length_upper = round(recording.length) + 3

            andQuery = dbcore.AndQuery(
                [
                    dbcore.query.SubstringQuery("title", recording.title),
                    dbcore.query.NumericQuery(
                        "length", f"{length_lower}..{length_upper}"
                    ),
                ]
            )

            songs = self.lib.items(andQuery)

            if len(songs) == 1:
                song = songs.get()
            else:
                for each_song in songs:
                    # We might get the a collision if the track title is in the track
                    # title of another song and the song lengths are similar. Double
                    # check that the artist is correct and that the title is
                    # reasonably close
                    if (
                        recording.artist
                        and first_artist(recording.artist) not in each_song["artist"]
                    ) or fuzz.ratio(each_song["title"], recording.title) < 90:
                        continue

                    # Note that song will be None on the first iteration. We want
                    # to match with the song with the highest track total
                    if not song or each_song.tracktotal > song.tracktotal:
                        song = each_song

                        self.logger.info(
                            "RecordingMatcher: Matched song --"
                            f"{song['title']} to {recording.title}"
                        )

        if not song:
            self.logger.info(
                f"RecordingMatcher: Unable to match song {recording.title}"
            )

        return song
