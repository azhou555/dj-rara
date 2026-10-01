import subprocess
import tempfile
import os
import urllib.parse
import urllib.request
import json
import random
import webbrowser
from datetime import date

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Static
from textual import work

from ..history import add_playlist, add_seen_tracks, set_track_skipped
from ..models import Track
from ..selection import RecommendationPool, recording_keys


def _itunes_preview(track: Track) -> str | None:
    """Look up a 30-second preview URL from the iTunes Search API."""
    try:
        artist = track.artists[0] if track.artists else ""
        query = urllib.parse.urlencode({"term": f"{artist} {track.name}", "entity": "song", "limit": 5})
        url = f"https://itunes.apple.com/search?{query}"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
        name_lower = track.name.lower()
        for result in data.get("results", []):
            if name_lower in result.get("trackName", "").lower():
                preview = result.get("previewUrl")
                if preview:
                    return preview
        # No exact match — return first available preview
        for result in data.get("results", []):
            preview = result.get("previewUrl")
            if preview:
                return preview
    except Exception:
        pass
    return None


class RecommendationsScreen(Screen):
    """Browse and curate recommended tracks, then create a playlist."""

    BINDINGS = [
        Binding("space", "toggle_track", "keep/skip", show=False),
        Binding("k", "keep_track", "keep", show=True),
        Binding("x", "skip_track", "skip", show=True),
        Binding("u", "undo", "undo", show=True),
        Binding("r", "replace_skipped", "replace skipped", show=True),
        Binding("R", "replace_unkept", "replace unkept", show=True),
        Binding("o", "open_preview", "preview", show=True),
        Binding("c", "create_playlist", "create playlist", show=True),
        Binding("s", "go_stats", "stats", show=False),
        Binding("p", "go_playlists", "playlists", show=False),
        Binding("escape", "go_back", "back", show=True, priority=True),
    ]

    CSS = """
    RecommendationsScreen {
        layout: vertical;
    }

    #header {
        height: 3;
        padding: 0 2;
        background: $surface;
        border-bottom: solid $subtle-border;
        content-align: left middle;
    }

    DataTable {
        height: 1fr;
    }

    #preview-msg {
        height: 1;
        padding: 0 2;
        color: $muted;
        display: none;
    }

    #preview-msg.visible {
        display: block;
    }

    #status-bar {
        height: 2;
        padding: 0 2;
        background: $surface;
        border-top: solid $subtle-border;
        content-align: left middle;
        color: $muted;
    }
    """

    def __init__(self, tracks: list[Track], mood: str, genres: list[str],
                 pool: RecommendationPool | None = None):
        super().__init__()
        self._tracks = tracks
        self._mood = mood
        self._genres = genres
        self._states: dict[str, str] = {t.id: "default" for t in tracks}
        self._preview_proc: subprocess.Popen | None = None
        self._pool = pool or RecommendationPool()
        self._pool.displayed_ids.update(t.id for t in tracks)
        for track in tracks:
            self._pool.displayed_recordings.update(recording_keys(track))
        self._undo: list[tuple[str, str]] = []
        self._creating = False

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
        yield Button(self._export_label(), id="create-playlist")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_column("#", key="num", width=4)
        table.add_column("Track", key="track", width=32)
        table.add_column("Artist", key="artist", width=26)
        table.add_column("♥", key="pop", width=4)
        for i, track in enumerate(self._tracks):
            table.add_row(*self._make_cells(track, i + 1), key=track.id)
        self._refresh_status()
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
        return f"kept: {kept}  ·  skipped: {skipped}  ·  undecided: {remaining}  ·  export: {len(self._export_tracks())}"

    def _export_tracks(self) -> list[Track]:
        kept = [t for t in self._tracks if self._states[t.id] == "kept"]
        return kept or [t for t in self._tracks if self._states[t.id] == "default"]

    def _export_label(self) -> str:
        return "Creating playlist…" if self._creating else f"Create playlist · {len(self._export_tracks())} tracks"

    def _refresh_status(self) -> None:
        self.query_one("#status-bar", Static).update(self._status_text())
        button = self.query_one("#create-playlist", Button)
        button.label = self._export_label()
        button.disabled = self._creating or not self._export_tracks()

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
        self._set_state(track, "skipped" if self._states[track.id] == "kept" else "kept")

    def _set_state(self, track: Track, state: str, remember: bool = True) -> None:
        if self._creating or self._states[track.id] == state:
            return
        try:
            set_track_skipped(track.id, state == "skipped")
        except OSError as error:
            self.notify(f"Could not save skip preference: {error}", severity="warning")
            return
        if remember:
            self._undo.append((track.id, self._states[track.id]))
        self._states[track.id] = state
        self._refresh_row(track)
        self._refresh_status()

    def action_keep_track(self) -> None:
        if track := self._current_track():
            self._set_state(track, "kept")

    def action_skip_track(self) -> None:
        if track := self._current_track():
            self._set_state(track, "skipped")

    def action_undo(self) -> None:
        if self._creating:
            return
        while self._undo:
            tid, state = self._undo.pop()
            track = next((t for t in self._tracks if t.id == tid), None)
            if track:
                self._set_state(track, state, remember=False)
                return

    def action_replace_skipped(self) -> None:
        self._replace_tracks({"skipped"})

    def action_replace_unkept(self) -> None:
        self._replace_tracks({"skipped", "default"})

    def _replace_tracks(self, states: set[str]) -> None:
        if self._creating:
            return
        indices = [i for i, t in enumerate(self._tracks) if self._states[t.id] in states]
        if not indices:
            self.notify("No tracks to replace.")
            return
        replaced = 0
        discovery_count = int(len(indices) * max(0.0, min(self._pool.discovery_ratio, 1.0)))
        preferences = [1.0] * discovery_count + [0.0] * (len(indices) - discovery_count)
        random.shuffle(preferences)
        for index, ratio in zip(indices, preferences):
            # Retain all other rows so partial replacements also respect the cap.
            retained = self._tracks[:index] + self._tracks[index + 1:]
            replacement = self._pool.take(1, retained=retained, discovery_ratio=ratio)
            if not replacement:
                continue
            old = self._tracks[index]
            del self._states[old.id]
            self._tracks[index] = replacement[0]
            self._states[replacement[0].id] = "default"
            replaced += 1
        table = self.query_one(DataTable)
        cursor = table.cursor_row
        table.clear()
        for i, track in enumerate(self._tracks):
            table.add_row(*self._make_cells(track, i + 1), key=track.id)
        table.move_cursor(row=cursor)
        self._refresh_status()
        self.notify(f"Replaced {replaced} of {len(indices)} tracks."
                    + (" No more suitable candidates; discover again for a fresh pool."
                       if replaced < len(indices) else ""))

    def action_open_preview(self) -> None:
        # If something is playing, stop it
        if self._preview_proc and self._preview_proc.poll() is None:
            self._preview_proc.terminate()
            self._preview_proc = None
            msg = self.query_one("#preview-msg", Static)
            msg.update("♪ stopped")
            self.set_timer(1.5, lambda: msg.remove_class("visible"))
            return
        track = self._current_track()
        if not track:
            return
        msg = self.query_one("#preview-msg", Static)
        msg.update("♪ fetching preview...")
        msg.add_class("visible")
        self._fetch_and_play_preview(track)

    @work(thread=True)
    def _fetch_and_play_preview(self, track: Track) -> None:
        preview_url = track.preview_url or _itunes_preview(track)
        if preview_url:
            # Stop any running preview first
            if self._preview_proc and self._preview_proc.poll() is None:
                self._preview_proc.terminate()

            import sys
            player = (
                ["afplay"]
                if sys.platform == "darwin"
                else ["cvlc", "--play-and-exit"]
                if sys.platform != "win32"
                else None
            )

            if player is None:
                # Windows: download and open with default media player
                tmp_path = None
                try:
                    with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as tmp:
                        tmp_path = tmp.name
                    urllib.request.urlretrieve(preview_url, tmp_path)
                    os.startfile(tmp_path)
                    self.app.call_from_thread(
                        lambda n=track.name: self.query_one("#preview-msg", Static).update(f"♪ previewing: {n}")
                    )
                except Exception:
                    self.app.call_from_thread(
                        lambda: self.query_one("#preview-msg", Static).update("♪ preview failed")
                    )
                return

            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as tmp:
                    tmp_path = tmp.name
                urllib.request.urlretrieve(preview_url, tmp_path)
                self._preview_proc = subprocess.Popen(player + [tmp_path])
                self.app.call_from_thread(
                    lambda n=track.name: self.query_one("#preview-msg", Static).update(f"♪ previewing: {n}  (o to stop)")
                )
                self._preview_proc.wait()
            except Exception:
                self.app.call_from_thread(
                    lambda: self.query_one("#preview-msg", Static).update("♪ preview failed")
                )
            finally:
                if tmp_path:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
        else:
            self.app.call_from_thread(lambda: (
                webbrowser.open(f"https://open.spotify.com/track/{track.id}"),
                self.query_one("#preview-msg", Static).update(f"♪ no preview — opening in spotify: {track.name}"),
            ))
        self.app.call_from_thread(
            lambda: self.set_timer(2.0, lambda: self.query_one("#preview-msg", Static).remove_class("visible"))
        )

    def action_create_playlist(self) -> None:
        if self._creating:
            return
        kept = self._export_tracks()
        if not kept:
            self.notify("Keep a track or undo a skip before creating a playlist.", severity="warning")
            return

        genre_str = " · ".join(self._genres) if self._genres else ""
        today = date.today().strftime("%Y-%m-%d")
        parts = ["DJ Rara", self._mood]
        if genre_str:
            parts.append(genre_str)
        parts.append(today)
        name = " — ".join(parts)
        description = f"Personalized {self._mood} recommendations by DJ Rara · {today}"

        self._creating = True
        self._refresh_status()
        self._do_create_playlist(name=name, tracks=kept, description=description)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create-playlist":
            self.action_create_playlist()

    def _finish_create(self) -> None:
        self._creating = False
        self._refresh_status()

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
            self.app.call_from_thread(
                lambda: self.notify(f"♪ playlist created — {name}", severity="information")
            )
            self.app.call_from_thread(lambda: webbrowser.open(playlist.url))
        except Exception as e:
            self.app.call_from_thread(
                lambda error=str(e): self.notify(f"♪ could not create playlist: {error}", severity="error")
            )
        finally:
            self.app.call_from_thread(self._finish_create)

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_go_stats(self) -> None:
        from screens.stats import StatsScreen
        self.app.push_screen(StatsScreen())

    def action_go_playlists(self) -> None:
        from screens.playlists import PlaylistManagerScreen
        self.app.push_screen(PlaylistManagerScreen())
