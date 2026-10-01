import asyncio
from unittest.mock import MagicMock

import pytest
from textual.app import App
from textual.widgets import Button, DataTable

from dj_rara.app import DJRaraApp
from dj_rara.history import get_skipped_track_ids
from dj_rara.models import Track
from dj_rara.screens.recommendations import RecommendationsScreen
from dj_rara.selection import RecommendationPool


def track(tid):
    return Track(tid, tid, [tid], "album", 50, None, f"spotify:track:{tid}", [tid])


@pytest.fixture(autouse=True)
def isolated_history(monkeypatch, tmp_path):
    monkeypatch.setattr("dj_rara.history.HISTORY_PATH", tmp_path / "history.json")


class CurationApp(App):
    CSS = DJRaraApp.CSS
    get_theme_variable_defaults = DJRaraApp.get_theme_variable_defaults

    def __init__(self, screen):
        super().__init__()
        self.client = MagicMock()
        self.curation = screen

    def on_mount(self):
        self.push_screen(self.curation)


def test_keyboard_curation_undo_and_export_count():
    async def check():
        screen = RecommendationsScreen([track("a"), track("b")], "chill", [])
        async with CurationApp(screen).run_test(size=(140, 35)) as pilot:
            await pilot.press("x")
            assert [t.id for t in screen._export_tracks()] == ["b"]
            assert get_skipped_track_ids() == {"a"}
            assert "1 tracks" in str(screen.query_one(Button).label)
            await pilot.press("u")
            assert len(screen._export_tracks()) == 2
            assert get_skipped_track_ids() == set()
            await pilot.press("k", "down", "x")
            assert [t.id for t in screen._export_tracks()] == ["a"]
            await pilot.press("up", "x")
            assert screen._export_tracks() == []
            assert screen.query_one(Button).disabled
            screen._do_create_playlist = MagicMock()
            await pilot.press("c")
            screen._do_create_playlist.assert_not_called()
    asyncio.run(check())


def test_replacements_preserve_kept_tracks_and_handle_exhaustion():
    async def check():
        pool = RecommendationPool(discovery=[track("c")])
        screen = RecommendationsScreen([track("a"), track("b")], "chill", [], pool)
        async with CurationApp(screen).run_test(size=(140, 35)) as pilot:
            await pilot.press("k", "down", "x", "r")
            assert [t.id for t in screen._tracks] == ["a", "c"]
            assert screen._states == {"a": "kept", "c": "default"}
            assert get_skipped_track_ids() == {"b"}
            assert screen.query_one(DataTable).row_count == 2
            await pilot.press("R")
            assert [t.id for t in screen._tracks] == ["a", "c"]
            assert screen._states["a"] == "kept"
    asyncio.run(check())


def test_replace_unkept_and_partial_reserve():
    async def check():
        pool = RecommendationPool(discovery=[track("c")])
        screen = RecommendationsScreen([track("a"), track("b")], "chill", [], pool)
        async with CurationApp(screen).run_test(size=(140, 35)) as pilot:
            await pilot.press("R")
            assert [t.id for t in screen._tracks] == ["c", "b"]
            await pilot.press("R")
            assert [t.id for t in screen._tracks] == ["c", "b"]
    asyncio.run(check())


def test_export_blocks_duplicate_submission_and_uses_kept_only():
    async def check():
        screen = RecommendationsScreen([track("a"), track("b")], "chill", [])
        screen._do_create_playlist = MagicMock()
        async with CurationApp(screen).run_test(size=(140, 35)) as pilot:
            await pilot.press("k", "c", "c")
            screen._do_create_playlist.assert_called_once()
            assert [t.id for t in screen._do_create_playlist.call_args.kwargs["tracks"]] == ["a"]
            assert screen.query_one(Button).disabled
            await pilot.press("x", "R")
            assert screen._states["a"] == "kept"
            screen._finish_create()
            assert not screen.query_one(Button).disabled
    asyncio.run(check())


@pytest.mark.parametrize("fail", [False, True])
def test_create_worker_recovers_and_exports_correct_tracks(monkeypatch, fail):
    from dj_rara.models import Playlist
    from dj_rara.history import get_seen_track_ids
    monkeypatch.setattr("dj_rara.screens.recommendations.webbrowser.open", lambda url: None)

    async def check():
        screen = RecommendationsScreen([track("a"), track("b")], "chill", [])
        app = CurationApp(screen)
        app.client.create_playlist.return_value = Playlist("p", "Test", "https://example.com", 1, "today", "chill", [])
        if fail:
            app.client.create_playlist.side_effect = RuntimeError("offline")
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.press("x", "c")
            await screen.workers.wait_for_complete()
            await pilot.pause()
            assert not screen._creating
            assert not screen.query_one(Button).disabled
            assert [t.id for t in app.client.create_playlist.call_args.kwargs["tracks"]] == ["b"]
            assert get_seen_track_ids() == (set() if fail else {"b"})
    asyncio.run(check())
