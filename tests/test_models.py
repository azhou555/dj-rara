from dataclasses import asdict
from models import Artist, Playlist, Track


def test_track_creation():
    track = Track(
        id="t1",
        name="Skinny Love",
        artists=["Bon Iver"],
        album="For Emma, Forever Ago",
        popularity=91,
        preview_url="https://example.com/preview.mp3",
        uri="spotify:track:t1",
    )
    assert track.id == "t1"
    assert track.name == "Skinny Love"
    assert track.artists == ["Bon Iver"]
    assert track.popularity == 91
    assert track.preview_url == "https://example.com/preview.mp3"


def test_track_no_preview():
    track = Track(
        id="t2", name="Holocene", artists=["Bon Iver"],
        album="Bon Iver, Bon Iver", popularity=88,
        preview_url=None, uri="spotify:track:t2",
    )
    assert track.preview_url is None


def test_artist_creation():
    artist = Artist(
        id="a1", name="Bon Iver",
        genres=["indie folk", "folk rock"], popularity=80,
    )
    assert artist.genres == ["indie folk", "folk rock"]


def test_playlist_creation():
    playlist = Playlist(
        id="p1", name="DJ Rara — chill · indie",
        url="https://open.spotify.com/playlist/p1",
        track_count=28, created_at="2026-04-03",
        mood="chill", genres=["indie", "folk"],
    )
    assert playlist.mood == "chill"
    assert playlist.genres == ["indie", "folk"]


def test_track_serializable():
    track = Track(
        id="t1", name="Test", artists=["Artist"], album="Album",
        popularity=50, preview_url=None, uri="spotify:track:t1",
    )
    data = asdict(track)
    assert data["id"] == "t1"
    assert data["preview_url"] is None


def test_playlist_serializable():
    playlist = Playlist(
        id="p1", name="Test", url="https://example.com",
        track_count=10, created_at="2026-04-03",
        mood="chill", genres=["indie"],
    )
    data = asdict(playlist)
    assert data["mood"] == "chill"
    assert data["genres"] == ["indie"]
