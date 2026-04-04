import webbrowser
from datetime import date

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Static
from textual import work

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
