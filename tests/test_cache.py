from dj_rara.cache import SessionCache


def test_expiry_and_values_are_isolated(monkeypatch):
    monkeypatch.setattr("dj_rara.cache.monotonic", lambda: 10)
    cache = SessionCache(ttl=5)
    original = {"genres": ["shoegaze"]}
    cache.put(("artist", "a"), original)
    original["genres"].clear()
    fetched = cache.get(("artist", "a"))
    fetched["genres"].append("noise pop")
    assert cache.get(("artist", "a")) == {"genres": ["shoegaze"]}
    monkeypatch.setattr("dj_rara.cache.monotonic", lambda: 15)
    assert cache.get(("artist", "a")) is None


def test_bound_evicts_least_recently_used_and_caches_empty_results():
    cache = SessionCache(max_entries=2)
    cache.put(("a",), [])
    cache.put(("b",), {})
    assert cache.get(("a",)) == []
    cache.put(("c",), {"tracks": []})
    assert cache.get(("b",)) is None
    assert cache.get(("a",)) == []
    assert cache.get(("c",)) == {"tracks": []}
