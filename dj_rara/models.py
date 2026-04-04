from dataclasses import dataclass


@dataclass
class Track:
    id: str
    name: str
    artists: list[str]
    album: str
    popularity: int
    preview_url: str | None
    uri: str


@dataclass
class Artist:
    id: str
    name: str
    genres: list[str]
    popularity: int


@dataclass
class Playlist:
    id: str
    name: str
    url: str
    track_count: int
    created_at: str
    mood: str
    genres: list[str]
