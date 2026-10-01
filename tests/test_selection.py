from dj_rara.models import Track
from dj_rara.selection import RecommendationPool


def track(tid, artist="a", name=None, isrc=None):
    return Track(tid, name or tid, [artist], "album", 50, None,
                 f"spotify:track:{tid}", [artist], isrc)


def test_cap_applies_across_pools_and_filler():
    pool = RecommendationPool(
        familiar=[track("f1"), track("f2"), track("f3")],
        discovery=[track("d1"), track("d2", "b"), track("d3", "c")],
    )
    selected = pool.take(6)
    assert len(selected) == 4
    assert sum(t.artist_ids == ["a"] for t in selected) == 2


def test_ratio_and_reserve():
    pool = RecommendationPool(
        familiar=[track(f"f{i}", f"fa{i}") for i in range(10)],
        discovery=[track(f"d{i}", f"da{i}") for i in range(10)],
        discovery_ratio=0.75,
    )
    selected = pool.take(4)
    assert sum(t.id.startswith("d") for t in selected) == 3
    replacements = pool.take(4, retained=selected[:1])
    assert not {t.id for t in selected} & {t.id for t in replacements}


def test_deduplicates_recordings_but_preserves_versions():
    pool = RecommendationPool(familiar=[
        track("original", name="Song", isrc="abc"),
        track("reissue", name="Song remastered", isrc="ABC"),
        track("compilation", name="  SONG  "),
        track("live", name="Song (Live)"),
    ])
    assert [t.id for t in pool.take(10)] == ["original", "live"]
    assert pool.take(10) == []  # duplicate recordings cannot return on reroll


def test_collaborations_count_toward_each_artist():
    collaboration = track("collab", "b")
    collaboration.artist_ids = ["a", "b"]
    pool = RecommendationPool(discovery=[collaboration, track("other", "c")])
    selected = pool.take(1, retained=[track("a1"), track("a2")])
    assert [t.id for t in selected] == ["other"]
