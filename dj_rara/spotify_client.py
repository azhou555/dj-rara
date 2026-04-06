import random
import time
from datetime import date

import spotipy

from .history import get_seen_track_ids, get_skipped_track_ids, get_taste_profile
from .models import Artist, Playlist, Track

# ---------------------------------------------------------------------------
# Mood feature targets  (used by mood_to_features() for external callers)
# ---------------------------------------------------------------------------

MOOD_FEATURES: dict[str, dict[str, float]] = {
    "chill":      {"target_energy": 0.30, "target_valence": 0.60,
                   "target_tempo": 90.0,  "target_acousticness": 0.70},
    "energetic":  {"target_energy": 0.85, "target_valence": 0.75,
                   "target_tempo": 140.0, "target_acousticness": 0.10},
    "focus":      {"target_energy": 0.50, "target_valence": 0.40,
                   "target_tempo": 110.0, "target_acousticness": 0.50},
    "melancholy": {"target_energy": 0.25, "target_valence": 0.20,
                   "target_tempo": 80.0,  "target_acousticness": 0.60},
}

# ---------------------------------------------------------------------------
# Scoring constants
# ---------------------------------------------------------------------------

# Normalized audio-feature targets for content-based scoring.
# Keys must match Spotify audio-features response keys (all 0-1 except tempo).
MOOD_TARGETS: dict[str, dict[str, float]] = {
    "chill":      {"energy": 0.30, "valence": 0.60, "acousticness": 0.70,
                   "danceability": 0.50, "instrumentalness": 0.20},
    "energetic":  {"energy": 0.85, "valence": 0.75, "acousticness": 0.10,
                   "danceability": 0.80, "instrumentalness": 0.05},
    "focus":      {"energy": 0.50, "valence": 0.40, "acousticness": 0.50,
                   "danceability": 0.40, "instrumentalness": 0.55},
    "melancholy": {"energy": 0.25, "valence": 0.20, "acousticness": 0.60,
                   "danceability": 0.30, "instrumentalness": 0.25},
}

# Features included in the taste-profile cosine similarity calculation.
_TASTE_KEYS = ["energy", "valence", "acousticness", "danceability", "instrumentalness"]

# Max tracks from any single artist in the final recommendation list.
_MAX_PER_ARTIST = 3

# Build pools this many times larger than the requested limit before scoring.
_POOL_MULTIPLIER = 3


def mood_to_features(mood: str) -> dict[str, float]:
    if mood not in MOOD_FEATURES:
        raise ValueError(f"Unknown mood: {mood!r}. Choose from {list(MOOD_FEATURES)}")
    return MOOD_FEATURES[mood].copy()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_track(raw: dict) -> Track:
    return Track(
        id=raw["id"],
        name=raw["name"],
        artists=[a["name"] for a in raw["artists"]],
        album=raw["album"]["name"],
        popularity=raw["popularity"],
        preview_url=raw.get("preview_url"),
        uri=raw["uri"],
    )


def _parse_artist(raw: dict) -> Artist:
    return Artist(
        id=raw["id"],
        name=raw["name"],
        genres=raw.get("genres", []),
        popularity=raw.get("popularity", 0),
    )


def _call_with_retry(fn, max_retries: int = 3):
    """Call fn(), retrying on HTTP 429 rate-limit with exponential back-off."""
    for attempt in range(max_retries):
        try:
            return fn()
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 429 and attempt < max_retries - 1:
                wait = int(e.headers.get("Retry-After", 2 ** attempt))
                time.sleep(wait)
            else:
                raise
        except Exception:
            raise


# ---------------------------------------------------------------------------
# Scoring engine
# ---------------------------------------------------------------------------

def _mood_score(features: dict, mood: str) -> float:
    """0-1 score for how closely a track's audio features match the mood target.

    Uses mean absolute deviation across all target keys, inverted so that
    a perfect match returns 1.0 and maximum deviation returns 0.0.
    """
    targets = MOOD_TARGETS.get(mood, {})
    if not targets or not features:
        return 0.5
    diffs = [abs(features.get(k, 0.5) - v) for k, v in targets.items()]
    return 1.0 - (sum(diffs) / len(diffs))


def _cosine_similarity(a: dict, b: dict) -> float:
    """Cosine similarity between two feature dicts over ``_TASTE_KEYS``."""
    dot = sum(a.get(k, 0.0) * b.get(k, 0.0) for k in _TASTE_KEYS)
    mag_a = sum(a.get(k, 0.0) ** 2 for k in _TASTE_KEYS) ** 0.5
    mag_b = sum(b.get(k, 0.0) ** 2 for k in _TASTE_KEYS) ** 0.5
    if mag_a < 1e-9 or mag_b < 1e-9:
        return 0.0
    return dot / (mag_a * mag_b)


