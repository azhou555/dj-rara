from textual.app import App
from textual.binding import Binding

from .spotify_client import SpotifyClient
from .themes import ALL_THEMES, SPOTIFY


class DJRaraApp(App):
    """DJ Rara — lo-fi Spotify recommendation TUI."""

    CSS = """
    Screen {
        background: $background;
    }

    .title {
        color: $accent;
        text-style: bold;
        padding: 0 2;
    }

    .section-label {
        color: $muted;
        text-style: bold;
        padding: 1 0 0 0;
    }

    .subtitle {
        color: $dim;
    }

    Button.primary {
        background: $primary;
        color: $background;
        border: none;
        text-style: bold;
    }

    Button.primary:hover {
        background: $primary-lighten-1;
    }

    Button.primary:disabled {
        background: $primary-muted;
        color: $muted;
    }

    Button.chip {
        background: $panel;
        border: solid $subtle-border;
        color: $muted;
        min-width: 14;
        height: 3;
    }

    Button.chip:hover {
        border: solid $foreground-muted;
        color: $foreground;
    }

    Button.chip.active {
        background: $chip-active-bg;
        border: solid $primary;
        color: $primary;
    }

    DataTable {
        background: $background;
        color: $foreground;
    }

    DataTable > .datatable--header {
        background: $surface;
        color: $muted;
        text-style: bold;
    }

    DataTable > .datatable--cursor {
        background: $chip-active-bg;
        color: $primary;
    }

    Footer {
        background: $surface;
        color: $dim;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "quit", show=False),
    ]

    def get_theme_variable_defaults(self) -> dict[str, str]:
        # Provide fallback values so CSS parses before the theme is applied.
        # The active theme's `variables` dict will override these at runtime.
        return {
            "chip-active-bg": "#1a2e1f",
            "muted": "#555555",
            "dim": "#444444",
            "subtle-border": "#222222",
        }

    def __init__(self, client: SpotifyClient | None):
        super().__init__()
        self.client = client

    def on_mount(self) -> None:
        for theme in ALL_THEMES:
            self.register_theme(theme)
        self.theme = SPOTIFY.name

        if self.client is None:
            from .screens.setup import SetupScreen
            self.push_screen(SetupScreen())
        else:
            from .screens.mood import MoodScreen
            self.push_screen(MoodScreen())
