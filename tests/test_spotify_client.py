import pytest
from unittest.mock import MagicMock
from dj_rara.models import Track, Artist, Playlist


@pytest.fixture
def mock_sp():
    sp = MagicMock()
    sp.current_user.return_value = {"id": "testuser", "display_name": "Test User"}
    return sp


@pytest.fixture
def client(mock_sp):
    from dj_rara.spotify_client import SpotifyClient
    return SpotifyClient(mock_sp)


def _raw_track(id="t1", name=None, artist="Bon Iver", artist_id="a1",
               album="For Emma", popularity=91, preview_url="https://example.com/p.mp3"):
    return {
        "id": id, "name": name if name is not None else ("Skinny Love" if id == "t1" else id),
        "artists": [{"name": artist, "id": artist_id}],
        "album": {"name": album},
        "popularity": popularity,
        "preview_url": preview_url,
        "uri": f"spotify:track:{id}",
    }


def _raw_artist(id="a1", name="Bon Iver", genres=None, popularity=80):
    return {
        "id": id, "name": name,
        "genres": genres or ["indie folk", "folk rock"],
        "popularity": popularity,
    }


class TestGetTopTracks:
    def test_returns_track_objects(self, client, mock_sp):
        mock_sp.current_user_top_tracks.return_value = {"items": [_raw_track()]}
        tracks = client.get_top_tracks(time_range="medium_term", limit=1)
        assert len(tracks) == 1
        assert isinstance(tracks[0], Track)
        assert tracks[0].name == "Skinny Love"
        assert tracks[0].artists == ["Bon Iver"]

    def test_none_preview_url_preserved(self, client, mock_sp):
        mock_sp.current_user_top_tracks.return_value = {
            "items": [_raw_track(preview_url=None)]
        }
        tracks = client.get_top_tracks(time_range="medium_term", limit=1)
        assert tracks[0].preview_url is None

    def test_passes_time_range(self, client, mock_sp):
        mock_sp.current_user_top_tracks.return_value = {"items": []}
        client.get_top_tracks(time_range="short_term", limit=10)
        mock_sp.current_user_top_tracks.assert_called_once_with(
            limit=10, offset=0, time_range="short_term"
        )


class TestGetTopArtists:
    def test_returns_artist_objects(self, client, mock_sp):
        mock_sp.current_user_top_artists.return_value = {"items": [_raw_artist()]}
        artists = client.get_top_artists(time_range="medium_term", limit=1)
        assert len(artists) == 1
        assert isinstance(artists[0], Artist)
        assert artists[0].genres == ["indie folk", "folk rock"]

    def test_passes_time_range(self, client, mock_sp):
        mock_sp.current_user_top_artists.return_value = {"items": []}
        client.get_top_artists(time_range="long_term", limit=5)
        mock_sp.current_user_top_artists.assert_called_once_with(
            limit=5, offset=0, time_range="long_term"
        )


class TestGetFollowedArtists:
    def test_returns_artist_objects(self, client, mock_sp):
        mock_sp.current_user_followed_artists.return_value = {
            "artists": {"items": [_raw_artist()], "next": None}
        }
        artists = client.get_followed_artists(limit=1)
        assert len(artists) == 1
        assert isinstance(artists[0], Artist)

    def test_paginates(self, client, mock_sp):
        page1 = {"artists": {"items": [_raw_artist(id="a1")], "next": "url"}}
        page2 = {"artists": {"items": [_raw_artist(id="a2")], "next": None}}
        mock_sp.current_user_followed_artists.return_value = page1
        mock_sp.next.return_value = page2
        artists = client.get_followed_artists(limit=50)
        assert len(artists) == 2


class TestGetAudioFeatures:
    def test_returns_keyed_dict(self, client, mock_sp):
        mock_sp.audio_features.return_value = [
            {"id": "t1", "energy": 0.4, "valence": 0.6,
             "danceability": 0.5, "acousticness": 0.7, "tempo": 85.0}
        ]
        features = client.get_audio_features(["t1"])
        assert "t1" in features
        assert features["t1"]["energy"] == pytest.approx(0.4)

    def test_empty_list_skips_api(self, client, mock_sp):
        features = client.get_audio_features([])
        assert features == {}
        mock_sp.audio_features.assert_not_called()


