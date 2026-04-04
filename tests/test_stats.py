import pytest
from screens.stats import _bar, _genre_percentages, _avg_audio_features, BAR_WIDTH


class FakeArtist:
    def __init__(self, genres):
        self.genres = genres


# --- _bar tests ---

def test_bar_all_empty():
    result = _bar(0.0)
    assert result == "░" * BAR_WIDTH


def test_bar_all_filled():
    result = _bar(1.0)
    assert result == "█" * BAR_WIDTH


def test_bar_half():
    result = _bar(0.5)
    assert result == "█" * 14 + "░" * 14


def test_bar_custom_width():
    result = _bar(0.25, width=8)
    assert result == "█" * 2 + "░" * 6


# --- _genre_percentages tests ---

def test_genre_percentages_empty():
    result = _genre_percentages([])
    assert result == []


def test_genre_percentages_sorted_descending():
    artists = [
        FakeArtist(["pop", "rock"]),
        FakeArtist(["pop", "indie"]),
        FakeArtist(["pop"]),
        FakeArtist(["rock"]),
    ]
    result = _genre_percentages(artists)
    # Total genre counts: pop=3, rock=2, indie=1 → total=6
    genres = [g for g, _ in result]
    assert genres[0] == "pop"
    assert genres[1] == "rock"
    assert genres[2] == "indie"
    # Check percentages
    pcts = {g: pct for g, pct in result}
    assert abs(pcts["pop"] - 3 / 6) < 1e-9
    assert abs(pcts["rock"] - 2 / 6) < 1e-9
    assert abs(pcts["indie"] - 1 / 6) < 1e-9


# --- _avg_audio_features tests ---

def test_avg_audio_features_empty():
    result = _avg_audio_features({})
    assert result == {"energy": 0.0, "valence": 0.0, "danceability": 0.0, "acousticness": 0.0}


def test_avg_audio_features_single():
    features = {
        "id1": {"energy": 0.8, "valence": 0.6, "danceability": 0.4, "acousticness": 0.2}
    }
    result = _avg_audio_features(features)
    assert abs(result["energy"] - 0.8) < 1e-9
    assert abs(result["valence"] - 0.6) < 1e-9
    assert abs(result["danceability"] - 0.4) < 1e-9
    assert abs(result["acousticness"] - 0.2) < 1e-9


def test_avg_audio_features_multiple():
    features = {
        "id1": {"energy": 0.8, "valence": 0.6, "danceability": 0.4, "acousticness": 0.2},
        "id2": {"energy": 0.4, "valence": 0.2, "danceability": 0.8, "acousticness": 0.6},
    }
    result = _avg_audio_features(features)
    assert abs(result["energy"] - 0.6) < 1e-9
    assert abs(result["valence"] - 0.4) < 1e-9
    assert abs(result["danceability"] - 0.6) < 1e-9
    assert abs(result["acousticness"] - 0.4) < 1e-9
