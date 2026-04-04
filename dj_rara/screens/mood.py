import random

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Input, Label, Static
from textual import work

EXPLORE_GENRES = [
    "afrobeats", "ambient", "bossa nova", "cumbia", "dark ambient",
    "drum and bass", "flamenco", "footwork", "garage rock", "gospel",
    "grime", "hyperpop", "j-pop", "k-indie", "latin jazz",
    "lo-fi beats", "math rock", "modal jazz", "neo soul", "new wave",
    "noise rock", "post-bop", "psychedelic rock", "reggaeton", "salsa",
    "shoegaze", "soca", "soul jazz", "synth-pop", "turkish folk",
    "city pop", "desert blues", "electro swing", "funk carioca", "mbaqanga",
]

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
        width: 72;
        background: $surface;
        border: round $subtle-border;
        padding: 1 3 1 3;
    }

    .section-label {
        margin-top: 0;
        margin-bottom: 0;
    }

    #genre-scroll {
        height: auto;
        max-height: 14;
        margin: 0;
    }

    .genre-row {
        height: 3;
    }

    #count-row {
        height: 3;
        margin-top: 0;
        align: left middle;
    }

    #count-input {
        width: 8;
        background: $panel;
        border: solid $subtle-border;
        color: $foreground;
        margin-left: 1;
    }

    #discover-btn {
        width: 100%;
        margin-top: 1;
        height: 3;
    }

    .explore-divider {
        color: $dim;
        margin-top: 1;
        margin-bottom: 0;
    }
    """

    VIBE_RATIOS = {"familiar": 0.1, "mixed": 0.5, "new": 0.9}

    def __init__(self):
        super().__init__()
        self._selected_mood = "chill"
        self._selected_time = "6 months"
        self._selected_vibe = "mixed"
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
            yield Label("vibe", classes="section-label")
            with Horizontal():
                for vibe in ("familiar", "mixed", "new"):
                    cls = "chip active" if vibe == "mixed" else "chip"
                    yield Button(vibe, id=f"vibe-{vibe}", classes=cls)
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
            top_genres = sorted(counts, key=counts.get, reverse=True)[:9]
            top_set = set(top_genres)
            explore = [g for g in EXPLORE_GENRES if g not in top_set]
            random.shuffle(explore)
            self.app.call_from_thread(
                lambda tg=top_genres, eg=explore[:3]: self._populate_genres(tg, eg)
            )
        except Exception:
            self.app.call_from_thread(
                lambda: self.query_one("#genre-loading", Static).update(
                    "· could not load genres"
                )
            )

    def _populate_genres(self, genres: list[str], explore: list[str]) -> None:
        self._genres = genres + explore
        loading = self.query_one("#genre-loading", Static)
        loading.remove()
        container = self.query_one("#genre-scroll", VerticalScroll)

        def _mount_rows(genre_list: list[str]) -> None:
            for i in range(0, len(genre_list), 3):
                row = Horizontal(classes="genre-row")
                container.mount(row)
                for genre in genre_list[i:i + 3]:
                    row.mount(Button(genre, id=f"genre-{genre.replace(' ', '-')}", classes="chip"))

        _mount_rows(genres)
        if explore:
            container.mount(Static("· explore ·", classes="explore-divider"))
            _mount_rows(explore)

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

        elif btn_id.startswith("vibe-"):
            vibe = btn_id[len("vibe-"):]
            if vibe in self.VIBE_RATIOS:
                for v in self.VIBE_RATIOS:
                    self.query_one(f"#vibe-{v}", Button).remove_class("active")
                event.button.add_class("active")
                self._selected_vibe = vibe

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
            discovery_ratio=self.VIBE_RATIOS[self._selected_vibe],
        )

    @work(thread=True)
    def _fetch_recommendations(
        self, mood: str, genres: list[str], time_range: str, count: int, discovery_ratio: float = 0.5
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
                discovery_ratio=discovery_ratio,
            )

            if len(tracks) < 3 and genres:
                tracks = client.get_recommendations(
                    seed_artist_ids=seed_artist_ids,
                    seed_track_ids=seed_track_ids,
                    mood=mood,
                    genres=[],
                    limit=count,
                    discovery_ratio=discovery_ratio,
                )
                self.app.call_from_thread(
                    lambda: self.notify(
                        "♪ broadened search — genre filter dropped",
                        severity="information",
                    )
                )

            self.app.call_from_thread(lambda t=tracks, m=mood, g=genres: self._on_recommendations_ready(t, m, g))

        except Exception as e:
            self.app.call_from_thread(lambda err=str(e): self._on_discovery_error(err))

    def _on_recommendations_ready(
        self, tracks, mood: str, genres: list[str]
    ) -> None:
        from .recommendations import RecommendationsScreen

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
        from .stats import StatsScreen
        self.app.push_screen(StatsScreen())

    def action_go_playlists(self) -> None:
        from .playlists import PlaylistManagerScreen
        self.app.push_screen(PlaylistManagerScreen())
