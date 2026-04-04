import webbrowser

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, ListItem, ListView, Static

from ..history import get_playlists


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
        background: $surface;
        border-bottom: solid $subtle-border;
        content-align: left middle;
    }

    ListView {
        height: 1fr;
        background: $background;
    }

    ListItem {
        padding: 0 2;
        height: 4;
        border-bottom: solid $panel;
    }

    ListItem.--highlight {
        background: $chip-active-bg;
    }

    #detail-panel {
        height: 7;
        padding: 1 3;
        background: $surface;
        border-top: solid $subtle-border;
    }

    #detail-name {
        color: $accent;
        text-style: bold;
    }

    #detail-meta {
        color: $muted;
        margin-top: 0;
    }

    #empty-msg {
        color: $dim;
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
            self.app.call_from_thread(lambda pl=merged: self._render(pl))
        except Exception as e:
            self.app.call_from_thread(
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
