import subprocess
import sys
import webbrowser
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Input, Label, Static


ENV_PATH = Path.cwd() / ".env"
REDIRECT_URI = "http://127.0.0.1:8888/callback"
SPOTIFY_DASHBOARD_URL = "https://developer.spotify.com/dashboard"


def _copy_to_clipboard(text: str) -> bool:
    try:
        if sys.platform == "darwin":
            subprocess.run(["pbcopy"], input=text.encode(), check=True)
        elif sys.platform == "win32":
            subprocess.run(["clip"], input=text.encode(), check=True)
        else:
            subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode(), check=True)
        return True
    except Exception:
        return False


class SetupScreen(Screen):
    """First-run setup — collect Spotify credentials and write .env."""

    BINDINGS = [
        Binding("ctrl+c", "quit", "quit", show=False),
    ]

    CSS = """
    SetupScreen {
        align: center middle;
    }

    #setup-container {
        width: 64;
        background: $surface;
        border: round $subtle-border;
        padding: 2 3;
    }

    #setup-title {
        color: $accent;
        text-style: bold;
        margin-bottom: 1;
    }

    #setup-subtitle {
        color: $muted;
        margin-bottom: 0;
    }

    #dashboard-link {
        color: $primary;
        text-style: underline;
        margin-bottom: 1;
    }

    #dashboard-link:hover {
        color: $accent;
    }

    .field-label {
        color: $muted;
        margin-top: 1;
    }

    Input {
        background: $panel;
        border: solid $subtle-border;
        color: $foreground;
        margin-top: 0;
    }

    Input:focus {
        border: solid $primary;
    }

    #redirect-row {
        margin-top: 1;
        height: 3;
        align: left middle;
    }

    #redirect-uri {
        color: $dim;
        width: 1fr;
        content-align: left middle;
        height: 3;
        padding: 0 1;
        background: $panel;
        border: solid $subtle-border;
    }

    #copy-btn {
        width: auto;
        min-width: 10;
        height: 3;
        margin-left: 1;
        background: $panel;
        border: solid $subtle-border;
        color: $muted;
    }

    #copy-btn:hover {
        border: solid $foreground-muted;
        color: $foreground;
    }

    #save-btn {
        width: 100%;
        margin-top: 2;
        height: 3;
    }

    #status-msg {
        color: $primary;
        margin-top: 1;
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="setup-container"):
            yield Static("~ dj rara setup ~", id="setup-title")
            yield Static(
                "Create a free Spotify app at:",
                id="setup-subtitle",
            )
            yield Static("  developer.spotify.com/dashboard ↗", id="dashboard-link")
            yield Static("then paste your credentials below.", classes="field-label")
            yield Label("Client ID", classes="field-label")
            yield Input(placeholder="paste your client id", id="client-id-input", password=False)
            yield Label("Client Secret", classes="field-label")
            yield Input(placeholder="paste your client secret", id="client-secret-input", password=True)
            yield Label("Add this Redirect URI to your Spotify app:", classes="field-label")
            with Horizontal(id="redirect-row"):
                yield Static(REDIRECT_URI, id="redirect-uri")
                yield Button("copy", id="copy-btn")
            yield Button("♫  save & continue", id="save-btn", classes="primary")
            yield Static("", id="status-msg")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            self._save_credentials()
        elif event.button.id == "copy-btn":
            self._copy_redirect_uri()

    def on_static_click(self, event: Static.Clicked) -> None:
        if event.static.id == "dashboard-link":
            webbrowser.open(SPOTIFY_DASHBOARD_URL)

    def _copy_redirect_uri(self) -> None:
        msg = self.query_one("#status-msg", Static)
        if _copy_to_clipboard(REDIRECT_URI):
            msg.update("♪ copied to clipboard")
        else:
            msg.update(f"♪ copy manually: {REDIRECT_URI}")

    def _save_credentials(self) -> None:
        client_id = self.query_one("#client-id-input", Input).value.strip()
        client_secret = self.query_one("#client-secret-input", Input).value.strip()
        msg = self.query_one("#status-msg", Static)

        if not client_id or not client_secret:
            msg.update("♪ both fields are required")
            return

        env_content = (
            f"SPOTIFY_CLIENT_ID={client_id}\n"
            f"SPOTIFY_CLIENT_SECRET={client_secret}\n"
        )
        try:
            ENV_PATH.write_text(env_content)
            msg.update("♪ saved — authenticating...")
            self.set_timer(0.5, self._launch_app)
        except Exception as e:
            msg.update(f"♪ could not write .env: {e}")

    def _launch_app(self) -> None:
        from dotenv import load_dotenv
        load_dotenv(ENV_PATH, override=True)

        from ..spotify_auth import SpotifyAuthenticator

        try:
            sp = SpotifyAuthenticator().authenticate()
        except Exception as e:
            self.query_one("#status-msg", Static).update(f"♪ auth failed: {e}")
            return

        from ..spotify_client import SpotifyClient
        self.app.client = SpotifyClient(sp)
        self.app.pop_screen()
        from .mood import MoodScreen
        self.app.push_screen(MoodScreen())
