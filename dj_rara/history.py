import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from .models import Playlist

HISTORY_PATH = Path.home() / ".dj-rara.json"

_DEFAULTS: dict = {
    "playlists": [],
    "seen_track_ids": [],
    "kept_tracks": [],       # list of {id, mood, features, at}
    "skipped_track_ids": [], # tracks explicitly skipped — never recommend again
}


def load_history() -> dict:
    try:
        data = json.loads(HISTORY_PATH.read_text())
        for key, default in _DEFAULTS.items():
            if key not in data:
                data[key] = default
        return data
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return {k: list(v) if isinstance(v, list) else v for k, v in _DEFAULTS.items()}


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


# ---------------------------------------------------------------------------
# Feedback collection
# ---------------------------------------------------------------------------

def add_kept_tracks(entries: list[dict]) -> None:
    """Persist kept track feedback with audio features for taste-profile learning.

    Each entry must have keys: ``id`` (str), ``mood`` (str), ``features`` (dict).
    Duplicate IDs are silently ignored.
    """
    history = load_history()
    existing_ids = {e["id"] for e in history["kept_tracks"]}
    today = date.today().isoformat()
    for entry in entries:
        if entry.get("id") and entry["id"] not in existing_ids:
            history["kept_tracks"].append(
                {"id": entry["id"], "mood": entry["mood"],
                 "features": entry.get("features", {}), "at": today}
            )
            existing_ids.add(entry["id"])
    save_history(history)


def add_skipped_track_ids(track_ids: list[str]) -> None:
    """Mark tracks as explicitly skipped — exclude from all future pools."""
    history = load_history()
    skipped = set(history["skipped_track_ids"])
    skipped.update(track_ids)
    history["skipped_track_ids"] = list(skipped)
    save_history(history)


def get_skipped_track_ids() -> set[str]:
    return set(load_history()["skipped_track_ids"])


# ---------------------------------------------------------------------------
# Taste-profile computation
# ---------------------------------------------------------------------------

_PROFILE_KEYS = ["energy", "valence", "acousticness", "danceability", "instrumentalness", "tempo"]
_MIN_KEPT_FOR_PROFILE = 3  # need at least this many kept tracks to produce a profile


def get_taste_profile(mood: str | None = None) -> dict[str, float]:
    """Return average audio features of kept tracks, optionally mood-filtered.

    Returns an empty dict when there is not enough data (< ``_MIN_KEPT_FOR_PROFILE``
    tracks), signalling the scorer to rely on mood targets + popularity only.
    Prefers mood-specific data; falls back to all moods when insufficient.
    """
    kept = load_history()["kept_tracks"]

    if mood:
        mood_kept = [e for e in kept if e.get("mood") == mood]
        if len(mood_kept) >= _MIN_KEPT_FOR_PROFILE:
            kept = mood_kept
        # else fall through to global pool

    if len(kept) < _MIN_KEPT_FOR_PROFILE:
        return {}

    totals: dict[str, float] = {k: 0.0 for k in _PROFILE_KEYS}
    counts: dict[str, int] = {k: 0 for k in _PROFILE_KEYS}
    for entry in kept:
        feats = entry.get("features", {})
        for key in _PROFILE_KEYS:
            val = feats.get(key)
            if val is not None:
                totals[key] += float(val)
                counts[key] += 1

    return {k: totals[k] / counts[k] for k in _PROFILE_KEYS if counts[k] > 0}
