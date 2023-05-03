from typing import Any


class MBRecording:
    def __init__(self, title: str, length: int, mbid: str):
        self.title = title
        self.length = int(length)
        self.mbid = mbid

    def __repr__(self) -> str:
        return f"Recording: {self.title} [{self.length}] -> {self.mbid}"


class RecordingInfo:
    def __init__(
        self,
        artist: str,
        album: str | None,
        title: str,
        length: int,
        mbid: str,
        rating: int = 0,
    ):
        self.artist = artist
        self.album = album if album else ""
        self.title = title
        self.length = int(length)
        self.mbid = mbid
        self.rating = rating
        self.extra: dict[str, Any] = {}
        self.sources: dict[str, int] = {}  # Key: source, Value: rating

    def valid(self) -> bool:
        return (
            self.artist != ""
            and self.album != ""
            and self.title != ""
            and self.length != 0
            and self.mbid != ""
        )

    def __repr__(self) -> str:
        return f"Recording: {self.title} [{self.length}] -> {self.mbid}"
