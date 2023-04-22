import re

import unidecode

# TODO: Normalize ’ characters to '
# Normalize all " to '


def to_title(string):
    return re.sub(
        r"(\s[\W]*|^[\W]*)([a-z])?",
        lambda m: m.group(1) + safe_title(m.group(2)),
        string,
    )


def safe_title(string):
    return string.title() if string is not None else ""


def force_titlecase(string):
    return safe_title(string.lower().strip())


def normalize_artists(artist_string):
    valid_delimters = [
        ", ",
        " x ",
        " X ",
        " & ",
        " vs ",
        " Vs ",
        " Vs. ",
        " vs. ",
        " ft. ",
        " Ft.",
        " Feat. ",
        " feat. ",
        " featuring ",
        " Featuring ",
        " with ",
        " With ",
    ]

    for delimiter in valid_delimters:
        artist_string = artist_string.replace(delimiter, "; ")

    # Transliterate unicode characters to ASCII
    artist_string = unidecode.unidecode(artist_string)

    return artist_string


def split_artists(artist_string):
    artist_string = normalize_artists(artist_string)
    artists = artist_string.split("; ")
    return artists


def first_artist(artist_string):
    artist_string = normalize_artists(artist_string)
    if "; " in artist_string:
        return artist_string.split("; ")[0].strip()
    else:
        return artist_string.strip()


def normalize_spotify_title(title):
    title = re.sub(r" - (.+ (Remix|Edit|VIP))", r" (\1)", title)
    return title.strip()


def remove_feat(title):
    # title = title.replace("featuring", "feat")
    title = re.sub(r"\([fF](ea)?[tT]\. .+?\)\s*", "", title)
    title = re.sub(r"\([wW]ith .+?\)\s*", "", title)
    return title.strip()


def remove_quoted_text(title):
    title = re.sub(r"(\w+’\w+\s*)", "", title)
    title = re.sub(r"(\w+'\w+\s*)", "", title)
    return title.strip()


def normalize(title):
    # Transliterate unicode characters to ASCII
    title = unidecode.unidecode(title)
    title = normalize_spotify_title(title)
    # title = remove_quoted_text(title)
    title = (
        title.lower()
        .replace("[", "(")  # Only use parentheses
        .replace("]", ")")
        # .replace('"', "'")  # Only use single quotes
        .replace(" - ", " ")  # Some song titles have a dash in them
        # MusicBrainz uses ’ while other apps use '
        # Normalize all title quotes to '
        .replace("’", "'")  # Only use normal quotation marks
        .replace('"', "")  # Remove quotes
        .replace("(original mix)", "")  # Remove original mix
        .replace("(album mix)", "")  # Remove original mix
        .strip()
    )

    # Note that we remove the feat last in case brackets were used
    # instead of parentheses
    return remove_feat(title)
