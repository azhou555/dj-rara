# DJ Rara TUI Rewrite — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite DJ Rara as a full-screen interactive Textual TUI with mood-based personalized recommendations, track curation, Music DNA stats, and playlist management.

**Architecture:** Multi-screen Textual app — MoodScreen (home) → RecommendationsScreen (pushed), with StatsScreen and PlaylistManagerScreen reachable from any screen via keybinding. `SpotifyClient` wraps all spotipy calls and returns typed dataclasses. History persisted to `~/.dj-rara.json`.

**Tech Stack:** Python 3.9+, `textual>=0.50.0`, `spotipy==2.23.0`, `python-dotenv==1.0.0`, `pytest`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `models.py` | Create | `Track`, `Artist`, `Playlist` dataclasses |
| `history.py` | Create | Read/write `~/.dj-rara.json` |
| `spotify_client.py` | Create | All Spotify API calls, mood mapping, returns model objects |
| `app.py` | Create | `DJRaraApp(App)` — holds client, CSS theme, screen routing |
| `main.py` | Rewrite | Credential check, auth, launch app |
| `screens/__init__.py` | Create | Empty package marker |
| `screens/mood.py` | Create | `MoodScreen` — mood/genre/time/count/discover |
| `screens/recommendations.py` | Create | `RecommendationsScreen` — track table, keep/skip, preview, playlist |
| `screens/stats.py` | Create | `StatsScreen` — genre bars, audio features, top artists |
| `screens/playlists.py` | Create | `PlaylistManagerScreen` — past playlists, open in Spotify |
| `tests/__init__.py` | Create | Empty |
| `tests/conftest.py` | Create | Shared `mock_sp` fixture |
| `tests/test_models.py` | Create | Unit tests for `models.py` |
| `tests/test_history.py` | Create | Unit tests for `history.py` |
| `tests/test_spotify_client.py` | Create | Unit tests for `spotify_client.py` |
| `requirements.txt` | Modify | Add `textual>=0.50.0`, `pytest` |
| `recommendation_engine.py` | Delete | Replaced by `spotify_client.py` |
| `diagnose.py`, `debug_data.py`, `test_auth.py` | Delete | Debug files from initial implementation |

---

## Task 1: Project Scaffolding

**Files:**
- Modify: `requirements.txt`
- Create: `screens/__init__.py`, `tests/__init__.py`, `tests/conftest.py`

- [ ] **Step 1: Update `requirements.txt`**

Replace contents with:

```
spotipy==2.23.0
python-dotenv==1.0.0
textual>=0.50.0
pytest
```

- [ ] **Step 2: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: All packages install without errors. Verify: `python -c "import textual; print(textual.__version__)"` prints a version number.

- [ ] **Step 3: Create directories and empty init files**

```bash
mkdir -p screens tests
touch screens/__init__.py tests/__init__.py
```

- [ ] **Step 4: Create `tests/conftest.py`**

```python
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_sp():
    sp = MagicMock()
    sp.current_user.return_value = {"id": "testuser", "display_name": "Test User"}
    return sp
```

- [ ] **Step 5: Verify test discovery**

```bash
pytest tests/ -v
```

Expected: `no tests ran` — no errors, just empty collection.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt screens/__init__.py tests/__init__.py tests/conftest.py
git commit -m "chore: scaffolding for TUI rewrite — directories, deps, test config"
```

---

## Task 2: Data Models

**Files:**
- Create: `models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_models.py`:

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_models.py -v
```

Expected: `ModuleNotFoundError: No module named 'models'`

- [ ] **Step 3: Implement `models.py`**

```python
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
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_models.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add models.py tests/test_models.py
git commit -m "feat: add Track, Artist, Playlist dataclasses"
```

---

## Task 3: History Module

**Files:**
- Create: `history.py`
- Create: `tests/test_history.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_history.py`:

```python
import json
import pytest
from pathlib import Path
from models import Playlist

FAKE_PATH = Path("/tmp/dj-rara-test.json")


@pytest.fixture(autouse=True)
def clean_file():
    FAKE_PATH.unlink(missing_ok=True)
    yield
    FAKE_PATH.unlink(missing_ok=True)


@pytest.fixture(autouse=True)
def patch_path(monkeypatch):
    import history
    monkeypatch.setattr(history, "HISTORY_PATH", FAKE_PATH)


def test_load_missing_file():
    from history import load_history
    assert load_history() == {"playlists": [], "seen_track_ids": []}


def test_load_valid_file():
    FAKE_PATH.write_text(json.dumps({
        "playlists": [{"id": "p1"}],
        "seen_track_ids": ["t1", "t2"],
    }))
    from history import load_history
    result = load_history()
    assert result["seen_track_ids"] == ["t1", "t2"]


def test_load_corrupt_file():
    FAKE_PATH.write_text("not json{{{")
    from history import load_history
    assert load_history() == {"playlists": [], "seen_track_ids": []}


def test_load_missing_keys():
    FAKE_PATH.write_text(json.dumps({"other": "data"}))
    from history import load_history
    assert load_history() == {"playlists": [], "seen_track_ids": []}


def test_save_and_reload():
    from history import save_history, load_history
    save_history({"playlists": [], "seen_track_ids": ["t1"]})
    assert load_history()["seen_track_ids"] == ["t1"]


def test_add_playlist():
    from history import add_playlist, get_playlists
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
    from history import add_seen_tracks, get_seen_track_ids
    add_seen_tracks(["t1", "t2", "t3"])
    assert get_seen_track_ids() == {"t1", "t2", "t3"}


def test_add_seen_tracks_deduplicates():
    from history import add_seen_tracks, get_seen_track_ids
    add_seen_tracks(["t1", "t2"])
    add_seen_tracks(["t2", "t3"])
    assert get_seen_track_ids() == {"t1", "t2", "t3"}


def test_get_playlists_empty():
    from history import get_playlists
    assert get_playlists() == []
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_history.py -v
```

Expected: `ModuleNotFoundError: No module named 'history'`

- [ ] **Step 3: Implement `history.py`**

```python
import json
from dataclasses import asdict
from pathlib import Path

from models import Playlist

HISTORY_PATH = Path.home() / ".dj-rara.json"


def load_history() -> dict:
    try:
        data = json.loads(HISTORY_PATH.read_text())
        if "playlists" not in data or "seen_track_ids" not in data:
            raise ValueError("missing keys")
        return data
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return {"playlists": [], "seen_track_ids": []}


def save_history(history: dict) -> None:
    HISTORY_PATH.write_text(json.dumps(history, indent=2))


def add_playlist(playlist: Playlist) -> None:
    history = load_history()
    history["playlists"].insert(0, asdict(playlist))
    save_history(history)


def add_seen_tracks(track_ids: list[str]) -> None:
    history = load_history()
    seen = set(history["seen_track_ids"])
    seen.update(track_ids)
    history["seen_track_ids"] = list(seen)
    save_history(history)


def get_seen_track_ids() -> set[str]:
    return set(load_history()["seen_track_ids"])


def get_playlists() -> list[dict]:
    return load_history()["playlists"]
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_history.py -v
```