class TestMoodToFeatures:
    def test_chill(self):
        from dj_rara.spotify_client import mood_to_features
        f = mood_to_features("chill")
        assert f["target_energy"] == pytest.approx(0.30)
        assert f["target_valence"] == pytest.approx(0.60)
        assert f["target_acousticness"] == pytest.approx(0.70)

    def test_energetic(self):
        from dj_rara.spotify_client import mood_to_features
        assert mood_to_features("energetic")["target_energy"] == pytest.approx(0.85)

    def test_focus(self):
        from dj_rara.spotify_client import mood_to_features
        assert mood_to_features("focus")["target_energy"] == pytest.approx(0.50)

    def test_melancholy(self):
        from dj_rara.spotify_client import mood_to_features
        assert mood_to_features("melancholy")["target_energy"] == pytest.approx(0.25)

    def test_unknown_mood_raises(self):
        from dj_rara.spotify_client import mood_to_features
        with pytest.raises(ValueError, match="Unknown mood"):
            mood_to_features("groovy")


class TestGetRecommendations:
    def _setup_mock(self, mock_sp, tracks=None):
        """Wire up all endpoints the new recommendations strategy calls."""
        tracks = tracks or [_raw_track(id="r1")]
        mock_sp.artist_top_tracks.return_value = {"tracks": tracks}
        mock_sp.current_user_saved_tracks.return_value = {"items": []}
        mock_sp.tracks.return_value = {"tracks": []}
        mock_sp.search.side_effect = lambda q, type, limit: (
            {"artists": {"items": []}} if type == "artist"
            else {"playlists": {"items": []}} if type == "playlist"
            else {"tracks": {"items": []}}
        )
        mock_sp.playlist_tracks.return_value = {"items": []}
        mock_sp.artists.return_value = {"artists": []}
        mock_sp.artist_related_artists.return_value = {"artists": []}
        mock_sp.audio_features.return_value = []

    def test_returns_track_objects(self, client, mock_sp):
        self._setup_mock(mock_sp, tracks=[_raw_track(id="r1")])
        tracks = client.get_recommendations(
            seed_artist_ids=["a1", "a2"],
            seed_track_ids=["t1"],
            mood="chill",
            genres=[],
            limit=10,
        )
        assert len(tracks) >= 1
        assert isinstance(tracks[0], Track)

    def test_uses_artist_top_tracks(self, client, mock_sp):
        self._setup_mock(mock_sp, tracks=[_raw_track(id="r1")])
        client.get_recommendations(
            seed_artist_ids=["a1"], seed_track_ids=[],
            mood="chill", genres=[], limit=5,
        )
        mock_sp.artist_top_tracks.assert_called()

    def test_incorporates_genre_in_search(self, client, mock_sp):
        self._setup_mock(mock_sp)
        client.get_recommendations(
            seed_artist_ids=["a1"], seed_track_ids=[],
            mood="chill", genres=["indie folk"], limit=5,
        )
        # genre should appear in at least one search query using the genre: field filter
        calls = [str(c) for c in mock_sp.search.call_args_list]
        assert any("indie folk" in c for c in calls)

    def test_genre_filter_uses_artist_lookup(self, client, mock_sp):
        """When genres are selected, sp.artists() is called to validate genre matches."""
        self._setup_mock(mock_sp, tracks=[_raw_track(id="r1", artist_id="a1")])
        client.get_recommendations(
            seed_artist_ids=["a1"], seed_track_ids=[],
            mood="chill", genres=["indie folk"], limit=5,
        )
        mock_sp.artists.assert_called()

    def test_genre_filter_uses_synonyms(self, client, mock_sp):
        """A track whose artist is tagged 'dream pop' passes the shoegaze filter via synonyms."""
        self._setup_mock(mock_sp, tracks=[_raw_track(id="r1", artist_id="a1")])
        mock_sp.artists.return_value = {"artists": [
            {"id": "a1", "name": "Slowdive", "genres": ["dream pop", "ambient pop"], "popularity": 60}
        ]}
        tracks = client.get_recommendations(
            seed_artist_ids=["a1"], seed_track_ids=[],
            mood="chill", genres=["shoegaze"], limit=5,
        )
        assert any(t.id == "r1" for t in tracks)

    def test_genre_search_queries_artists_by_genre(self, client, mock_sp):
        """When genres are selected, sp.search is called with type='artist'."""
        self._setup_mock(mock_sp)
        client.get_recommendations(
            seed_artist_ids=["a1"], seed_track_ids=[],
            mood="chill", genres=["shoegaze"], limit=5,
        )
        artist_search_calls = [
            c for c in mock_sp.search.call_args_list
            if c.kwargs.get("type") == "artist" or (c.args and "artist" in str(c.args))
        ]
        assert len(artist_search_calls) > 0

    def test_related_artists_queried_for_discovery(self, client, mock_sp):
        """artist_related_artists is called for seed artists to enrich discovery pool."""
        self._setup_mock(mock_sp)
        client.get_recommendations(
            seed_artist_ids=["a1", "a2"], seed_track_ids=[],
            mood="chill", genres=[], limit=5,
        )
        mock_sp.artist_related_artists.assert_called()

    def test_related_artist_tracks_appear_in_results(self, client, mock_sp):
        """Top tracks from related artists end up in the result pool."""
        self._setup_mock(mock_sp, tracks=[])  # seed artists have no top tracks
        related_track = _raw_track(id="related1", artist_id="rel_artist")
        mock_sp.artist_related_artists.return_value = {"artists": [
            {"id": "rel_artist", "name": "Related Artist", "genres": []}
        ]}
        # Override: related artist has a top track, seed artists do not
        mock_sp.artist_top_tracks.side_effect = lambda a: (
            {"tracks": [related_track]} if a == "rel_artist" else {"tracks": []}
        )
        tracks = client.get_recommendations(
            seed_artist_ids=["a1"], seed_track_ids=[],
            mood="chill", genres=[], limit=5,
        )
        assert any(t.id == "related1" for t in tracks)

    def test_related_artist_traversal_respects_genre_filter(self, client, mock_sp):
        """Related artists outside the expanded genre set are skipped."""
        self._setup_mock(mock_sp, tracks=[])
        mock_sp.artist_related_artists.return_value = {"artists": [
            {"id": "rel1", "name": "Genre Match",  "genres": ["dream pop"]},
            {"id": "rel2", "name": "Genre Mismatch", "genres": ["reggaeton"]},
        ]}
        genre_track  = _raw_track(id="g1", artist_id="rel1")
        other_track  = _raw_track(id="g2", artist_id="rel2")
        mock_sp.artist_top_tracks.side_effect = lambda a: {
            "rel1": {"tracks": [genre_track]},
            "rel2": {"tracks": [other_track]},
        }.get(a, {"tracks": []})
        mock_sp.artists.return_value = {"artists": [
            {"id": "rel1", "name": "Genre Match", "genres": ["dream pop"], "popularity": 70}
        ]}
        tracks = client.get_recommendations(
            seed_artist_ids=["a1"], seed_track_ids=[],
            mood="chill", genres=["shoegaze"], limit=10,
        )
        ids = [t.id for t in tracks]
        assert "g1" in ids       # dream pop → passes shoegaze synonym filter
        assert "g2" not in ids   # reggaeton → filtered out

    def test_audio_features_fetched_for_mood_scoring(self, client, mock_sp):
        """get_recommendations calls audio_features to score the candidate pool."""
        self._setup_mock(mock_sp, tracks=[_raw_track(id="r1")])
        client.get_recommendations(
            seed_artist_ids=["a1"], seed_track_ids=[],
            mood="chill", genres=[], limit=5,
        )
        mock_sp.audio_features.assert_called()

    def test_mood_scoring_prefers_closer_tracks(self, client, mock_sp):
        """Tracks closer to the mood target are selected over worse matches."""
        close  = _raw_track(id="close",  artist_id="a1")
        far    = _raw_track(id="far",    artist_id="a1")
        self._setup_mock(mock_sp, tracks=[close, far])
        # chill target: energy≈0.30, valence≈0.60, acousticness≈0.70, tempo≈90
        mock_sp.audio_features.return_value = [
            {"id": "close", "energy": 0.30, "valence": 0.60,
             "acousticness": 0.70, "tempo": 90.0,  "danceability": 0.5},
            {"id": "far",   "energy": 0.90, "valence": 0.10,
             "acousticness": 0.05, "tempo": 180.0, "danceability": 0.5},
        ]
        tracks = client.get_recommendations(
            seed_artist_ids=["a1"], seed_track_ids=[],
            mood="chill", genres=[], limit=1,
        )
        assert tracks[0].id == "close"

    def test_genre_filter_falls_back_when_no_match(self, client, mock_sp):
        """If no tracks match the genre filter, all tracks are returned (partial match fallback)."""
        self._setup_mock(mock_sp, tracks=[_raw_track(id="r1", artist_id="a1")])
        # artist has no genres overlapping with selected genre
        mock_sp.artists.return_value = {"artists": [
            {"id": "a1", "name": "Bon Iver", "genres": ["folk"], "popularity": 80}
        ]}
        tracks = client.get_recommendations(
            seed_artist_ids=["a1"], seed_track_ids=[],
            mood="chill", genres=["k-pop"], limit=5,
        )
        # Falls back to unfiltered — r1 should still be present
        assert any(t.id == "r1" for t in tracks)

    def test_genre_filter_keeps_matching_tracks(self, client, mock_sp):
        """Tracks whose artists match any selected genre are kept."""
        matching = _raw_track(id="r1", artist_id="a1")
        non_matching = _raw_track(id="r2", artist_id="a2")
        mock_sp.artist_top_tracks.return_value = {"tracks": [matching, non_matching]}
        mock_sp.current_user_saved_tracks.return_value = {"items": []}
        mock_sp.tracks.return_value = {"tracks": []}
        mock_sp.search.side_effect = lambda q, type, limit: (
            {"artists": {"items": []}} if type == "artist" else {"tracks": {"items": []}}
        )
        mock_sp.artist_related_artists.return_value = {"artists": []}
        mock_sp.audio_features.return_value = []
        mock_sp.artists.return_value = {"artists": [
            {"id": "a1", "name": "Artist A", "genres": ["indie folk"], "popularity": 80},
            {"id": "a2", "name": "Artist B", "genres": ["reggaeton"], "popularity": 70},
        ]}
        tracks = client.get_recommendations(
            seed_artist_ids=["a1", "a2"], seed_track_ids=[],
            mood="chill", genres=["indie folk"], limit=10,
        )
        ids = [t.id for t in tracks]
        assert "r1" in ids
        assert "r2" not in ids

    def test_deduplicates_results(self, client, mock_sp):
        dup = _raw_track(id="dup")
        mock_sp.artist_top_tracks.return_value = {"tracks": [dup, dup]}
        mock_sp.current_user_saved_tracks.return_value = {"items": [{"track": dup}]}
        mock_sp.tracks.return_value = {"tracks": []}
        mock_sp.search.side_effect = lambda q, type, limit: (
            {"artists": {"items": []}} if type == "artist" else {"tracks": {"items": []}}
        )
        mock_sp.artist_related_artists.return_value = {"artists": []}
        mock_sp.audio_features.return_value = []
        tracks = client.get_recommendations(
            seed_artist_ids=["a1"], seed_track_ids=[],
            mood="chill", genres=[], limit=10,
        )
        ids = [t.id for t in tracks]
        assert len(ids) == len(set(ids))

    def test_filters_out_seen_track_ids(self, client, mock_sp, monkeypatch):
        import dj_rara.history as history
        monkeypatch.setattr(history, "HISTORY_PATH", __import__("pathlib").Path("/tmp/dj-rara-seen-test.json"))
        from dj_rara.history import add_seen_tracks
        add_seen_tracks(["t1"])

        mock_sp.artist_top_tracks.return_value = {"tracks": [_raw_track(id="t1"), _raw_track(id="t2")]}
        mock_sp.current_user_saved_tracks.return_value = {"items": []}
        mock_sp.tracks.return_value = {"tracks": []}
        mock_sp.search.side_effect = lambda q, type, limit: (
            {"artists": {"items": []}} if type == "artist" else {"tracks": {"items": []}}
        )
        mock_sp.artist_related_artists.return_value = {"artists": []}
        mock_sp.audio_features.return_value = []
        tracks = client.get_recommendations(
            seed_artist_ids=["a1"], seed_track_ids=[],
            mood="chill", genres=[], limit=10,
        )
        ids = [t.id for t in tracks]
        assert "t1" not in ids
        assert "t2" in ids

        __import__("pathlib").Path("/tmp/dj-rara-seen-test.json").unlink(missing_ok=True)


