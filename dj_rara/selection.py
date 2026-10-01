"""Selection and replacement from an already ranked recommendation pool."""

from collections import Counter
from dataclasses import dataclass, field

from .models import Track


def recording_keys(track: Track) -> set[tuple]:
    # Keep version suffixes: live recordings and remixes are distinct versions.
    normalize = lambda value: " ".join(value.casefold().split())
    keys = {("title", normalize(track.name), tuple(sorted(normalize(a) for a in track.artists)))}
    if track.isrc:
        keys.add(("isrc", track.isrc.upper()))
    return keys


def artist_keys(track: Track) -> set[str]:
    return set(track.artist_ids) or {a.casefold().strip() for a in track.artists}


@dataclass
class RecommendationPool:
    familiar: list[Track] = field(default_factory=list)
    discovery: list[Track] = field(default_factory=list)
    discovery_ratio: float = 0.5
    displayed_ids: set[str] = field(default_factory=set)
    displayed_recordings: set[tuple] = field(default_factory=set)

    def take(self, limit: int, retained: list[Track] | None = None,
             discovery_ratio: float | None = None) -> list[Track]:
        retained = retained or []
        counts = Counter(key for t in retained for key in artist_keys(t))
        used = self.displayed_ids | {t.id for t in retained}
        recordings = self.displayed_recordings.copy()
        for track in retained:
            recordings.update(recording_keys(track))
        chosen: list[Track] = []

        def add(pool: list[Track], quota: int) -> None:
            added = 0
            for track in pool:
                if added >= quota:
                    break
                artists = artist_keys(track)
                keys = recording_keys(track)
                if track.id in used or recordings & keys:
                    continue
                if any(counts[a] >= 2 for a in artists):
                    continue
                chosen.append(track)
                used.add(track.id)
                recordings.update(keys)
                counts.update(artists)
                added += 1

        ratio = self.discovery_ratio if discovery_ratio is None else discovery_ratio
        discovery_count = int(limit * max(0.0, min(ratio, 1.0)))
        add(self.familiar, limit - discovery_count)
        add(self.discovery, discovery_count)
        add(self.discovery + self.familiar, limit - len(chosen))
        self.displayed_ids.update(t.id for t in chosen)
        for track in chosen:
            self.displayed_recordings.update(recording_keys(track))
        return chosen
