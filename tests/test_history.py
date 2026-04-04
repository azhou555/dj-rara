import json
import pytest
from pathlib import Path
from dj_rara.models import Playlist

FAKE_PATH = Path("/tmp/dj-rara-test.json")


@pytest.fixture(autouse=True)
def clean_file():
    FAKE_PATH.unlink(missing_ok=True)
    yield
    FAKE_PATH.unlink(missing_ok=True)


@pytest.fixture(autouse=True)
def patch_path(monkeypatch):
    import dj_rara.history as history
    monkeypatch.setattr(history, "HISTORY_PATH", FAKE_PATH)


def test_load_missing_file():
    from dj_rara.history import load_history
    assert load_history() == {"playlists": [], "seen_track_ids": []}


def test_load_valid_file():
    FAKE_PATH.write_text(json.dumps({
        "playlists": [{"id": "p1"}],
        "seen_track_ids": ["t1", "t2"],
    }))
    from dj_rara.history import load_history
    result = load_history()
    assert result["seen_track_ids"] == ["t1", "t2"]


def test_load_corrupt_file():
    FAKE_PATH.write_text("not json{{{")
    from dj_rara.history import load_history
    assert load_history() == {"playlists": [], "seen_track_ids": []}


def test_load_missing_keys():
    FAKE_PATH.write_text(json.dumps({"other": "data"}))
    from dj_rara.history import load_history
    assert load_history() == {"playlists": [], "seen_track_ids": []}


def test_save_and_reload():
    from dj_rara.history import save_history, load_history
    save_history({"playlists": [], "seen_track_ids": ["t1"]})
    assert load_history()["seen_track_ids"] == ["t1"]


def test_add_playlist():
    from dj_rara.history import add_playlist, get_playlists
    pl = Playlist(
        id="p1", name="DJ Rara — chill", url="https://example.com",
        track_count=30, created_at="2026-04-03", mood="chill", genres=["indie"],
    )
    add_playlist(pl)
    playlists = get_playlists()
    assert len(playlists) == 1
    assert playlists[0]["id"] == "p1"
    assert playlists[0]["mood"] == "chill"


def test_add_seen_tracks():
    from dj_rara.history import add_seen_tracks, get_seen_track_ids
    add_seen_tracks(["t1", "t2", "t3"])
    assert get_seen_track_ids() == {"t1", "t2", "t3"}


def test_add_seen_tracks_deduplicates():
    from dj_rara.history import add_seen_tracks, get_seen_track_ids
    add_seen_tracks(["t1", "t2"])
    add_seen_tracks(["t2", "t3"])
    assert get_seen_track_ids() == {"t1", "t2", "t3"}


def test_get_playlists_empty():
    from dj_rara.history import get_playlists
    assert get_playlists() == []