class TestFetchPlaylistProxyTracks:
    def _playlist_item(self, track):
        return {"track": track}

    def test_returns_empty_when_no_playlists_found(self, client, mock_sp):
        mock_sp.search.side_effect = lambda q, type, limit: {"playlists": {"items": []}}
        tracks, scores = client._fetch_playlist_proxy_tracks("chill", [], set())
        assert tracks == []
        assert scores == {}

    def test_counts_cooccurrence_across_playlists(self, client, mock_sp):
        t1 = _raw_track(id="t1", popularity=50)
        t2 = _raw_track(id="t2", popularity=50)
        mock_sp.search.side_effect = lambda q, type, limit: {
            "playlists": {"items": [{"id": "p1"}, {"id": "p2"}]}
        }
        # t1 in both playlists, t2 in only one
        mock_sp.playlist_tracks.side_effect = lambda p, limit: {
            "p1": {"items": [self._playlist_item(t1), self._playlist_item(t2)]},
            "p2": {"items": [self._playlist_item(t1)]},
        }[p]
        _, scores = client._fetch_playlist_proxy_tracks("chill", [], set())
        assert scores["t1"] > scores["t2"]

    def test_idf_normalization_penalizes_popular_tracks(self, client, mock_sp):
        # Both tracks appear in 2 playlists, but t_pop is very popular.
        # IDF normalization should score t_niche higher.
        t_pop   = _raw_track(id="pop",   popularity=90)
        t_niche = _raw_track(id="niche", popularity=5)
        mock_sp.search.side_effect = lambda q, type, limit: {
            "playlists": {"items": [{"id": "p1"}, {"id": "p2"}]}
        }
        mock_sp.playlist_tracks.side_effect = lambda p, limit: {
            "items": [self._playlist_item(t_pop), self._playlist_item(t_niche)]
        }
        _, scores = client._fetch_playlist_proxy_tracks("chill", [], set())
        assert scores["niche"] > scores["pop"]

    def test_filters_seen_track_ids(self, client, mock_sp):
        t1 = _raw_track(id="seen1", popularity=50)
        t2 = _raw_track(id="new1",  popularity=50)
        mock_sp.search.side_effect = lambda q, type, limit: {
            "playlists": {"items": [{"id": "p1"}]}
        }
        mock_sp.playlist_tracks.return_value = {
            "items": [self._playlist_item(t1), self._playlist_item(t2)]
        }
        _, scores = client._fetch_playlist_proxy_tracks("chill", [], seen_ids={"seen1"})
        assert "seen1" not in scores
        assert "new1" in scores

    def test_scores_normalized_to_one(self, client, mock_sp):
        t1 = _raw_track(id="t1", popularity=50)
        t2 = _raw_track(id="t2", popularity=50)
        mock_sp.search.side_effect = lambda q, type, limit: {
            "playlists": {"items": [{"id": "p1"}, {"id": "p2"}]}
        }
        mock_sp.playlist_tracks.side_effect = lambda p, limit: {
            "p1": {"items": [self._playlist_item(t1), self._playlist_item(t2)]},
            "p2": {"items": [self._playlist_item(t1)]},
        }[p]
        _, scores = client._fetch_playlist_proxy_tracks("chill", [], set())
        assert max(scores.values()) == pytest.approx(1.0)

    def test_handles_api_failure_gracefully(self, client, mock_sp):
        mock_sp.search.side_effect = Exception("network error")
        tracks, scores = client._fetch_playlist_proxy_tracks("chill", [], set())
        assert tracks == []
        assert scores == {}


