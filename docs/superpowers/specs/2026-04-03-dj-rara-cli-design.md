# DJ Rara CLI — Design Spec
**Date:** 2026-04-03  
**Status:** Approved

---

## Overview

DJ Rara is a Spotify recommendation engine CLI that delivers a fully interactive terminal UI experience. Users pick a mood and genre, get personalized track recommendations seeded from their actual Spotify listening history, curate the list interactively, and publish it as a Spotify playlist — all without leaving the terminal.

**Aesthetic:** Lo-Fi Chill meets Spotify Native. Mellow language, soft teal (`#80CBC4`) and Spotify green (`#1DB954`) on dark backgrounds. Clean, understated, warm.

---

## Tech Stack

| Concern | Choice |
|---|---|
| TUI framework | `textual` |
| Spotify API | `spotipy` |
| Config | `python-dotenv` |
| History | Local JSON (`~/.dj-rara.json`) |
| Python | 3.9+ |

**New dependency:** `textual` added to `requirements.txt`.

---

## File Structure

```
dj-rara/
├── main.py                  # Entry point — auth check, launch Textual app
├── app.py                   # DJRaraApp(App) — screen routing, global keybindings
├── screens/
│   ├── __init__.py
│   ├── mood.py              # MoodScreen — mood, genre, time range, track count
│   ├── recommendations.py   # RecommendationsScreen — browse, curate, playlist
│   ├── stats.py             # StatsScreen — Music DNA view
│   └── playlists.py         # PlaylistManagerScreen — past DJ Rara playlists
├── spotify_auth.py          # Unchanged — OAuth via spotipy
├── spotify_client.py        # All Spotify API calls (replaces recommendation_engine.py)
├── models.py                # Track, Artist, Playlist dataclasses
├── history.py               # Read/write ~/.dj-rara.json
├── requirements.txt         # + textual
└── .env / .env.example
```

`recommendation_engine.py` is removed — its logic is absorbed into `spotify_client.py`.

---

## Data Models (`models.py`)

```python
@dataclass
class Track:
    id: str
    name: str
    artists: list[str]      # display names
    album: str
    popularity: int         # 0–100
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
    created_at: str         # ISO date string
    mood: str
    genres: list[str]
```

---

## Screen Map

### MoodScreen (`screens/mood.py`)
The launch screen. Shown immediately after auth.

**Controls:**
- Mood selector — single-select chips: `chill`, `energetic`, `focus`, `melancholy`
- Genre chips — multi-select, populated from user's top artist genres via Spotify API. If none selected, no genre filter is applied to the recommendations call (broader results).
- Time range — single-select: `last 4 weeks`, `6 months` (default), `all time`
- Track count — numeric input, default 30
- Discover button — triggers recommendation fetch, shows loading overlay

**Keybindings:** `tab` next field, `enter` discover, `s` stats, `p` playlists

---

### RecommendationsScreen (`screens/recommendations.py`)
Shown after recommendations load. Core interaction screen.

**Layout:**
- Scrollable track table: `#  track  artist  popularity`
- Status bar: `kept: N  skipped: N  remaining: N`
- Selected row highlighted in Spotify green
- Kept tracks marked green, skipped tracks dimmed and struck through

**Keybindings:**
- `↑↓` — navigate
- `space` — toggle keep/skip on current track
- `o` — open 30s preview in system browser (uses `preview_url`; shows inline message if unavailable)
- `c` — create playlist from kept tracks (prompts for name, defaults to `DJ Rara — {mood} · {genres} · {date}`)
- `esc` — back to MoodScreen

---

### StatsScreen (`screens/stats.py`)
Music DNA view. Accessible at any time.

**Sections:**
- **Top genres** — ASCII bar chart, derived from top artists' genre tags, shown as percentages
- **Audio features** — ASCII bars for energy, valence, danceability, acousticness (averaged from user's top tracks via `audio_features` API)
- **Top artists** — numbered list, up to 5, for the selected time range
- Time range toggle cycles short/medium/long term and refreshes all data

**Keybindings:** `r` recommendations, `p` playlists, `t` toggle time range

---

### PlaylistManagerScreen (`screens/playlists.py`)
Shows past DJ Rara playlists, sourced from history + Spotify.

**Layout:**
- Scrollable list of playlists with name, date, track count
- Detail panel below selected item: mood, genres, created date
- "Open in Spotify" button launches browser with playlist URL

**Keybindings:** `↑↓` navigate, `enter` open in Spotify, `r` recommendations, `s` stats

---

## Spotify Client (`spotify_client.py`)

Single class `SpotifyClient` wrapping all API calls. Returns model objects, never raw dicts.

**Methods:**
- `get_top_tracks(time_range, limit)` → `list[Track]`
- `get_top_artists(time_range, limit)` → `list[Artist]`
- `get_followed_artists(limit)` → `list[Artist]`
- `get_recommendations(seed_artists, seed_tracks, mood, genres, limit)` → `list[Track]`
- `get_audio_features(track_ids)` → `dict[str, dict]`
- `create_playlist(name, tracks, description, public)` → `Playlist`
- `get_user_playlists(name_prefix)` → `list[Playlist]`

Personalization: seeds come from user's top tracks + top artists + followed artists. Mood maps to Spotify `target_*` audio feature params passed to the recommendations endpoint.

---

## Mood → Audio Features Mapping

| Mood | target_energy | target_valence | target_tempo | target_acousticness |
|---|---|---|---|---|
| chill | 0.30 | 0.60 | 90 | 0.70 |
| energetic | 0.85 | 0.75 | 140 | 0.10 |
| focus | 0.50 | 0.40 | 110 | 0.50 |
| melancholy | 0.25 | 0.20 | 80 | 0.60 |

---

## History (`history.py`)

Stored at `~/.dj-rara.json`. Tracks:
- `playlists` — list of `Playlist` dicts for the manager screen
- `seen_track_ids` — set of track IDs already recommended, used to de-duplicate future runs

Written after every successful playlist creation. Read on startup.

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Missing `.env` credentials | Exit before launching TUI; print setup instructions |
| Spotify auth failure | Exit with clear message; suggest re-running to re-authenticate |
| API rate limit | Auto-retry with exponential backoff; show spinner status in TUI |
| No recommendations returned | Retry with genre filter dropped; notify user in status bar |
| Track has no preview URL | Show `♪ no preview available` inline, do not open browser |
| History file missing/corrupt | Recreate empty file, continue silently |

---

## Testing

- `spotify_client.py` — unit tested with a mock spotipy client
- `models.py` — dataclass construction and serialization
- `history.py` — read/write/corrupt-file recovery
- Mood mapping — pure function, unit tested for all four moods
- TUI screens — not unit tested (Textual widget testing is high-effort, low ROI for a personal tool)
