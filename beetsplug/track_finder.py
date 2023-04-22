import musicbrainzngs
import unidecode
from beets import dbcore
from thefuzz import fuzz

from .mb_user import log_rate_limited_call
from .normalize import (first_artist, force_titlecase, normalize, remove_feat,
                        remove_quoted_text)
from .recording import MBRecording, RecordingInfo
from .track_cache import MBTrackCache


class LibraryTrackFinder:
    def __init__(self, library, library_only=False, cache: MBTrackCache | None = None):
        self.library = library
        self.library_only = library_only
        self.cache = cache

        # Initialize a single intstance of MBTrackFinder we can reuse for non-library lookups
        self.mb_track_finder = MBTrackFinder(self.cache)

    def findByMBID(self, mbid) -> RecordingInfo | None:
        # Return the cached value if it exists
        if self.cache:
            result = self.cache.getByMBID(mbid)
            if result:
                return result

        query = dbcore.MatchQuery("mb_trackid", mbid)
        songs = self.library.items(query)

        if len(songs) == 1:
            song = songs[0]
            recording = RecordingInfo(
                song.artist,
                song.album,
                song.title,
                round(song.length),
                song.mb_trackid,
            )

            if self.cache:
                self.cache.add(recording)

            return recording

        else:
            return None

    def findByRecording(self, recording: MBRecording) -> RecordingInfo | None:
        result = self.findByMBID(recording.mbid)

        # We couldn't find by MBID, so search by title and length
        if not result:
            result = self.findByTitleLength(recording.title, recording.length)

            # If we got a result without the MBID, make sure we return it with the MBID
            if result and result.mbid != recording.mbid:
                result.mbid = recording.mbid

            # Make sure to recache the result if it was found
            if result and self.cache:
                self.cache.add(result)

        # Return the result which may be None if nothing was found
        return result

    def findByTitleLength(self, title: str, length: int) -> RecordingInfo | None:
        allowed_variance = 3
        length_lower = length - allowed_variance
        length_upper = length + allowed_variance

        andQuery = dbcore.AndQuery(
            [
                dbcore.query.SubstringQuery("title", remove_quoted_text(title)),
                dbcore.query.NumericQuery(
                    "length", "{0}..{1}".format(length_lower, length_upper)
                ),
            ]
        )

        songs = self.library.items(andQuery)

        # Initialize song to None since we have not found a song yet
        song = None
        if len(songs) == 1:
            song = songs.get()
        else:
            for each_song in songs:
                # This was a bad match, skip it
                if fuzz.ratio(each_song["title"], title) < 90:
                    continue

                # Note that song will be None on the first iteration. We want
                # to match with the song with the highest track total
                if not song or each_song.tracktotal > song.tracktotal:
                    song = each_song

        # If we found a song return it as a RecordingInfo object
        return (
            RecordingInfo(
                song["artist"], song["album"], title, length, song["mb_trackid"]
            )
            if song
            else None
        )

    def find(self, artist, title, album=None) -> RecordingInfo | None:
        # Return the cached value if it exists
        if self.cache:
            # Will return None if no match is found
            result = self.cache.get(artist, title, album)

            # Only return the result if we found one, otherwise proceed with the lookup
            if result:
                return result

        songs = []

        normalized_title = normalize(title)
        normalized_artist = first_artist(artist)

        # We want to broaden the search if album and title are the same
        if album and album != title:
            album = normalize(album)

            query = dbcore.AndQuery(
                [
                    dbcore.query.SubstringQuery(
                        "title", remove_quoted_text(normalized_title)
                    ),
                    dbcore.query.SubstringQuery("artist", normalized_artist),
                    dbcore.query.SubstringQuery("album", remove_quoted_text(album)),
                ]
            )
            songs = self.library.items(query)

        # The album was not provided or we searched with the album and got no results
        if not album or len(songs) == 0:
            query = dbcore.AndQuery(
                [
                    dbcore.query.SubstringQuery(
                        "title", remove_quoted_text(normalized_title)
                    ),
                    dbcore.query.SubstringQuery("artist", normalized_artist),
                ]
            )
            songs = self.library.items(query)

        correct_song = None
        for song in songs:
            result_song_title = normalize(song.title)
            fuzz_match_ratio = fuzz.ratio(result_song_title, normalized_title)

            result_remix = "remix" in result_song_title
            actual_remix = "remix" in normalized_title

            # Prefer the song with the highest number of tracks on the album
            # that isn't a remixes album
            if (fuzz_match_ratio > 90 and result_remix == actual_remix) and (
                (correct_song is None)
                or (
                    (song.tracktotal > correct_song.tracktotal)
                    and (
                        "remixes" not in song.album.lower()
                        and "remix" not in song.album.lower()
                    )
                )
            ):
                correct_song = song

        if correct_song:
            has_mbid = correct_song.mb_trackid != ""
            if has_mbid:
                correct_recording = RecordingInfo(
                    correct_song.artist,
                    correct_song.album,
                    correct_song.title,
                    round(correct_song.length),
                    correct_song.mb_trackid,
                )

                # We got a result, store it in the cache
                if self.cache:
                    self.cache.add(correct_recording)

                return correct_recording

            # We don't have an MBID in the library so we need to search MusicBrainz
            elif not self.library_only:
                # Provide the album hint to the track finder so that we get better
                # recording results
                return self.mb_track_finder.find(artist, title, correct_song.album)
            # We can't search MusicBrainz and the id isn't stored in the library
            else:
                return None
        else:
            # This song is not present in the library, find all the info anyway
            if not self.library_only:

                return self.mb_track_finder.find(artist, title, album)
            # If library only is set, then do not fetch anything
            else:
                return None