class TestProxyIntegration:
    """Proxy signal reaches get_recommendations and influences ranking."""

    def test_proxy_tracks_included_in_results(self, client, mock_sp):
        proxy_track = _raw_track(id="proxy1", popularity=40)
        mock_sp.artist_top_tracks.return_value = {"tracks": []}
        mock_sp.current_user_saved_tracks.return_value = {"items": []}
        mock_sp.tracks.return_value = {"tracks": []}
        mock_sp.artist_related_artists.return_value = {"artists": []}
        mock_sp.audio_features.return_value = []
        mock_sp.artists.return_value = {"artists": []}
        mock_sp.search.side_effect = lambda q, type, limit: (
            {"artists": {"items": []}} if type == "artist"
            else {"playlists": {"items": [{"id": "p1"}]}} if type == "playlist"
            else {"tracks": {"items": []}}
        )
        mock_sp.playlist_tracks.return_value = {
            "items": [{"track": proxy_track}]
        }
        tracks = client.get_recommendations(
            seed_artist_ids=["a1"], seed_track_ids=[],
            mood="chill", genres=[], limit=10,
        )
        assert any(t.id == "proxy1" for t in tracks)

    def test_proxy_score_boosts_ranking_over_mood_equivalent(self, client, mock_sp, monkeypatch):
        # Both tracks are equally close to the chill mood target.
        # proxy_track also appears in curated playlists; plain_track does not.
        # The proxy signal should push proxy_track ahead within the discovery pool.
        #
        # Both tracks must be in the same pool (discovery) to compete on ranking.
        # We use discovery_ratio=1.0 so all slots come from discovery, and patch
        # random.shuffle so presentation order reflects the ranked result.
        import random
        monkeypatch.setattr(random, "shuffle", lambda x: None)

        proxy_track = _raw_track(id="proxy1", popularity=30)
        plain_track  = _raw_track(id="plain1",  popularity=30)
        mock_sp.artist_top_tracks.return_value = {"tracks": []}
        mock_sp.current_user_saved_tracks.return_value = {"items": []}
        mock_sp.tracks.return_value = {"tracks": []}
        mock_sp.artist_related_artists.return_value = {"artists": []}
        mock_sp.artists.return_value = {"artists": []}
        # plain_track enters discovery via text search; proxy_track via playlist proxy
        mock_sp.search.side_effect = lambda q, type, limit: (
            {"artists": {"items": []}} if type == "artist"
            else {"playlists": {"items": [{"id": "p1"}, {"id": "p2"}]}} if type == "playlist"
            else {"tracks": {"items": [plain_track]}}
        )
        mock_sp.playlist_tracks.return_value = {"items": [{"track": proxy_track}]}
        # Identical audio features → equal mood goodness; proxy signal is the tiebreaker
        mock_sp.audio_features.return_value = [
            {"id": "proxy1", "energy": 0.30, "valence": 0.60,
             "acousticness": 0.70, "tempo": 90.0},
            {"id": "plain1", "energy": 0.30, "valence": 0.60,
             "acousticness": 0.70, "tempo": 90.0},
        ]
        tracks = client.get_recommendations(
            seed_artist_ids=["a1"], seed_track_ids=[],
            mood="chill", genres=[], limit=2,
            discovery_ratio=1.0,  # all slots from discovery pool
        )
        ids = [t.id for t in tracks]
        assert ids.index("proxy1") < ids.index("plain1")