Expected: All 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add history.py tests/test_history.py
git commit -m "feat: add history persistence module"
```

---

## Task 4: SpotifyClient — Data Fetching

**Files:**
- Create: `spotify_client.py` (partial — data fetching methods)
- Create: `tests/test_spotify_client.py` (partial)

- [ ] **Step 1: Write failing tests**

Create `tests/test_spotify_client.py`:

```python
import pytest
from unittest.mock import MagicMock
from models import Track, Artist


@pytest.fixture
def mock_sp():
    sp = MagicMock()
    sp.current_user.return_value = {"id": "testuser", "display_name": "Test User"}
    return sp


@pytest.fixture
def client(mock_sp):
    from spotify_client import SpotifyClient
    return SpotifyClient(mock_sp)


def _raw_track(id="t1", name="Skinny Love", artist="Bon Iver",
               album="For Emma", popularity=91, preview_url="https://example.com/p.mp3"):
    return {
        "id": id, "name": name,
        "artists": [{"name": artist}],
        "album": {"name": album},
        "popularity": popularity,
        "preview_url": preview_url,
        "uri": f"spotify:track:{id}",
    }


def _raw_artist(id="a1", name="Bon Iver", genres=None, popularity=80):
    return {
        "id": id, "name": name,
        "genres": genres or ["indie folk", "folk rock"],
        "popularity": popularity,
    }


class TestGetTopTracks:
    def test_returns_track_objects(self, client, mock_sp):
        mock_sp.current_user_top_tracks.return_value = {"items": [_raw_track()]}
        tracks = client.get_top_tracks(time_range="medium_term", limit=1)
        assert len(tracks) == 1
        assert isinstance(tracks[0], Track)
        assert tracks[0].name == "Skinny Love"
        assert tracks[0].artists == ["Bon Iver"]

    def test_none_preview_url_preserved(self, client, mock_sp):
        mock_sp.current_user_top_tracks.return_value = {
            "items": [_raw_track(preview_url=None)]
        }
        tracks = client.get_top_tracks(time_range="medium_term", limit=1)
        assert tracks[0].preview_url is None

    def test_passes_time_range(self, client, mock_sp):
        mock_sp.current_user_top_tracks.return_value = {"items": []}
        client.get_top_tracks(time_range="short_term", limit=10)
        mock_sp.current_user_top_tracks.assert_called_once_with(
            limit=10, offset=0, time_range="short_term"
        )


class TestGetTopArtists:
    def test_returns_artist_objects(self, client, mock_sp):
        mock_sp.current_user_top_artists.return_value = {"items": [_raw_artist()]}
        artists = client.get_top_artists(time_range="medium_term", limit=1)
        assert len(artists) == 1
        assert isinstance(artists[0], Artist)
        assert artists[0].genres == ["indie folk", "folk rock"]

    def test_passes_time_range(self, client, mock_sp):
        mock_sp.current_user_top_artists.return_value = {"items": []}
        client.get_top_artists(time_range="long_term", limit=5)
        mock_sp.current_user_top_artists.assert_called_once_with(
            limit=5, offset=0, time_range="long_term"
        )


class TestGetFollowedArtists:
    def test_returns_artist_objects(self, client, mock_sp):
        mock_sp.current_user_followed_artists.return_value = {
            "artists": {"items": [_raw_artist()], "next": None}
        }
        artists = client.get_followed_artists(limit=1)
        assert len(artists) == 1
        assert isinstance(artists[0], Artist)

    def test_paginates(self, client, mock_sp):
        page1 = {"artists": {"items": [_raw_artist(id="a1")], "next": "url"}}
        page2 = {"artists": {"items": [_raw_artist(id="a2")], "next": None}}
        mock_sp.current_user_followed_artists.return_value = page1
        mock_sp.next.return_value = page2
        artists = client.get_followed_artists(limit=50)
        assert len(artists) == 2


class TestGetAudioFeatures:
    def test_returns_keyed_dict(self, client, mock_sp):
        mock_sp.audio_features.return_value = [
            {"id": "t1", "energy": 0.4, "valence": 0.6,
             "danceability": 0.5, "acousticness": 0.7, "tempo": 85.0}
        ]
        features = client.get_audio_features(["t1"])
        assert "t1" in features
        assert features["t1"]["energy"] == pytest.approx(0.4)

    def test_empty_list_skips_api(self, client, mock_sp):
        features = client.get_audio_features([])
        assert features == {}
        mock_sp.audio_features.assert_not_called()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_spotify_client.py -v
```

Expected: `ModuleNotFoundError: No module named 'spotify_client'`

- [ ] **Step 3: Implement `spotify_client.py` with data fetching methods**

```python
import random
import time
from datetime import date

import spotipy

from history import get_seen_track_ids
from models import Artist, Playlist, Track

MOOD_FEATURES: dict[str, dict[str, float]] = {
    "chill":      {"target_energy": 0.30, "target_valence": 0.60,
                   "target_tempo": 90.0,  "target_acousticness": 0.70},
    "energetic":  {"target_energy": 0.85, "target_valence": 0.75,
                   "target_tempo": 140.0, "target_acousticness": 0.10},
    "focus":      {"target_energy": 0.50, "target_valence": 0.40,
                   "target_tempo": 110.0, "target_acousticness": 0.50},
    "melancholy": {"target_energy": 0.25, "target_valence": 0.20,
                   "target_tempo": 80.0,  "target_acousticness": 0.60},
}


def mood_to_features(mood: str) -> dict[str, float]:
    if mood not in MOOD_FEATURES:
        raise ValueError(f"Unknown mood: {mood!r}. Choose from {list(MOOD_FEATURES)}")
    return MOOD_FEATURES[mood].copy()


def _parse_track(raw: dict) -> Track:
    return Track(
        id=raw["id"],
        name=raw["name"],
        artists=[a["name"] for a in raw["artists"]],
        album=raw["album"]["name"],
        popularity=raw["popularity"],
        preview_url=raw.get("preview_url"),
        uri=raw["uri"],
    )


def _parse_artist(raw: dict) -> Artist:
    return Artist(
        id=raw["id"],
        name=raw["name"],
        genres=raw.get("genres", []),
        popularity=raw.get("popularity", 0),
    )