def _score_candidates(
    tracks: list[Track],
    features_map: dict[str, dict],
    mood: str,
    taste_profile: dict[str, float],
) -> list[tuple[float, Track]]:
    """Return ``(score, track)`` pairs sorted descending by score.

    Scoring strategy:
    - **No taste data** (< 3 kept tracks): 65 % mood match + 35 % popularity.
    - **With taste data**: 35 % mood match + 45 % cosine similarity to taste
      profile + 20 % popularity.

    A tiny Gaussian jitter (σ = 0.02) is added so rankings vary slightly
    across sessions, preventing the exact same list from appearing every time.
    """
    has_taste = bool(taste_profile)
    scored: list[tuple[float, Track]] = []
    for track in tracks:
        feats = features_map.get(track.id, {})
        mood_s = _mood_score(feats, mood)
        pop_s = track.popularity / 100.0
        if has_taste and feats:
            taste_s = _cosine_similarity(feats, taste_profile)
            score = 0.35 * mood_s + 0.45 * taste_s + 0.20 * pop_s
        else:
            score = 0.65 * mood_s + 0.35 * pop_s
        score += random.gauss(0, 0.02)  # jitter for variety
        scored.append((score, track))
    return sorted(scored, key=lambda x: x[0], reverse=True)


def _apply_artist_diversity(
    scored: list[tuple[float, Track]], n: int
) -> list[Track]:
    """Pick up to *n* tracks from a scored list, capping at ``_MAX_PER_ARTIST``
    per artist to keep the results varied."""
    selected: list[Track] = []
    artist_counts: dict[str, int] = {}
    for _, track in scored:
        artist = track.artists[0] if track.artists else "__unknown__"
        if artist_counts.get(artist, 0) < _MAX_PER_ARTIST:
            selected.append(track)
            artist_counts[artist] = artist_counts.get(artist, 0) + 1
        if len(selected) >= n:
            break
    return selected


# ---------------------------------------------------------------------------
# SpotifyClient
# ---------------------------------------------------------------------------