class TestCreatePlaylist:
    def test_returns_playlist_object(self, client, mock_sp):
        mock_sp.user_playlist_create.return_value = {
            "id": "p1", "name": "DJ Rara — chill",
            "external_urls": {"spotify": "https://open.spotify.com/playlist/p1"},
        }
        tracks = [Track("t1", "Song", ["Artist"], "Album", 80, None, "spotify:track:t1")]
        playlist = client.create_playlist(
            name="DJ Rara — chill", tracks=tracks,
            description="test", mood="chill", genres=["indie"],
        )
        assert isinstance(playlist, Playlist)
        assert playlist.id == "p1"
        assert playlist.mood == "chill"
        assert playlist.genres == ["indie"]

    def test_adds_tracks_to_playlist(self, client, mock_sp):
        mock_sp.user_playlist_create.return_value = {
            "id": "p1", "name": "Test",
            "external_urls": {"spotify": "https://example.com"},
        }
        tracks = [
            Track(f"t{i}", "Song", ["Artist"], "Album", 80, None, f"spotify:track:t{i}")
            for i in range(3)
        ]
        client.create_playlist("Test", tracks, "desc", "chill", [])
        mock_sp.playlist_add_items.assert_called_once_with(
            "p1", [f"spotify:track:t{i}" for i in range(3)]
        )