def _call_with_retry(fn, max_retries: int = 3):
    """Call fn(), retrying on HTTP 429 rate limit with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return fn()
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 429 and attempt < max_retries - 1:
                wait = int(e.headers.get("Retry-After", 2 ** attempt))
                time.sleep(wait)
            else:
                raise
        except Exception:
            raise


class SpotifyClient:
    def __init__(self, sp):
        self.sp = sp
        self.user_id: str = sp.current_user()["id"]

    def get_top_tracks(self, time_range: str = "medium_term", limit: int = 50) -> list[Track]:
        results = _call_with_retry(
            lambda: self.sp.current_user_top_tracks(
                limit=min(limit, 50), offset=0, time_range=time_range
            )
        )
        return [_parse_track(t) for t in results["items"]][:limit]

    def get_top_artists(self, time_range: str = "medium_term", limit: int = 50) -> list[Artist]:
        results = _call_with_retry(
            lambda: self.sp.current_user_top_artists(
                limit=min(limit, 50), offset=0, time_range=time_range
            )
        )
        return [_parse_artist(a) for a in results["items"]][:limit]

    def get_followed_artists(self, limit: int = 50) -> list[Artist]:
        artists: list[Artist] = []
        results = _call_with_retry(
            lambda: self.sp.current_user_followed_artists(limit=min(limit, 50))
        )
        while results and len(artists) < limit:
            artists.extend([_parse_artist(a) for a in results["artists"]["items"]])
            if results["artists"]["next"] and len(artists) < limit:
                results = _call_with_retry(lambda: self.sp.next(results["artists"]))
            else:
                break
        return artists[:limit]

    def get_audio_features(self, track_ids: list[str]) -> dict[str, dict]:
        if not track_ids:
            return {}
        raw = _call_with_retry(lambda: self.sp.audio_features(track_ids))
        return {f["id"]: f for f in raw if f is not None}
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_spotify_client.py -v
```

Expected: All 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add spotify_client.py tests/test_spotify_client.py
git commit -m "feat: add SpotifyClient with data fetching and rate-limit retry"
```

---

## Task 5: SpotifyClient — Recommendations & Playlists

**Files:**
- Modify: `spotify_client.py` (add 3 methods)
- Modify: `tests/test_spotify_client.py` (add test classes)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_spotify_client.py`:

```python
class TestMoodToFeatures:
    def test_chill(self):
        from spotify_client import mood_to_features
        f = mood_to_features("chill")
        assert f["target_energy"] == pytest.approx(0.30)
        assert f["target_valence"] == pytest.approx(0.60)
        assert f["target_acousticness"] == pytest.approx(0.70)

    def test_energetic(self):
        from spotify_client import mood_to_features
        assert mood_to_features("energetic")["target_energy"] == pytest.approx(0.85)

    def test_focus(self):
        from spotify_client import mood_to_features
        assert mood_to_features("focus")["target_energy"] == pytest.approx(0.50)

    def test_melancholy(self):
        from spotify_client import mood_to_features
        assert mood_to_features("melancholy")["target_energy"] == pytest.approx(0.25)

    def test_unknown_mood_raises(self):
        from spotify_client import mood_to_features
        with pytest.raises(ValueError, match="Unknown mood"):
            mood_to_features("groovy")


class TestGetRecommendations:
    def test_returns_track_objects(self, client, mock_sp):
        mock_sp.recommendations.return_value = {"tracks": [_raw_track(id="r1")]}
        tracks = client.get_recommendations(
            seed_artist_ids=["a1", "a2"],
            seed_track_ids=["t1"],
            mood="chill",
            genres=[],
            limit=10,
        )
        assert len(tracks) >= 1
        assert isinstance(tracks[0], Track)

    def test_passes_mood_audio_features(self, client, mock_sp):
        mock_sp.recommendations.return_value = {"tracks": [_raw_track()]}
        client.get_recommendations(
            seed_artist_ids=["a1"], seed_track_ids=[],
            mood="chill", genres=[], limit=5,
        )
        kwargs = mock_sp.recommendations.call_args[1]
        assert kwargs["target_energy"] == pytest.approx(0.30)
        assert kwargs["target_valence"] == pytest.approx(0.60)

    def test_includes_genre_seeds_when_provided(self, client, mock_sp):
        mock_sp.recommendations.return_value = {"tracks": [_raw_track()]}
        client.get_recommendations(
            seed_artist_ids=["a1", "a2"], seed_track_ids=[],
            mood="chill", genres=["indie folk"], limit=5,
        )
        kwargs = mock_sp.recommendations.call_args[1]
        assert "seed_genres" in kwargs
        assert "indie folk" in kwargs["seed_genres"]

    def test_deduplicates_results(self, client, mock_sp):
        dup = _raw_track(id="dup")
        mock_sp.recommendations.return_value = {"tracks": [dup, dup]}
        tracks = client.get_recommendations(
            seed_artist_ids=["a1"], seed_track_ids=[],
            mood="chill", genres=[], limit=10,
        )
        ids = [t.id for t in tracks]
        assert len(ids) == len(set(ids))


class TestCreatePlaylist:
    def test_returns_playlist_object(self, client, mock_sp):
        mock_sp.user_playlist_create.return_value = {
            "id": "p1", "name": "DJ Rara — chill",
            "external_urls": {"spotify": "https://open.spotify.com/playlist/p1"},
        }
        tracks = [Track("t1", "Song", ["Artist"], "Album", 80, None, "spotify:track:t1")]
        playlist = client.create_playlist(
            name="DJ Rara — chill", tracks=tracks,
            description="test", mood="chill", genres=["indie"],
        )
        assert isinstance(playlist, Playlist)
        assert playlist.id == "p1"
        assert playlist.mood == "chill"
        assert playlist.genres == ["indie"]

    def test_adds_tracks_to_playlist(self, client, mock_sp):
        mock_sp.user_playlist_create.return_value = {
            "id": "p1", "name": "Test",
            "external_urls": {"spotify": "https://example.com"},
        }
        tracks = [
            Track(f"t{i}", "Song", ["Artist"], "Album", 80, None, f"spotify:track:t{i}")
            for i in range(3)
        ]
        client.create_playlist("Test", tracks, "desc", "chill", [])
        mock_sp.playlist_add_items.assert_called_once_with(
            "p1", [f"spotify:track:t{i}" for i in range(3)]
        )


class TestGetUserPlaylists:
    def test_filters_by_prefix(self, client, mock_sp):
        mock_sp.current_user_playlists.return_value = {
            "items": [
                {"id": "p1", "name": "DJ Rara — chill", "tracks": {"total": 28},
                 "external_urls": {"spotify": "https://open.spotify.com/playlist/p1"}},
                {"id": "p2", "name": "My Morning Mix", "tracks": {"total": 10},
                 "external_urls": {"spotify": "https://example.com"}},
            ],
            "next": None,
        }
        playlists = client.get_user_playlists(name_prefix="DJ Rara")
        assert len(playlists) == 1
        assert playlists[0].id == "p1"

    def test_returns_empty_when_none_match(self, client, mock_sp):
        mock_sp.current_user_playlists.return_value = {
            "items": [
                {"id": "p1", "name": "Some Other Playlist", "tracks": {"total": 5},
                 "external_urls": {"spotify": "https://example.com"}},
            ],
            "next": None,
        }
        assert client.get_user_playlists(name_prefix="DJ Rara") == []
```

- [ ] **Step 2: Run new tests to confirm they fail**

```bash
pytest tests/test_spotify_client.py::TestMoodToFeatures tests/test_spotify_client.py::TestGetRecommendations tests/test_spotify_client.py::TestCreatePlaylist tests/test_spotify_client.py::TestGetUserPlaylists -v
```

Expected: `AttributeError` — methods don't exist yet.

- [ ] **Step 3: Add remaining methods to `SpotifyClient` in `spotify_client.py`**

Add these three methods inside the `SpotifyClient` class (after `get_audio_features`):

```python
    def get_recommendations(
        self,
        seed_artist_ids: list[str],
        seed_track_ids: list[str],
        mood: str,
        genres: list[str],
        limit: int = 30,
    ) -> list[Track]:
        features = mood_to_features(mood)
        seen_ids = get_seen_track_ids()
        results: list[Track] = []
        seen_in_session: set[str] = set()

        artists = list(seed_artist_ids)
        tracks_pool = list(seed_track_ids)
        random.shuffle(artists)
        random.shuffle(tracks_pool)

        # Reserve 1 genre seed slot if genres provided; rest split between artists/tracks
        genre_seeds = genres[:1] if genres else []
        remaining = 5 - len(genre_seeds)
        max_artists = min(3, remaining, len(artists))
        max_tracks = min(remaining - max_artists, len(tracks_pool))

        iterations = max((limit // 50) + 2, 3)

        for i in range(iterations):
            if len(results) >= limit:
                break

            a_start = (i * max(max_artists, 1)) % max(len(artists), 1)
            t_start = (i * max(max_tracks, 1)) % max(len(tracks_pool), 1)

            batch_artists = artists[a_start : a_start + max_artists]
            batch_tracks = tracks_pool[t_start : t_start + max_tracks]

            if not batch_artists and not batch_tracks and not genre_seeds:
                break

            params: dict = {"limit": min(100, limit), **features}
            if batch_artists:
                params["seed_artists"] = batch_artists
            if batch_tracks:
                params["seed_tracks"] = batch_tracks
            if genre_seeds:
                params["seed_genres"] = genre_seeds

            try:
                raw = _call_with_retry(lambda: self.sp.recommendations(**params))
            except Exception:
                continue

            for item in raw["tracks"]:
                tid = item["id"]
                if tid not in seen_ids and tid not in seen_in_session:
                    results.append(_parse_track(item))
                    seen_in_session.add(tid)

        return results[:limit]

    def create_playlist(
        self,
        name: str,
        tracks: list[Track],
        description: str,
        mood: str,
        genres: list[str],
        public: bool = False,
    ) -> Playlist:
        raw = _call_with_retry(
            lambda: self.sp.user_playlist_create(
                user=self.user_id, name=name, public=public, description=description
            )
        )
        track_uris = [t.uri for t in tracks]
        for i in range(0, len(track_uris), 100):
            _call_with_retry(
                lambda batch=track_uris[i : i + 100]: self.sp.playlist_add_items(raw["id"], batch)
            )
        return Playlist(
            id=raw["id"],
            name=name,
            url=raw["external_urls"]["spotify"],
            track_count=len(tracks),
            created_at=date.today().isoformat(),
            mood=mood,
            genres=genres,
        )

    def get_user_playlists(self, name_prefix: str = "DJ Rara") -> list[Playlist]:
        playlists: list[Playlist] = []
        results = _call_with_retry(lambda: self.sp.current_user_playlists(limit=50))
        while results:
            for item in results["items"]:
                if item["name"].startswith(name_prefix):
                    playlists.append(Playlist(
                        id=item["id"],
                        name=item["name"],
                        url=item["external_urls"]["spotify"],
                        track_count=item["tracks"]["total"],
                        created_at="",
                        mood="",
                        genres=[],
                    ))
            if results.get("next"):
                results = _call_with_retry(lambda: self.sp.next(results))
            else:
                break
        return playlists
```

- [ ] **Step 4: Run full test suite**

```bash
pytest tests/ -v
```

Expected: All tests PASS across models, history, and spotify_client.

- [ ] **Step 5: Commit**

```bash
git add spotify_client.py tests/test_spotify_client.py
git commit -m "feat: add recommendations, create_playlist, get_user_playlists to SpotifyClient"
```

---

## Task 6: App Shell

**Files:**
- Create: `app.py`
- Rewrite: `main.py`

- [ ] **Step 1: Create `app.py`**

```python
from textual.app import App
from textual.binding import Binding

from spotify_client import SpotifyClient


class DJRaraApp(App):
    """DJ Rara — lo-fi Spotify recommendation TUI."""

    CSS = """
    Screen {
        background: #0d0d0d;
    }

    .title {
        color: #80cbc4;
        text-style: bold;
        padding: 0 2;
    }

    .section-label {
        color: #555555;
        text-style: bold;
        padding: 1 0 0 0;
    }

    .subtitle {
        color: #444444;
    }

    Button.primary {
        background: #1db954;
        color: #000000;
        border: none;
        text-style: bold;
    }

    Button.primary:hover {
        background: #1ed760;
    }

    Button.primary:disabled {
        background: #1a3a28;
        color: #555555;
    }

    Button.chip {
        background: #1a1a1a;
        border: solid #333333;
        color: #666666;
        min-width: 14;
        height: 3;
    }

    Button.chip:hover {
        border: solid #666666;
        color: #aaaaaa;
    }

    Button.chip.active {
        background: #1a2e1f;
        border: solid #1db954;
        color: #1db954;
    }

    DataTable {
        background: #0d0d0d;
        color: #cccccc;
    }

    DataTable > .datatable--header {
        background: #141414;
        color: #555555;
        text-style: bold;
    }

    DataTable > .datatable--cursor {
        background: #1a2e1f;
        color: #1db954;
    }

    Footer {
        background: #111111;
        color: #444444;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "quit", show=False),
    ]

    def __init__(self, client: SpotifyClient):
        super().__init__()
        self.client = client

    def on_mount(self) -> None:
        from screens.mood import MoodScreen
        self.push_screen(MoodScreen())
