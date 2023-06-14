import math

import musicbrainzngs


def star_to_hundred_rating(rating: int):
    """
    Convert star rating from (0 to 5) to (0 to 100)
    """
    rating = 0 if rating < 0 else rating
    rating = 5 if rating > 5 else rating

    return math.floor(rating * 20)


def add_recordings_to_collection(collection, recordings_to_add=[]):
    # We don't need to do anything
    if len(recordings_to_add) == 0:
        return

    if len(recordings_to_add) >= 50:
        first_part = recordings_to_add[:50]
        assert len(first_part) == 50
        second_part = recordings_to_add[50:]
        assert len(first_part) + len(second_part) == len(recordings_to_add)

        recording_list = ";".join(first_part)

        musicbrainzngs.musicbrainz._do_mb_put(  # type: ignore
            "collection/%s/recordings/%s" % (collection, recording_list)
        )
        return add_recordings_to_collection(collection, second_part)

    recording_list = ";".join(recordings_to_add)
    return musicbrainzngs.musicbrainz._do_mb_put(  # type: ignore
        "collection/%s/recordings/%s" % (collection, recording_list)
    )


def remove_recordings_from_collection(collection, recordings_to_add=[]):
    # We don't need to do anything
    if len(recordings_to_add) == 0:
        return

    # TODO: Break the array into chunks if it's greater than size 400
    if len(recordings_to_add) >= 400:
        raise ValueError("Cannot remove more than 400 recordings at a time.")

    recording_list = ";".join(recordings_to_add)
    return musicbrainzngs.musicbrainz._do_mb_delete(  # type: ignore
        "collection/%s/recordings/%s" % (collection, recording_list)
    )
