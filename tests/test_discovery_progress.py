import asyncio
from unittest.mock import MagicMock

import pytest
from textual.app import App
from textual.widgets import Button, Static

from dj_rara.app import DJRaraApp
from dj_rara.models import Artist, Track
from dj_rara.screens.mood import MoodScreen
from dj_rara.screens.recommendations import RecommendationsScreen


class DiscoveryApp(App):
    CSS = DJRaraApp.CSS
    get_theme_variable_defaults = DJRaraApp.get_theme_variable_defaults

    def __init__(self):
        super().__init__()
        self.client = MagicMock()
        self.client.get_top_artists.return_value = [Artist("a", "Artist", ["shoegaze"], 50)]
        self.client.get_top_tracks.return_value = []
        self.client.get_followed_artists.return_value = []
        self.mood = MoodScreen()

    def on_mount(self):
        self.push_screen(self.mood)


@pytest.mark.parametrize("fail", [False, True])
def test_thread_progress_and_completion(fail):
    async def check():
        app = DiscoveryApp()
        progress_seen = []
        original = app.mood._set_discovery_progress

        def observe(message):
            original(message)
            progress_seen.append(str(app.mood.query_one("#discovery-progress", Static).render()))
        app.mood._set_discovery_progress = observe

        def recommend(**kwargs):
            kwargs["progress"]("Ranking tracks…")
            if fail:
                raise RuntimeError("offline")
            kwargs["candidate_pool"].reasons = {"t": ["Found by search: shoegaze"]}
            return [Track("t", "Song", ["Artist"], "Album", 50, None, "spotify:track:t")]
        app.client.get_recommendations.side_effect = recommend

        async with app.run_test(size=(120, 45)) as pilot:
            await app.workers.wait_for_complete()
            app.mood._start_discovery()
            app.mood._start_discovery()  # double submission is ignored
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert "Loading your listening profile…" in progress_seen
            assert "Ranking tracks…" in progress_seen
            assert not app.mood.query_one("#discover-btn", Button).disabled
            app.client.get_recommendations.assert_called_once()
            if fail:
                assert app.screen is app.mood
                assert progress_seen[-1] == "Discovery failed. Try again."
            else:
                assert isinstance(app.screen, RecommendationsScreen)
                assert "shoegaze" in str(app.screen.query_one("#track-reasons", Static).render())
                assert progress_seen[-1] == "Found 1 tracks."
    asyncio.run(check())