```

- [ ] **Step 2: Rewrite `main.py`**

```python
#!/usr/bin/env python3
"""DJ Rara — entry point."""

import os
import sys

from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("♪ dj rara needs your spotify credentials.\n")
        print("  1. Copy .env.example to .env")
        print("  2. Add your SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET")
        print("  3. Get credentials at https://developer.spotify.com/dashboard")
        sys.exit(1)

    try:
        from spotify_auth import SpotifyAuthenticator
        sp = SpotifyAuthenticator().authenticate()
    except Exception as e:
        print(f"♪ authentication failed: {e}")
        print("  Try deleting .cache and running again.")
        sys.exit(1)

    from spotify_client import SpotifyClient
    from app import DJRaraApp

    client = SpotifyClient(sp)
    DJRaraApp(client).run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Verify imports resolve**

```bash
python -c "from app import DJRaraApp; from spotify_client import SpotifyClient; print('ok')"
```

Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add app.py main.py
git commit -m "feat: add DJRaraApp shell and rewrite main.py entry point"
```

---

## Task 7: MoodScreen

**Files:**
- Create: `screens/mood.py`

- [ ] **Step 1: Implement `screens/mood.py`**

```python
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Input, Label, Static
from textual.worker import work

TIME_RANGE_MAP = {
    "last 4 weeks": "short_term",
    "6 months": "medium_term",
    "all time": "long_term",
}
MOODS = ["chill", "energetic", "focus", "melancholy"]
TIME_RANGES = list(TIME_RANGE_MAP.keys())


