from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Input, Label, Static
from textual import work

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