class SpotifyClient:
    def __init__(self, sp):
        self.sp = sp
        self.user_id: str = sp.current_user()["id"]

    def get_top_tracks(self, time_range: str = "medium_term", limit: int = 50) -> list[Track]:
        results = _call_with_retry(
            lambda: self.sp.current_user_top_tracks(
                limit=min(limit, 50), offset=0, time_range=time_range
            )
        )
        return [_parse_track(t) for t in results["items"]][:limit]

    def get_top_artists(self, time_range: str = "medium_term", limit: int = 50) -> list[Artist]:
        results = _call_with_retry(
            lambda: self.sp.current_user_top_artists(
                limit=min(limit, 50), offset=0, time_range=time_range
            )
        )
        return [_parse_artist(a) for a in results["items"]][:limit]

    def get_followed_artists(self, limit: int = 50) -> list[Artist]:
        artists: list[Artist] = []
        results = _call_with_retry(
            lambda: self.sp.current_user_followed_artists(limit=min(limit, 50))
        )
        while results and len(artists) < limit:
            artists.extend([_parse_artist(a) for a in results["artists"]["items"]])
            if results["artists"]["next"] and len(artists) < limit:
                current = results["artists"]
                results = _call_with_retry(lambda r=current: self.sp.next(r))
            else:
                break
        return artists[:limit]

    def get_audio_features(self, track_ids: list[str]) -> dict[str, dict]:
        """Batch-fetch audio features for up to any number of tracks (auto-chunks by 100)."""
        if not track_ids:
            return {}
        result: dict[str, dict] = {}
        try:
            for i in range(0, len(track_ids), 100):
                chunk = track_ids[i : i + 100]
                raw = _call_with_retry(lambda c=chunk: self.sp.audio_features(c))
                if raw:
                    result.update({f["id"]: f for f in raw if f is not None})
        except Exception:
            pass
        return result

    def get_recommendations(
        self,
        seed_artist_ids: list[str],
        seed_track_ids: list[str],
        mood: str,
        genres: list[str],
        limit: int = 30,
        discovery_ratio: float = 0.5,
    ) -> list[Track]:
        """Return *limit* scored, diversity-filtered track recommendations.

        Algorithm (content-based filtering):
        1. Build a **familiar** pool (artist top-tracks, saved library, user tops)
           and a **discovery** pool (mood/genre keyword searches) — each targeting
           ``limit × _POOL_MULTIPLIER`` candidates.
        2. Batch-fetch Spotify audio features for every candidate.
        3. Score each pool using mood-feature alignment + learned taste profile
           + popularity.  A ±2 % Gaussian jitter adds session-to-session variety.
        4. Apply per-artist diversity cap (``_MAX_PER_ARTIST``).
        5. Split the final list according to ``discovery_ratio``, fill gaps from
           the opposite pool, then shuffle display order.

        Tracks in ``seen_track_ids`` **or** ``skipped_track_ids`` are excluded
        from the candidate pools entirely so they never resurface.
        """
        seen_ids = get_seen_track_ids()
        skipped_ids = get_skipped_track_ids()
        excluded = seen_ids | skipped_ids
        taste_profile = get_taste_profile(mood=mood)

        familiar: list[Track] = []
        discovery: list[Track] = []
        familiar_ids: set[str] = set()
        discovery_ids: set[str] = set()

        def _add_familiar(item: dict) -> None:
            if not item:
                return
            tid = item.get("id")
            if tid and tid not in excluded and tid not in familiar_ids and tid not in discovery_ids:
                familiar.append(_parse_track(item))
                familiar_ids.add(tid)

        def _add_discovery(item: dict) -> None:
            if not item:
                return
            tid = item.get("id")
            if tid and tid not in excluded and tid not in familiar_ids and tid not in discovery_ids:
                discovery.append(_parse_track(item))
                discovery_ids.add(tid)

        # --- Familiar pool ---
        artist_ids = list(seed_artist_ids)
        random.shuffle(artist_ids)
        for artist_id in artist_ids[:10]:
            try:
                raw = _call_with_retry(lambda a=artist_id: self.sp.artist_top_tracks(a))
                for item in raw["tracks"]:
                    _add_familiar(item)
            except Exception:
                continue

        try:
            raw = _call_with_retry(lambda: self.sp.current_user_saved_tracks(limit=50))
            for item in raw["items"]:
                if item.get("track"):
                    _add_familiar(item["track"])
        except Exception:
            pass

        if seed_track_ids:
            try:
                raw = _call_with_retry(lambda ids=seed_track_ids[:50]: self.sp.tracks(ids))
                for item in raw["tracks"]:
                    _add_familiar(item)
            except Exception:
                pass

        # --- Discovery pool ---
        MOOD_QUERIES: dict[str, list[str]] = {
            "chill":      ["chill acoustic", "lo-fi indie", "mellow vibes", "indie chill"],
            "energetic":  ["high energy rock", "upbeat dance", "power pop", "energetic hits"],
            "focus":      ["focus instrumental", "ambient study", "concentration", "deep work music"],
            "melancholy": ["sad indie folk", "melancholy alternative", "emotional ballads", "heartbreak songs"],
        }
        queries = list(MOOD_QUERIES.get(mood, [mood]))
        for genre in genres[:3]:
            queries.insert(0, f"{genre} {mood}")

        for query in queries[:5]:
            try:
                raw = _call_with_retry(lambda q=query: self.sp.search(q=q, type="track", limit=50))
                for item in raw["tracks"]["items"]:
                    _add_discovery(item)
            except Exception:
                continue

        # --- Score each pool independently ---
        all_ids = [t.id for t in familiar + discovery]
        features_map = self.get_audio_features(all_ids)

        scored_familiar = _score_candidates(familiar, features_map, mood, taste_profile)
        scored_discovery = _score_candidates(discovery, features_map, mood, taste_profile)

        # --- Apply discovery_ratio split with artist diversity ---
        n_discovery = int(limit * discovery_ratio)
        n_familiar = limit - n_discovery

        selected_familiar = _apply_artist_diversity(scored_familiar, n_familiar)
        selected_discovery = _apply_artist_diversity(scored_discovery, n_discovery)

        mixed = selected_familiar + selected_discovery

        # Fill if either pool was short
        if len(mixed) < limit:
            used_ids = {t.id for t in mixed}
            filler = [
                t for _, t in (scored_discovery + scored_familiar)
                if t.id not in used_ids
            ]
            mixed += filler[: limit - len(mixed)]

        # Shuffle display order so high-scoring tracks aren't always at the top
        random.shuffle(mixed)
        return mixed[:limit]

    def create_playlist(
        self,
        name: str,
        tracks: list[Track],
        description: str,
        mood: str,
        genres: list[str],
        public: bool = False,
    ) -> Playlist:
        raw = _call_with_retry(
            lambda: self.sp.user_playlist_create(
                user=self.user_id, name=name, public=public, description=description
            )
        )
        track_uris = [t.uri for t in tracks]
        for i in range(0, len(track_uris), 100):
            batch = track_uris[i : i + 100]
            _call_with_retry(lambda b=batch: self.sp.playlist_add_items(raw["id"], b))
        return Playlist(
            id=raw["id"],
            name=name,
            url=raw["external_urls"]["spotify"],
            track_count=len(tracks),
            created_at=date.today().isoformat(),
            mood=mood,
            genres=genres,
        )

    def get_user_playlists(self, name_prefix: str = "DJ Rara") -> list[Playlist]:
        playlists: list[Playlist] = []
        results = _call_with_retry(lambda: self.sp.current_user_playlists(limit=50))
        while results:
            for item in results["items"]:
                if item["name"].startswith(name_prefix):
                    playlists.append(Playlist(
                        id=item["id"],
                        name=item["name"],
                        url=item["external_urls"]["spotify"],
                        track_count=item["tracks"]["total"],
                        created_at="",
                        mood="",
                        genres=[],
                    ))
            if results.get("next"):
                current = results
                results = _call_with_retry(lambda r=current: self.sp.next(r))
            else:
                break
        return playlists