class MoodScreen(Screen):
    """Home screen — pick mood, genres, time range, and track count."""

    BINDINGS = [
        Binding("s", "go_stats", "stats", show=False),
        Binding("p", "go_playlists", "playlists", show=False),
    ]

    CSS = """
    MoodScreen {
        align: center middle;
    }

    #mood-container {
        width: 64;
        background: #111111;
        border: round #222222;
        padding: 1 3 2 3;
    }

    #genre-scroll {
        max-height: 9;
        margin: 0;
    }

    #count-row {
        height: 4;
        margin-top: 1;
        align: left middle;
    }

    #count-input {
        width: 8;
        background: #1a1a1a;
        border: solid #333333;
        color: #e0e0e0;
        margin-left: 1;
    }

    #discover-btn {
        width: 100%;
        margin-top: 1;
        height: 3;
    }
    """

    def __init__(self):
        super().__init__()
        self._selected_mood = "chill"
        self._selected_time = "6 months"
        self._genres: list[str] = []
        self._selected_genres: set[str] = set()

    def compose(self) -> ComposeResult:
        with Container(id="mood-container"):
            yield Static("~ what's the vibe today? ~", classes="title")
            yield Label("mood", classes="section-label")
            with Horizontal():
                for mood in MOODS:
                    cls = "chip active" if mood == "chill" else "chip"
                    yield Button(mood, id=f"mood-{mood}", classes=cls)
            yield Label("genre", classes="section-label")
            with VerticalScroll(id="genre-scroll"):
                yield Static("· loading genres...", id="genre-loading", classes="subtitle")
            yield Label("time range", classes="section-label")
            with Horizontal():
                for tr in TIME_RANGES:
                    cls = "chip active" if tr == "6 months" else "chip"
                    yield Button(tr, id=f"time-{tr.replace(' ', '-')}", classes=cls)
            with Horizontal(id="count-row"):
                yield Label("how many tracks?", classes="section-label")
                yield Input(value="30", id="count-input", placeholder="30")
            yield Button("♫  discover", id="discover-btn", classes="primary")
        yield Footer()

    def on_mount(self) -> None:
        self._load_genres()

    @work(thread=True)
    def _load_genres(self) -> None:
        try:
            time_range = TIME_RANGE_MAP[self._selected_time]
            artists = self.app.client.get_top_artists(time_range=time_range, limit=30)
            counts: dict[str, int] = {}
            for artist in artists:
                for genre in artist.genres:
                    counts[genre] = counts.get(genre, 0) + 1
            top_genres = sorted(counts, key=counts.get, reverse=True)[:12]
            self.call_from_thread(self._populate_genres, top_genres)
        except Exception:
            self.call_from_thread(
                lambda: self.query_one("#genre-loading", Static).update(
                    "· could not load genres"
                )
            )

    def _populate_genres(self, genres: list[str]) -> None:
        self._genres = genres
        loading = self.query_one("#genre-loading", Static)
        loading.remove()
        container = self.query_one("#genre-scroll", VerticalScroll)
        for genre in genres:
            container.mount(Button(genre, id=f"genre-{genre.replace(' ', '-')}", classes="chip"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""

        if btn_id.startswith("mood-"):
            mood = btn_id[len("mood-"):]
            for m in MOODS:
                self.query_one(f"#mood-{m}", Button).remove_class("active")
            event.button.add_class("active")
            self._selected_mood = mood

        elif btn_id.startswith("time-"):
            slug = btn_id[len("time-"):]
            matched = next((t for t in TIME_RANGES if t.replace(" ", "-") == slug), None)
            if matched:
                for tr in TIME_RANGES:
                    self.query_one(f"#time-{tr.replace(' ', '-')}", Button).remove_class("active")
                event.button.add_class("active")
                self._selected_time = matched

        elif btn_id.startswith("genre-"):
            slug = btn_id[len("genre-"):]
            matched = next((g for g in self._genres if g.replace(" ", "-") == slug), None)
            if matched:
                if matched in self._selected_genres:
                    self._selected_genres.discard(matched)
                    event.button.remove_class("active")
                else:
                    self._selected_genres.add(matched)
                    event.button.add_class("active")

        elif btn_id == "discover-btn":
            self._start_discovery()

    def _start_discovery(self) -> None:
        try:
            count = int(self.query_one("#count-input", Input).value or "30")
            count = max(1, min(count, 100))
        except ValueError:
            count = 30

        btn = self.query_one("#discover-btn", Button)
        btn.disabled = True
        btn.label = "· brewing..."

        self._fetch_recommendations(
            mood=self._selected_mood,
            genres=sorted(self._selected_genres),
            time_range=TIME_RANGE_MAP[self._selected_time],
            count=count,
        )

    @work(thread=True)
    def _fetch_recommendations(
        self, mood: str, genres: list[str], time_range: str, count: int
    ) -> None:
        try:
            client = self.app.client
            top_artists = client.get_top_artists(time_range=time_range, limit=20)
            top_tracks = client.get_top_tracks(time_range=time_range, limit=20)
            followed = client.get_followed_artists(limit=20)

            seed_artist_ids = list(
                {a.id for a in top_artists[:10]} | {a.id for a in followed[:10]}
            )
            seed_track_ids = [t.id for t in top_tracks[:10]]

            tracks = client.get_recommendations(
                seed_artist_ids=seed_artist_ids,
                seed_track_ids=seed_track_ids,
                mood=mood,
                genres=genres,
                limit=count,
            )

            if len(tracks) < 3 and genres:
                tracks = client.get_recommendations(
                    seed_artist_ids=seed_artist_ids,
                    seed_track_ids=seed_track_ids,
                    mood=mood,
                    genres=[],
                    limit=count,
                )
                self.call_from_thread(
                    lambda: self.notify(
                        "♪ broadened search — genre filter dropped",
                        severity="information",
                    )
                )

            self.call_from_thread(self._on_recommendations_ready, tracks, mood, genres)

        except Exception as e:
            self.call_from_thread(self._on_discovery_error, str(e))

    def _on_recommendations_ready(
        self, tracks, mood: str, genres: list[str]
    ) -> None:
        from screens.recommendations import RecommendationsScreen

        btn = self.query_one("#discover-btn", Button)
        btn.disabled = False
        btn.label = "♫  discover"

        if not tracks:
            self.notify("♪ no tracks found — try different settings", severity="warning")
            return

        self.app.push_screen(RecommendationsScreen(tracks=tracks, mood=mood, genres=genres))

    def _on_discovery_error(self, message: str) -> None:
        self.notify(f"♪ something went wrong: {message}", severity="error")
        btn = self.query_one("#discover-btn", Button)
        btn.disabled = False
        btn.label = "♫  discover"

    def action_go_stats(self) -> None:
        from screens.stats import StatsScreen
        self.app.push_screen(StatsScreen())

    def action_go_playlists(self) -> None:
        from screens.playlists import PlaylistManagerScreen
        self.app.push_screen(PlaylistManagerScreen())
```

- [ ] **Step 2: Smoke test — open MoodScreen**

```bash
python main.py
```

Expected: Full-screen TUI opens. Title shows "~ what's the vibe today? ~". Genre chips load after a moment. Clicking mood/time chips toggles their active state (green border). Pressing `s` or `p` should error gracefully (those screens don't exist yet). `ctrl+c` exits.

- [ ] **Step 3: Commit**

```bash
git add screens/mood.py
git commit -m "feat: add MoodScreen with mood/genre/time controls and recommendation fetch"
```

---

## Task 8: RecommendationsScreen

**Files:**
- Create: `screens/recommendations.py`

- [ ] **Step 1: Implement `screens/recommendations.py`**

```python
import webbrowser
from datetime import date

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Static
from textual.worker import work

from history import add_playlist, add_seen_tracks
from models import Track


class RecommendationsScreen(Screen):
    """Browse and curate recommended tracks, then create a playlist."""

    BINDINGS = [
        Binding("space", "toggle_track", "keep/skip", show=True),
        Binding("o", "open_preview", "preview", show=True),
        Binding("c", "create_playlist", "create playlist", show=True),
        Binding("s", "go_stats", "stats", show=False),
        Binding("p", "go_playlists", "playlists", show=False),
        Binding("escape", "pop_screen", "back", show=True),
    ]

    CSS = """
    RecommendationsScreen {
        layout: vertical;
    }

    #header {
        height: 3;
        padding: 0 2;
        background: #111111;
        border-bottom: solid #222222;
        content-align: left middle;
    }

    DataTable {
        height: 1fr;
    }

    #preview-msg {
        height: 1;
        padding: 0 2;
        color: #555555;
        display: none;
    }

    #preview-msg.visible {
        display: block;
    }

    #status-bar {
        height: 2;
        padding: 0 2;
        background: #111111;
        border-top: solid #222222;
        content-align: left middle;
        color: #555555;
    }
    """

    def __init__(self, tracks: list[Track], mood: str, genres: list[str]):
        super().__init__()
        self._tracks = tracks
        self._mood = mood
        self._genres = genres
        # "default" | "kept" | "skipped"
        self._states: dict[str, str] = {t.id: "default" for t in tracks}

    def compose(self) -> ComposeResult:
        genre_str = " · ".join(self._genres) if self._genres else "all genres"
        yield Static(
            f"♫  {len(self._tracks)} tracks  ·  {self._mood}  ·  {genre_str}",
            id="header",
            classes="title",
        )
        yield DataTable(id="track-table", cursor_type="row", zebra_stripes=False)
        yield Static("", id="preview-msg")
        yield Static(self._status_text(), id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_column("#", key="num", width=4)
        table.add_column("Track", key="track", width=32)
        table.add_column("Artist", key="artist", width=26)
        table.add_column("♥", key="pop", width=4)
        for i, track in enumerate(self._tracks):
            table.add_row(*self._make_cells(track, i + 1), key=track.id)
        table.focus()

    def _make_cells(self, track: Track, num: int) -> tuple:
        state = self._states[track.id]
        if state == "kept":
            style = "bold green"
        elif state == "skipped":
            style = "dim strike"
        else:
            style = ""
        return (
            Text(str(num), style=style),
            Text(track.name, style=style),
            Text(", ".join(track.artists), style=style),
            Text(str(track.popularity), style=style),
        )

    def _status_text(self) -> str:
        kept = sum(1 for s in self._states.values() if s == "kept")
        skipped = sum(1 for s in self._states.values() if s == "skipped")
        remaining = len(self._tracks) - kept - skipped
        return f"kept: {kept}  ·  skipped: {skipped}  ·  remaining: {remaining}"

    def _current_track(self) -> Track | None:
        table = self.query_one(DataTable)
        if table.row_count == 0:
            return None
        idx = table.cursor_row
        if idx < 0 or idx >= len(self._tracks):
            return None
        return self._tracks[idx]

    def _refresh_row(self, track: Track) -> None:
        table = self.query_one(DataTable)
        num = self._tracks.index(track) + 1
        cells = self._make_cells(track, num)
        for col_key, cell in zip(["num", "track", "artist", "pop"], cells):
            table.update_cell(track.id, col_key, cell, update_width=False)

    def action_toggle_track(self) -> None:
        track = self._current_track()
        if not track:
            return
        current = self._states[track.id]
        self._states[track.id] = (
            "skipped" if current == "kept"
            else "kept" if current == "skipped"
            else "kept"
        )
        self._refresh_row(track)
        self.query_one("#status-bar", Static).update(self._status_text())

    def action_open_preview(self) -> None:
        track = self._current_track()
        if not track:
            return
        msg = self.query_one("#preview-msg", Static)
        if track.preview_url:
            webbrowser.open(track.preview_url)
            msg.update(f"♪ opening preview: {track.name}")
        else:
            msg.update("♪ no preview available for this track")
        msg.add_class("visible")
        self.set_timer(3.0, lambda: msg.remove_class("visible"))

    def action_create_playlist(self) -> None:
        kept = [t for t in self._tracks if self._states[t.id] == "kept"]
        if not kept:
            kept = list(self._tracks)

        genre_str = " · ".join(self._genres) if self._genres else ""
        today = date.today().strftime("%Y-%m-%d")
        parts = ["DJ Rara", self._mood]
        if genre_str:
            parts.append(genre_str)
        parts.append(today)
        name = " — ".join(parts)
        description = f"Personalized {self._mood} recommendations by DJ Rara · {today}"

        self._do_create_playlist(name=name, tracks=kept, description=description)

    @work(thread=True)
    def _do_create_playlist(
        self, name: str, tracks: list[Track], description: str
    ) -> None:
        try:
            playlist = self.app.client.create_playlist(
                name=name,
                tracks=tracks,
                description=description,
                mood=self._mood,
                genres=self._genres,
            )
            add_playlist(playlist)
            add_seen_tracks([t.id for t in tracks])
            self.call_from_thread(
                lambda: self.notify(f"♪ playlist created — {name}", severity="information")
            )
            self.call_from_thread(lambda: webbrowser.open(playlist.url))
        except Exception as e:
            self.call_from_thread(
                lambda: self.notify(f"♪ could not create playlist: {e}", severity="error")
            )

    def action_go_stats(self) -> None:
        from screens.stats import StatsScreen
        self.app.push_screen(StatsScreen())

    def action_go_playlists(self) -> None:
        from screens.playlists import PlaylistManagerScreen
        self.app.push_screen(PlaylistManagerScreen())
```

- [ ] **Step 2: Smoke test — full discover flow**

```bash
python main.py
```

Expected: MoodScreen → select mood → press Discover → RecommendationsScreen shows numbered track list. `↑↓` navigates rows. `space` toggles keep (green) / skip (dimmed strikethrough). Status bar updates. `o` on a track opens preview or shows "no preview available". `c` creates a playlist and opens it in the browser. `esc` returns to MoodScreen.

- [ ] **Step 3: Commit**

```bash
git add screens/recommendations.py
git commit -m "feat: add RecommendationsScreen with keep/skip curation and playlist creation"
```

---

## Task 9: StatsScreen

**Files:**
- Create: `screens/stats.py`

- [ ] **Step 1: Implement `screens/stats.py`**

```python
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Label, Static
from textual.worker import work

TIME_RANGES = ["short_term", "medium_term", "long_term"]
TIME_LABELS = {
    "short_term": "last 4 weeks",
    "medium_term": "6 months",
    "long_term": "all time",
}
BAR_WIDTH = 28


def _bar(value: float, width: int = BAR_WIDTH) -> str:
    filled = int(value * width)
    return "█" * filled + "░" * (width - filled)


def _genre_percentages(artists) -> list[tuple[str, float]]:
    counts: dict[str, int] = {}
    for artist in artists:
        for genre in artist.genres:
            counts[genre] = counts.get(genre, 0) + 1
    total = sum(counts.values()) or 1
    top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:8]
    return [(g, c / total) for g, c in top]


def _avg_audio_features(features: dict[str, dict]) -> dict[str, float]:
    keys = ["energy", "valence", "danceability", "acousticness"]
    if not features:
        return {k: 0.0 for k in keys}
    totals = {k: 0.0 for k in keys}
    for f in features.values():
        for k in keys:
            totals[k] += f.get(k, 0.0)
    n = len(features)
    return {k: v / n for k, v in totals.items()}


class StatsScreen(Screen):
    """Music DNA — genre breakdown, audio profile, top artists."""

    BINDINGS = [
        Binding("t", "toggle_time", "toggle time", show=True),
        Binding("r", "go_back", "back", show=True),
        Binding("p", "go_playlists", "playlists", show=False),
        Binding("escape", "pop_screen", "back", show=True),
    ]

    CSS = """
    StatsScreen {
        layout: vertical;
    }

    #header {
        height: 3;
        padding: 0 2;
        background: #111111;
        border-bottom: solid #222222;
        content-align: left middle;
    }

    #stats-scroll {
        padding: 1 3;
        height: 1fr;
    }

    .stat-heading {
        color: #80cbc4;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 0;
    }

    .bar-line {
        color: #cccccc;
    }

    .artist-line {
        color: #cccccc;
    }
    """

    def __init__(self):
        super().__init__()
        self._time_idx = 1

    def compose(self) -> ComposeResult:
        tr = TIME_LABELS[TIME_RANGES[self._time_idx]]
        yield Static(f"📊  music dna  ·  {tr}", id="header", classes="title")
        with VerticalScroll(id="stats-scroll"):
            yield Static("· loading your music dna...", id="loading-msg", classes="subtitle")
        yield Footer()

    def on_mount(self) -> None:
        self._load_stats()

    @work(thread=True)
    def _load_stats(self) -> None:
        try:
            time_range = TIME_RANGES[self._time_idx]
            client = self.app.client
            display_name = client.sp.current_user().get("display_name", "you")
            top_artists = client.get_top_artists(time_range=time_range, limit=20)
            top_tracks = client.get_top_tracks(time_range=time_range, limit=20)
            audio_features = client.get_audio_features([t.id for t in top_tracks]) if top_tracks else {}
            self.call_from_thread(
                self._render, display_name, top_artists, top_tracks[:5], audio_features
            )
        except Exception as e:
            self.call_from_thread(
                lambda: self.query_one("#loading-msg", Static).update(
                    f"· could not load stats: {e}"
                )
            )

    def _render(self, display_name, top_artists, top_five_artists, audio_features) -> None:
        scroll = self.query_one("#stats-scroll", VerticalScroll)
        try:
            self.query_one("#loading-msg", Static).remove()
        except Exception:
            pass

        tr = TIME_LABELS[TIME_RANGES[self._time_idx]]
        self.query_one("#header", Static).update(
            f"📊  music dna  ·  {display_name}  ·  {tr}"
        )

        # Genre bars
        scroll.mount(Static("top genres", classes="stat-heading"))
        genres = _genre_percentages(top_artists)
        if genres:
            for genre, pct in genres:
                bar = _bar(pct)
                scroll.mount(Static(
                    f"  [dim]{genre:<20}[/dim] [green]{bar}[/green] [dim]{pct:.0%}[/dim]",
                    markup=True, classes="bar-line"
                ))
        else:
            scroll.mount(Static("  · no genre data", classes="subtitle"))

        # Audio feature bars
        scroll.mount(Static("audio profile", classes="stat-heading"))
        avgs = _avg_audio_features(audio_features)
        feature_names = {
            "energy": "energy",
            "valence": "mood",
            "danceability": "danceable",
            "acousticness": "acoustic",
        }
        for key, label in feature_names.items():
            val = avgs[key]
            bar = _bar(val)
            scroll.mount(Static(
                f"  [dim]{label:<20}[/dim] [cyan]{bar}[/cyan] [dim]{val:.2f}[/dim]",
                markup=True, classes="bar-line"
            ))

        # Top artists
        scroll.mount(Static("top artists", classes="stat-heading"))
        if top_five_artists:
            for i, artist in enumerate(top_five_artists, 1):
                scroll.mount(Static(
                    f"  [green]{i}.[/green]  {artist.name}",
                    markup=True, classes="artist-line"
                ))
        else:
            scroll.mount(Static("  · no artist data", classes="subtitle"))

    def action_toggle_time(self) -> None:
        self._time_idx = (self._time_idx + 1) % len(TIME_RANGES)
        scroll = self.query_one("#stats-scroll", VerticalScroll)
        scroll.remove_children()
        scroll.mount(Static("· loading...", id="loading-msg", classes="subtitle"))
        self._load_stats()

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_go_playlists(self) -> None:
        from screens.playlists import PlaylistManagerScreen
        self.app.push_screen(PlaylistManagerScreen())
```

- [ ] **Step 2: Smoke test — open stats screen**

```bash
python main.py
```

Expected: Press `s` from MoodScreen → StatsScreen shows genre bars (Spotify green), audio feature bars (teal), and top 5 artists. Press `t` to cycle through last 4 weeks / 6 months / all time — bars reload. Press `esc` to go back.

- [ ] **Step 3: Commit**

```bash
git add screens/stats.py
git commit -m "feat: add StatsScreen with genre bars, audio profile, and top artists"
```

---

## Task 10: PlaylistManagerScreen + Cleanup

**Files:**
- Create: `screens/playlists.py`
- Delete: `recommendation_engine.py`, `diagnose.py`, `debug_data.py`, `test_auth.py`

- [ ] **Step 1: Implement `screens/playlists.py`**

```python
import webbrowser

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, ListItem, ListView, Static
from textual.worker import work

from history import get_playlists


class PlaylistManagerScreen(Screen):
    """Browse past DJ Rara playlists and open them in Spotify."""

    BINDINGS = [
        Binding("enter", "open_playlist", "open in spotify", show=True),
        Binding("r", "go_back", "back", show=True),
        Binding("s", "go_stats", "stats", show=False),
        Binding("escape", "pop_screen", "back", show=True),
    ]

    CSS = """
    PlaylistManagerScreen {
        layout: vertical;
    }

    #header {
        height: 3;
        padding: 0 2;
        background: #111111;
        border-bottom: solid #222222;
        content-align: left middle;
    }

    ListView {
        height: 1fr;
        background: #0d0d0d;
    }

    ListItem {
        padding: 0 2;
        height: 4;
        border-bottom: solid #1a1a1a;
    }

    ListItem.--highlight {
        background: #1a2e1f;
    }

    #detail-panel {
        height: 7;
        padding: 1 3;
        background: #111111;
        border-top: solid #222222;
    }

    #detail-name {
        color: #80cbc4;
        text-style: bold;
    }

    #detail-meta {
        color: #555555;
        margin-top: 0;
    }

    #empty-msg {
        color: #444444;
        padding: 2 2;
    }
    """

    def __init__(self):
        super().__init__()
        self._playlists: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Static("📋  playlists  ·  dj rara", id="header", classes="title")
        yield ListView(id="playlist-list")
        with Vertical(id="detail-panel"):
            yield Static("", id="detail-name")
            yield Static("", id="detail-meta")
        yield Footer()

    def on_mount(self) -> None:
        self._load_playlists()

    @work(thread=True)
    def _load_playlists(self) -> None:
        try:
            history = get_playlists()
            spotify = self.app.client.get_user_playlists(name_prefix="DJ Rara")
            history_ids = {p["id"] for p in history}
            merged = list(history)
            for pl in spotify:
                if pl.id not in history_ids:
                    merged.append({
                        "id": pl.id, "name": pl.name, "url": pl.url,
                        "track_count": pl.track_count, "created_at": pl.created_at,
                        "mood": "", "genres": [],
                    })
            self.call_from_thread(self._render, merged)
        except Exception as e:
            self.call_from_thread(
                lambda: self.notify(f"♪ could not load playlists: {e}", severity="error")
            )

    def _render(self, playlists: list[dict]) -> None:
        self._playlists = playlists
        lv = self.query_one("#playlist-list", ListView)

        if not playlists:
            lv.mount(ListItem(Static("· no dj rara playlists yet", id="empty-msg")))
            return

        for pl in playlists:
            count = pl.get("track_count", 0)
            created = pl.get("created_at", "")
            label = (
                f"[green]♫[/green]  {pl['name']}\n"
                f"   [dim]{count} tracks · {created}[/dim]"
            )
            lv.append(ListItem(Static(label, markup=True)))

        if playlists:
            self._update_detail(playlists[0])

    def _update_detail(self, pl: dict) -> None:
        self.query_one("#detail-name", Static).update(pl.get("name", ""))
        parts = []
        count = pl.get("track_count", 0)
        created = pl.get("created_at", "")
        mood = pl.get("mood", "")
        genres = pl.get("genres", [])
        if count:
            parts.append(f"{count} tracks")
        if created:
            parts.append(created)
        if mood:
            parts.append(f"mood: {mood}")
        if genres:
            parts.append(f"genres: {', '.join(genres)}")
        self.query_one("#detail-meta", Static).update("  ·  ".join(parts))

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        idx = event.list_view.index
        if idx is not None and 0 <= idx < len(self._playlists):
            self._update_detail(self._playlists[idx])

    def action_open_playlist(self) -> None:
        lv = self.query_one("#playlist-list", ListView)
        idx = lv.index
        if idx is not None and 0 <= idx < len(self._playlists):
            url = self._playlists[idx].get("url", "")
            if url:
                webbrowser.open(url)
                self.notify("♪ opening in spotify", severity="information")

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_go_stats(self) -> None:
        from screens.stats import StatsScreen
        self.app.push_screen(StatsScreen())
```

- [ ] **Step 2: Smoke test — open playlist manager**

```bash
python main.py
```

Expected: Press `p` from any screen → PlaylistManagerScreen shows DJ Rara playlists from history and Spotify. Arrow keys highlight rows and update the detail panel. `enter` opens the selected playlist in the browser.

- [ ] **Step 3: Remove old files**

```bash
git rm recommendation_engine.py diagnose.py debug_data.py test_auth.py
```

- [ ] **Step 4: Run full test suite**

```bash
pytest tests/ -v
```

Expected: All tests PASS. No import errors.

- [ ] **Step 5: Full end-to-end smoke test**

Walk through the complete flow:
1. `python main.py` → MoodScreen loads, genres populate
2. Select a mood (e.g. chill) and 1-2 genres → press Discover
3. RecommendationsScreen: use `space` to keep/skip a few tracks → press `c` → playlist created and opens in browser
4. Press `s` → StatsScreen: genre bars and audio profile load → press `t` to cycle time range
5. Press `p` → PlaylistManagerScreen: newly created playlist appears → press `enter` → opens in browser
6. Press `esc` repeatedly to unwind the screen stack back to MoodScreen
7. Press `ctrl+c` to exit

- [ ] **Step 6: Final commit**

```bash
git add screens/playlists.py
git commit -m "feat: add PlaylistManagerScreen and complete TUI rewrite

Removes recommendation_engine.py, diagnose.py, debug_data.py, test_auth.py.
All four screens wired: MoodScreen, RecommendationsScreen, StatsScreen,
PlaylistManagerScreen. Full lo-fi Spotify-green Textual TUI."
```