class TestGetUserPlaylists:
    def test_filters_by_prefix(self, client, mock_sp):
        mock_sp.current_user_playlists.return_value = {
            "items": [
                {"id": "p1", "name": "DJ Rara — chill", "tracks": {"total": 28},
                 "external_urls": {"spotify": "https://open.spotify.com/playlist/p1"}},
                {"id": "p2", "name": "My Morning Mix", "tracks": {"total": 10},
                 "external_urls": {"spotify": "https://example.com"}},
            ],
            "next": None,
        }
        playlists = client.get_user_playlists(name_prefix="DJ Rara")
        assert len(playlists) == 1
        assert playlists[0].id == "p1"

    def test_returns_empty_when_none_match(self, client, mock_sp):
        mock_sp.current_user_playlists.return_value = {
            "items": [
                {"id": "p1", "name": "Some Other Playlist", "tracks": {"total": 5},
                 "external_urls": {"spotify": "https://example.com"}},
            ],
            "next": None,
        }
        assert client.get_user_playlists(name_prefix="DJ Rara") == []


class TestRankingFallback:
    def test_missing_audio_is_neutral_not_worst(self, client, mock_sp, monkeypatch):
        TestGetRecommendations()._setup_mock(mock_sp, tracks=[
            _raw_track(id="poor"), _raw_track(id="unknown"), _raw_track(id="good"),
        ])
        monkeypatch.setattr("dj_rara.spotify_client.random.shuffle", lambda values: None)
        mock_sp.audio_features.return_value = [
            {"id": "poor", "energy": 1.0, "valence": 0.0, "acousticness": 0.0, "tempo": 200},
            {"id": "good", "energy": 0.3, "valence": 0.6, "acousticness": 0.7, "tempo": 90},
        ]
        tracks = client.get_recommendations(["a1"], [], "chill", [], limit=2)
        assert [t.id for t in tracks] == ["good", "unknown"]

    def test_ties_are_randomized_before_selection(self, client, mock_sp, monkeypatch):
        TestGetRecommendations()._setup_mock(mock_sp, tracks=[
            _raw_track(id="first"), _raw_track(id="last"),
        ])
        monkeypatch.setattr("dj_rara.spotify_client.random.shuffle", lambda values: values.reverse())
        tracks = client.get_recommendations(["a1"], [], "chill", [], limit=1)
        assert tracks[0].id == "last"

    def test_reserve_is_populated_and_skips_excluded(self, client, mock_sp, monkeypatch):
        from dj_rara.selection import RecommendationPool
        TestGetRecommendations()._setup_mock(mock_sp, tracks=[
            _raw_track(id="skipped"), _raw_track(id="a"), _raw_track(id="b"),
        ])
        monkeypatch.setattr("dj_rara.spotify_client.get_skipped_track_ids", lambda: {"skipped"})
        pool = RecommendationPool()
        tracks = client.get_recommendations(["a1"], [], "chill", [], limit=1, candidate_pool=pool)
        reserve = pool.take(10)
        assert len(tracks) == len(reserve) == 1
        assert {t.id for t in tracks + reserve} == {"a", "b"}

    def test_playlist_duplicates_do_not_inflate_score(self, client, mock_sp):
        mock_sp.search.return_value = {"playlists": {"items": [{"id": "p1"}]}}
        mock_sp.playlist_tracks.return_value = {"items": [
            {"track": _raw_track(id="a")}, {"track": _raw_track(id="a")},
            {"track": _raw_track(id="b")},
        ]}
        _, scores = client._fetch_playlist_proxy_tracks("chill", [], set())
        assert scores["a"] == scores["b"]

    def test_proxy_ranks_when_audio_unavailable(self, client, mock_sp, monkeypatch):
        TestGetRecommendations()._setup_mock(mock_sp, tracks=[_raw_track(id="plain")])
        monkeypatch.setattr("dj_rara.spotify_client.random.shuffle", lambda values: None)
        from dj_rara.spotify_client import _parse_track
        client._fetch_playlist_proxy_tracks = MagicMock(return_value=(
            [_parse_track(_raw_track(id="proxy"))], {"proxy": 1.0},
        ))
        tracks = client.get_recommendations(["a1"], [], "chill", [], limit=1, discovery_ratio=1)
        assert tracks[0].id == "proxy"


