from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Label, Static


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
