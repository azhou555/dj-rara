import pytest
from unittest.mock import MagicMock
from models import Track, Artist, Playlist


@pytest.fixture
def mock_sp():
    sp = MagicMock()
    sp.current_user.return_value = {"id": "testuser", "display_name": "Test User"}
    return sp


@pytest.fixture
def client(mock_sp):
    from spotify_client import SpotifyClient
    return SpotifyClient(mock_sp)


def _raw_track(id="t1", name="Skinny Love", artist="Bon Iver",
               album="For Emma", popularity=91, preview_url="https://example.com/p.mp3"):
    return {
        "id": id, "name": name,
        "artists": [{"name": artist}],
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
        from spotify_client import mood_to_features
        f = mood_to_features("chill")
        assert f["target_energy"] == pytest.approx(0.30)
        assert f["target_valence"] == pytest.approx(0.60)
        assert f["target_acousticness"] == pytest.approx(0.70)

    def test_energetic(self):
        from spotify_client import mood_to_features
        assert mood_to_features("energetic")["target_energy"] == pytest.approx(0.85)

    def test_focus(self):
        from spotify_client import mood_to_features
        assert mood_to_features("focus")["target_energy"] == pytest.approx(0.50)

    def test_melancholy(self):
        from spotify_client import mood_to_features
        assert mood_to_features("melancholy")["target_energy"] == pytest.approx(0.25)

    def test_unknown_mood_raises(self):
        from spotify_client import mood_to_features
        with pytest.raises(ValueError, match="Unknown mood"):
            mood_to_features("groovy")


class TestGetRecommendations:
    def test_returns_track_objects(self, client, mock_sp):
        mock_sp.recommendations.return_value = {"tracks": [_raw_track(id="r1")]}
        tracks = client.get_recommendations(
            seed_artist_ids=["a1", "a2"],
            seed_track_ids=["t1"],
            mood="chill",
            genres=[],
            limit=10,
        )
        assert len(tracks) >= 1
        assert isinstance(tracks[0], Track)

    def test_passes_mood_audio_features(self, client, mock_sp):
        mock_sp.recommendations.return_value = {"tracks": [_raw_track()]}
        client.get_recommendations(
            seed_artist_ids=["a1"], seed_track_ids=[],
            mood="chill", genres=[], limit=5,
        )
        kwargs = mock_sp.recommendations.call_args[1]
        assert kwargs["target_energy"] == pytest.approx(0.30)
        assert kwargs["target_valence"] == pytest.approx(0.60)

    def test_includes_genre_seeds_when_provided(self, client, mock_sp):
        mock_sp.recommendations.return_value = {"tracks": [_raw_track()]}
        client.get_recommendations(
            seed_artist_ids=["a1", "a2"], seed_track_ids=[],
            mood="chill", genres=["indie folk"], limit=5,
        )
        kwargs = mock_sp.recommendations.call_args[1]
        assert "seed_genres" in kwargs
        assert "indie folk" in kwargs["seed_genres"]

    def test_deduplicates_results(self, client, mock_sp):
        dup = _raw_track(id="dup")
        mock_sp.recommendations.return_value = {"tracks": [dup, dup]}
        tracks = client.get_recommendations(
            seed_artist_ids=["a1"], seed_track_ids=[],
            mood="chill", genres=[], limit=10,
        )
        ids = [t.id for t in tracks]
        assert len(ids) == len(set(ids))


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
