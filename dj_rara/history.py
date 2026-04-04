import json
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
