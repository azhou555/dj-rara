import pytest
from unittest.mock import MagicMock
from models import Track, Artist


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
