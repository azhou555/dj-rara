from textual.app import App
from textual.binding import Binding

from spotify_client import SpotifyClient


class DJRaraApp(App):
    """DJ Rara — lo-fi Spotify recommendation TUI."""

    CSS = """
    Screen {
        background: #0d0d0d;
    }

    .title {
        color: #80cbc4;
        text-style: bold;
        padding: 0 2;
    }

    .section-label {
        color: #555555;
        text-style: bold;
        padding: 1 0 0 0;
    }

    .subtitle {
        color: #444444;
    }

    Button.primary {
        background: #1db954;
        color: #000000;
        border: none;
        text-style: bold;
    }

    Button.primary:hover {
        background: #1ed760;
    }

    Button.primary:disabled {
        background: #1a3a28;
        color: #555555;
    }

    Button.chip {
        background: #1a1a1a;
        border: solid #333333;
        color: #666666;
        min-width: 14;
        height: 3;
    }

    Button.chip:hover {
        border: solid #666666;
        color: #aaaaaa;
    }

    Button.chip.active {
        background: #1a2e1f;
        border: solid #1db954;
        color: #1db954;
    }

    DataTable {
        background: #0d0d0d;
        color: #cccccc;
    }

    DataTable > .datatable--header {
        background: #141414;
        color: #555555;
        text-style: bold;
    }

    DataTable > .datatable--cursor {
        background: #1a2e1f;
        color: #1db954;
    }

    Footer {
        background: #111111;
        color: #444444;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "quit", show=False),
    ]

    def __init__(self, client: SpotifyClient):
        super().__init__()
        self.client = client

    def on_mount(self) -> None:
        from screens.mood import MoodScreen
        self.push_screen(MoodScreen())
