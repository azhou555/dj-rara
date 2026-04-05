import subprocess
import tempfile
import os
import urllib.parse
import urllib.request
import json
import webbrowser
from datetime import date

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Static
from textual import work

from ..history import add_playlist, add_seen_tracks
from ..models import Track


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
        Binding("space", "toggle_track", "keep/skip", show=True),
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

    def __init__(self, tracks: list[Track], mood: str, genres: list[str]):
        super().__init__()
        self._tracks = tracks
        self._mood = mood
        self._genres = genres
        self._states: dict[str, str] = {t.id: "default" for t in tracks}
        self._preview_proc: subprocess.Popen | None = None

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
            self.app.call_from_thread(
                lambda: self.notify(f"♪ playlist created — {name}", severity="information")
            )
            self.app.call_from_thread(lambda: webbrowser.open(playlist.url))
        except Exception as e:
            self.app.call_from_thread(
                lambda: self.notify(f"♪ could not create playlist: {e}", severity="error")
            )

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_go_stats(self) -> None:
        from screens.stats import StatsScreen
        self.app.push_screen(StatsScreen())

    def action_go_playlists(self) -> None:
        from screens.playlists import PlaylistManagerScreen
        self.app.push_screen(PlaylistManagerScreen())