class TestGenreExplanations:
    def test_exact_genre_beats_better_mood_and_related_tag(self, client, mock_sp, monkeypatch):
        from dj_rara.selection import RecommendationPool
        TestGetRecommendations()._setup_mock(mock_sp, tracks=[
            _raw_track(id="related", artist_id="r"), _raw_track(id="exact", artist_id="e"),
        ])
        mock_sp.artists.return_value = {"artists": [
            {"id": "r", "genres": ["dream pop"]}, {"id": "e", "genres": [" Shoegaze "]},
        ]}
        mock_sp.audio_features.return_value = [{"id": "related", "energy": 0.3}]
        pool = RecommendationPool()
        tracks = client.get_recommendations(["a1"], [], "chill", ["shoegaze"], limit=1, candidate_pool=pool)
        assert tracks[0].id == "exact"
        assert "Artist genre matches: shoegaze" in pool.reasons["exact"]
        assert "Related artist genre: dream pop" in pool.reasons["related"]
        assert not any("Audio measurements" in reason for reason in pool.reasons["exact"])
        assert any("Audio measurements" in reason for reason in pool.reasons["related"])

    @pytest.mark.parametrize("tags,expected", [([], "metadata unavailable"), (["reggaeton"], "broader selection")])
    def test_fallback_explains_missing_or_nonmatching_metadata(self, client, mock_sp, tags, expected):
        from dj_rara.selection import RecommendationPool
        TestGetRecommendations()._setup_mock(mock_sp)
        mock_sp.artists.return_value = {"artists": [{"id": "a1", "genres": tags}]}
        pool = RecommendationPool()
        tracks = client.get_recommendations(["a1"], [], "chill", ["shoegaze"], candidate_pool=pool)
        assert tracks
        assert expected in pool.genre_notice
        assert not any("genre matches" in reason for reason in pool.reasons[tracks[0].id])

    def test_provenance_accumulates_without_inventing_mood_fit(self, client, mock_sp):
        from dj_rara.selection import RecommendationPool
        song = _raw_track(id="r1")
        TestGetRecommendations()._setup_mock(mock_sp, tracks=[song])
        mock_sp.current_user_saved_tracks.return_value = {"items": [{"track": song}]}
        mock_sp.search.side_effect = lambda q, type, limit: (
            {"playlists": {"items": [{"id": "p1"}, {"id": "p2"}]}} if type == "playlist"
            else {"tracks": {"items": []}}
        )
        mock_sp.playlist_tracks.return_value = {"items": [{"track": song}, {"track": song}]}
        pool = RecommendationPool()
        client.get_recommendations(["a1"], [], "chill", [], candidate_pool=pool)
        assert pool.reasons["r1"] == [
            "Top track from one of your seed artists", "In your saved tracks",
            "Appears in 2 matching public playlists",
        ]
