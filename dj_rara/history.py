import json
import time
from dataclasses import asdict
from pathlib import Path

from .models import Playlist

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


def set_track_skipped(track_id: str, skipped: bool) -> None:
    history = load_history()
    now = time.time()
    cooldowns = {tid: expiry for tid, expiry in history.get("skipped_until", {}).items()
                 if isinstance(expiry, (int, float)) and expiry > now}
    if skipped:
        cooldowns[track_id] = now + 7 * 24 * 60 * 60
    else:
        cooldowns.pop(track_id, None)
    history["skipped_until"] = cooldowns
    save_history(history)


def get_skipped_track_ids() -> set[str]:
    now = time.time()
    return {tid for tid, expiry in load_history().get("skipped_until", {}).items()
            if isinstance(expiry, (int, float)) and expiry > now}