class MBTrackFinder:
    def __init__(self, cache: MBTrackCache | None = None):
        self.cache = cache

    def findByMBID(self, mbid) -> RecordingInfo | None:
        # Return the cached value if it exists
        if self.cache:
            result = self.cache.getByMBID(mbid)
            if result:
                return result

        log_rate_limited_call("get_recording_by_id")
        recordings = musicbrainzngs.get_recording_by_id(
            mbid, includes=["artists", "releases"]
        )

        if len(recordings) == 1:
            recording = recordings["recording"]
            artist = force_titlecase(recording["artist-credit"][0]["artist"]["name"])
            album = recording["release-list"][0]["title"]
            title = recording["title"]

            # Load the length information if available
            if "length" in recording:
                length = int(recording["length"]) / 1000
                length = round(length)
            else:
                length = 0

            rec_info = RecordingInfo(artist, album, title, length, mbid)

            # We got a result, store it in the cache
            if self.cache:
                self.cache.add(rec_info)

            return rec_info
        else:
            return None

    def find(self, artist, title, album=None) -> RecordingInfo | None:
        # Return the cached value if it exists
        if self.cache:
            # Will return None if no match is found
            result = self.cache.get(artist, title, album)

            if result:
                return result

        # If album is None we just use the title
        album = title if not album else album
        track = None
        print("Searching for %s - %s " % (artist, title), end="")

        # Normalize the strings
        title = normalize(title)
        artist = unidecode.unidecode(artist)

        search_args = {
            "artist": artist.lower().strip(),
            "release": album.lower().strip(),
        }

        track = self.mb_search_releases(search_args, title)

        # We didn't get a result searching by album, but album and title are
        # different so try just searching with the title
        if not track and album != title:
            search_args["release"] = title.lower().strip()
            track = self.mb_search_releases(search_args, title)

        # We still haven't found a track, try a recording search
        if not track:
            track = self.mb_search_recordings(search_args, title)

        # We got a result, store it in the cache
        if track and self.cache:
            self.cache.add(track)

        return track

    def mb_search_recordings(
        self, search_args, title: str, use_strict: bool = True
    ) -> RecordingInfo | None:
        primary_artist = first_artist(search_args["artist"])
        normalized_title = normalize(title)

        # If we're searching for a recording, passing in a release
        # tends to mess up the results. Search based on the title and
        # artist only.
        if "release" in search_args:
            del search_args["release"]

        log_rate_limited_call("search_recordings")
        results = musicbrainzngs.search_recordings(
            query=normalized_title, limit=10, strict=use_strict, **search_args
        )

        # If there aren't any results, try again without strict
        # If this wasn't strict then we won't find anything
        if not results:
            return (
                None
                if not use_strict
                else self.mb_search_recordings(search_args, title, False)
            )

        recordings = results["recording-list"]

        def get_num_releases(recording):
            return len(recording["release-list"])

        # Filter out all the recordings where primary_artist.lower()
        # is not in the artist-credit-phrase
        recordings = [
            rec
            for rec in recordings
            if primary_artist.lower().strip()
            in rec["artist-credit-phrase"].lower().strip()
        ]

        # Sort the recordings by the number of releases they are on
        # Thought process: if a recording is the most releases, it's probably
        # the best possible result
        recordings.sort(key=get_num_releases, reverse=True)

        for recording in recordings:
            candidate_title = recording["title"].lower().strip()
            candidate_title = remove_feat(candidate_title)

            extended_candidate = "extended" in candidate_title
            extended_actual = "extended" in normalized_title

            # Check to see if the title is a fuzzy match
            if fuzz.ratio(candidate_title, normalized_title) > 90 and (
                extended_actual == extended_candidate
            ):

                def find_artist_release(releases):
                    for release in releases:
                        if (
                            (
                                primary_artist.lower()
                                in release["artist-credit-phrase"].lower()
                            )
                            # Release medium must be digital media or CD
                            and (
                                release["medium-list"][0]["format"] == "Digital Media"
                                or release["medium-list"][0]["format"] == "CD"
                            )
                        ):
                            return release
                    return None

                # We have to find a specific release by this artist
                # This may not work for compilaton albums
                release = find_artist_release(recording["release-list"])

                # We didn't find a valid release, keep searching
                if not release:
                    continue

                # Load the length information if available
                if "length" in recording:
                    length = int(recording["length"]) / 1000
                    length = round(length)
                else:
                    length = 0

                print("(%s,%s)" % (recording["id"], length))
                return RecordingInfo(
                    recording["artist-credit-phrase"],
                    release["title"],
                    recording["title"],
                    length,
                    recording["id"],
                )

        # If we didn't find a result, try again without strict
        if use_strict:
            return self.mb_search_releases(search_args, title, False)

        return None

    def mb_search_releases(
        self, search_args, title: str, use_strict: bool = True
    ) -> RecordingInfo | None:
        artist = search_args["artist"].replace(" & ", "; ")
        artist = artist.replace(", ", "; ")
        artists = artist.split("; ")
        title = title.lower().strip()

        # Make sure that release is present
        if "release" not in search_args:
            search_args["release"] = title.lower().strip()

        search_args["release"] = remove_feat(search_args["release"])

        log_rate_limited_call("search_release_groups")
        results = musicbrainzngs.search_release_groups(
            limit=10, **search_args, strict=use_strict
        )

        # Sort the releases by type so that we search albums first,
        # then EPs, then singles
        release_group_results = results["release-group-list"]
        release_group_results = sorted(
            release_group_results, key=lambda k: k.get("type", "Unknown")
        )
        rg_count = len(release_group_results)

        if rg_count == 0 and use_strict:
            return self.mb_search_releases(search_args, title, False)

        for release_group in release_group_results:
            release_results = release_group["release-list"]

            for release_result in release_results:
                release_id = release_result["id"]

                log_rate_limited_call("get_release_by_id")
                release = musicbrainzngs.get_release_by_id(
                    release_id, includes=["recordings", "artists"]
                )

                try:
                    track_list = release["release"]["medium-list"][0]["track-list"]
                    medium = release["release"]["medium-list"][0]["format"]

                    # Ignore mediums such as vinyl.
                    # We only want digital files or files from CDs
                    if medium not in ["Digital Media", "CD"]:
                        continue

                    artist_credit = (
                        release["release"]["artist-credit-phrase"].lower().strip()
                    )
                # If the medium or track list is missing, just skip this iteration
                except (KeyError, IndexError):
                    continue

                # If artist is not on this release, skip it because it's wrong
                # correct_artist = any(artist in artist_credit for artist in artists)
                if not artists[0].lower().strip() in artist_credit:
                    continue

                # This release group is a remix release group but we aren't searching for a remix
                if (
                    "remix" in release["release"]["title"].lower()
                    or "remixes" in release["release"]["title"].lower()
                ) and "remix" not in title:
                    continue

                for track in track_list:
                    candidate_title = track["recording"]["title"].lower().strip()
                    candidate_title_no_feat = remove_feat(candidate_title)
                    title_no_feat = remove_feat(title)

                    extended_candidate = "extended" in candidate_title_no_feat
                    extended_actual = "extended" in title_no_feat

                    # Check to see if the title is a fuzzy match
                    if fuzz.ratio(candidate_title_no_feat, title_no_feat) > 90 and (
                        extended_actual == extended_candidate
                    ):
                        # Load the length information if available
                        if "length" in track["recording"]:
                            length = int(track["recording"]["length"]) / 1000
                            length = round(length)
                        else:
                            length = 0

                        print("(%s,%s)" % (track["recording"]["id"], length))
                        return RecordingInfo(
                            release["release"]["artist-credit-phrase"],
                            release["release"]["title"],
                            track["recording"]["title"],
                            length,
                            track["recording"]["id"],
                        )

        # Try a non-strict search if we didn't find anything
        return (
            self.mb_search_releases(search_args, title, False) if use_strict else None
        )
