import random
import time
from datetime import date

import spotipy

from .history import get_seen_track_ids
from .models import Artist, Playlist, Track

# Spotify's artist genre tags often don't use the exact genre label a user would
# expect. This map expands each explore genre to the related Spotify tags it
# commonly falls under, so the post-filter can match tracks from artists that
# are genuinely in the genre even if Spotify uses a different label.
GENRE_SYNONYMS: dict[str, list[str]] = {
    "afrobeats":        ["afrobeats", "afropop", "afro soul", "highlife"],
    "ambient":          ["ambient", "drone", "dark ambient", "new age"],
    "bossa nova":       ["bossa nova", "mpb", "samba", "brazilian jazz"],
    "cumbia":           ["cumbia", "latin", "tropical"],
    "dark ambient":     ["dark ambient", "ambient", "drone", "industrial"],
    "drum and bass":    ["drum and bass", "dnb", "liquid funk", "jungle"],
    "flamenco":         ["flamenco", "nuevo flamenco", "spanish classical"],
    "footwork":         ["footwork", "chicago footwork", "juke", "ghetto house"],
    "garage rock":      ["garage rock", "indie rock", "proto-punk"],
    "gospel":           ["gospel", "christian music", "contemporary christian"],
    "grime":            ["grime", "uk hip hop", "uk garage"],
    "hyperpop":         ["hyperpop", "digicore", "bubblegum bass", "pc music"],
    "j-pop":            ["j-pop", "japanese pop", "city pop"],
    "k-indie":          ["k-indie", "korean indie", "k-pop"],
    "latin jazz":       ["latin jazz", "latin", "afro-cuban jazz"],
    "lo-fi beats":      ["lo-fi beats", "lo-fi", "chillhop", "lo-fi hip hop"],
    "math rock":        ["math rock", "post-rock", "midwest emo", "progressive rock"],
    "modal jazz":       ["modal jazz", "post-bop", "jazz"],
    "neo soul":         ["neo soul", "r&b", "soul", "contemporary r&b"],
    "new wave":         ["new wave", "post-punk", "synth-pop", "art rock"],
    "noise rock":       ["noise rock", "post-punk", "art punk", "no wave"],
    "post-bop":         ["post-bop", "bebop", "cool jazz", "hard bop", "jazz"],
    "psychedelic rock": ["psychedelic rock", "psychedelia", "neo-psychedelia", "acid rock"],
    "reggaeton":        ["reggaeton", "latin trap", "dembow"],
    "salsa":            ["salsa", "tropical", "cumbia", "latin"],
    "shoegaze":         ["shoegaze", "dream pop", "noise pop", "neo-psychedelia"],
    "soca":             ["soca", "calypso", "caribbean"],
    "soul jazz":        ["soul jazz", "jazz", "funk", "hard bop"],
    "synth-pop":        ["synth-pop", "new wave", "electropop", "synthpop"],
    "turkish folk":     ["turkish folk", "halk muzigi", "anatolian rock"],
    "city pop":         ["city pop", "j-pop", "japanese pop", "japanese city pop"],
    "desert blues":     ["desert blues", "blues", "tuareg"],
    "electro swing":    ["electro swing", "swing", "jazz", "electronica"],
    "funk carioca":     ["funk carioca", "baile funk", "funk"],
    "mbaqanga":         ["mbaqanga", "afrobeat", "south african"],
}


def _expand_genres(genres: list[str]) -> set[str]:
    """Expand genre labels to include Spotify synonym tags."""
    expanded: set[str] = set()
    for g in genres:
        expanded.update(GENRE_SYNONYMS.get(g, [g]))
    return expanded


def _mood_score(features: dict | None, targets: dict[str, float]) -> float:
    """Mean absolute deviation from mood audio feature targets.

    Lower = closer match. Returns 1.0 (worst) for tracks with no feature data.
    Tempo is normalized to [0, 1] by dividing by 200 BPM before comparison.
    """
    if not features:
        return 1.0
    checks = [
        ("energy",       "target_energy",       1.0),
        ("valence",      "target_valence",       1.0),
        ("acousticness", "target_acousticness",  1.0),
        ("tempo",        "target_tempo",         200.0),
    ]
    total, count = 0.0, 0
    for feature, target_key, scale in checks:
        if target_key in targets and feature in features:
            total += abs(features[feature] / scale - targets[target_key] / scale)
            count += 1
    return total / count if count else 1.0


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


def mood_to_features(mood: str) -> dict[str, float]:
    if mood not in MOOD_FEATURES:
        raise ValueError(f"Unknown mood: {mood!r}. Choose from {list(MOOD_FEATURES)}")
    return MOOD_FEATURES[mood].copy()


# Weight of the public-playlist co-occurrence signal in the blended ranking.
# The complement (1 - PROXY_BLEND_WEIGHT) goes to audio-feature mood proximity.
PROXY_BLEND_WEIGHT: float = 0.4


def _parse_track(raw: dict) -> Track:
    return Track(
        id=raw["id"],
        name=raw["name"],
        artists=[a["name"] for a in raw["artists"]],
        album=raw["album"]["name"],
        popularity=raw["popularity"],
        preview_url=raw.get("preview_url"),
        uri=raw["uri"],
        artist_ids=[a["id"] for a in raw["artists"] if "id" in a],
    )


def _parse_artist(raw: dict) -> Artist:
    return Artist(
        id=raw["id"],
        name=raw["name"],
        genres=raw.get("genres", []),
        popularity=raw.get("popularity", 0),
    )


def _call_with_retry(fn, max_retries: int = 3):
    """Call fn(), retrying on HTTP 429 rate limit with exponential backoff."""
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
        if not track_ids:
            return {}
        result: dict[str, dict] = {}
        for i in range(0, len(track_ids), 100):
            batch = track_ids[i : i + 100]
            try:
                raw = _call_with_retry(lambda b=batch: self.sp.audio_features(b))
                result.update({f["id"]: f for f in raw if f is not None})
            except Exception:
                pass
        return result

    def _fetch_playlist_proxy_tracks(
        self,
        mood: str,
        genres: list[str],
        seen_ids: set[str],
        max_playlists: int = 8,
    ) -> tuple[list[Track], dict[str, float]]:
        """Crowd-validate tracks via public playlist co-occurrence.

        Searches public playlists for the mood/genre context, counts how many
        playlists each track appears in (co-occurrence), then applies IDF-style
        normalization to penalize globally popular tracks in favour of tracks
        that are specifically curated into this context.

        Returns (tracks, proxy_scores) where proxy_scores maps track_id to a
        normalized [0, 1] score — higher means stronger contextual signal.
        """
        queries: list[str] = []
        for genre in genres[:2]:
            queries.append(f"{genre} {mood}")
        if not queries:
            queries = [mood]

        playlist_ids: list[str] = []
        seen_playlist_ids: set[str] = set()
        for query in queries[:3]:
            try:
                raw = _call_with_retry(
                    lambda q=query: self.sp.search(q=q, type="playlist", limit=5)
                )
                for item in raw["playlists"]["items"]:
                    if item and item["id"] not in seen_playlist_ids:
                        playlist_ids.append(item["id"])
                        seen_playlist_ids.add(item["id"])
            except Exception:
                continue

        cooc: dict[str, int] = {}
        track_objects: dict[str, Track] = {}

        for pid in playlist_ids[:max_playlists]:
            try:
                raw = _call_with_retry(
                    lambda p=pid: self.sp.playlist_tracks(p, limit=50)
                )
                for item in raw["items"]:
                    if not item or not item.get("track"):
                        continue
                    t = item["track"]
                    tid = t.get("id")
                    if not tid or tid in seen_ids:
                        continue
                    cooc[tid] = cooc.get(tid, 0) + 1
                    if tid not in track_objects:
                        track_objects[tid] = _parse_track(t)
            except Exception:
                continue

        if not cooc:
            return [], {}

        # IDF-style normalization: divide co-occurrence count by a popularity
        # weight so ubiquitously popular tracks don't dominate. ε=0.1 prevents
        # division by zero and smooths tracks with near-zero Spotify popularity.
        raw_scores: dict[str, float] = {}
        for tid, count in cooc.items():
            popularity = track_objects[tid].popularity
            raw_scores[tid] = count / (max(popularity, 1) / 100.0 + 0.1)

        max_raw = max(raw_scores.values())
        proxy_scores = {tid: s / max_raw for tid, s in raw_scores.items()}
        return list(track_objects.values()), proxy_scores

    def get_recommendations(
        self,
        seed_artist_ids: list[str],
        seed_track_ids: list[str],
        mood: str,
        genres: list[str],
        limit: int = 30,
        discovery_ratio: float = 0.5,
    ) -> list[Track]:
        # Spotify deprecated /recommendations for new apps in late 2024.
        # Strategy: split into "familiar" pool (artist tops + saved + user tops)
        # and "discovery" pool (search + related artists). discovery_ratio controls
        # the mix. Both pools are sorted by mood-feature proximity before selection.
        seen_ids = get_seen_track_ids()
        familiar: list[Track] = []
        discovery: list[Track] = []
        familiar_ids: set[str] = set()
        discovery_ids: set[str] = set()

        # Pre-compute expanded genres once — shared by related-artist traversal
        # and genre post-filter so we don't expand twice.
        expanded: set[str] = _expand_genres(genres) if genres else set()

        def _add_familiar(item: dict) -> None:
            if not item:
                return
            tid = item.get("id")
            if tid and tid not in seen_ids and tid not in familiar_ids and tid not in discovery_ids:
                familiar.append(_parse_track(item))
                familiar_ids.add(tid)

        def _add_discovery(item: dict) -> None:
            if not item:
                return
            tid = item.get("id")
            if tid and tid not in seen_ids and tid not in familiar_ids and tid not in discovery_ids:
                discovery.append(_parse_track(item))
                discovery_ids.add(tid)

        # --- Familiar pool ---
        artist_ids = list(seed_artist_ids)
        random.shuffle(artist_ids)
        for artist_id in artist_ids[:8]:
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

        # --- Discovery pool: mood-keyed text search ---
        MOOD_QUERIES = {
            "chill":      ["chill acoustic", "lo-fi indie", "mellow vibes"],
            "energetic":  ["high energy rock", "upbeat dance", "power pop"],
            "focus":      ["focus instrumental", "ambient study", "concentration"],
            "melancholy": ["sad indie folk", "melancholy alternative", "emotional"],
        }
        queries = list(MOOD_QUERIES.get(mood, [mood]))
        for genre in genres[:2]:
            queries.insert(0, f'genre:"{genre}" {mood}')

        for query in queries[:4]:
            try:
                raw = _call_with_retry(lambda q=query: self.sp.search(q=q, type="track", limit=50))
                for item in raw["tracks"]["items"]:
                    _add_discovery(item)
            except Exception:
                continue

        # --- Discovery pool: genre-targeted artist search ---
        # Asks Spotify which artists it classifies under the genre and pulls their
        # top tracks. More reliable than track-level text search for niche genres.
        if genres:
            for genre in genres[:2]:
                try:
                    raw = _call_with_retry(
                        lambda g=genre: self.sp.search(q=f'genre:"{g}"', type="artist", limit=10)
                    )
                    for artist in raw["artists"]["items"][:4]:
                        try:
                            tops = _call_with_retry(
                                lambda a=artist["id"]: self.sp.artist_top_tracks(a)
                            )
                            for item in tops["tracks"][:4]:
                                _add_discovery(item)
                        except Exception:
                            continue
                except Exception:
                    continue

        # --- Discovery pool: related-artist traversal ---
        # Hop one degree from seed artists to surface musically adjacent artists.
        # When genres are selected, only follow edges to genre-matching artists so
        # the traversal stays in the right musical neighborhood.
        related_seen: set[str] = set(seed_artist_ids)
        for seed_id in seed_artist_ids[:3]:
            try:
                raw = _call_with_retry(lambda a=seed_id: self.sp.artist_related_artists(a))
                related = raw["artists"]
                if expanded:
                    related = [a for a in related if expanded & set(a.get("genres", []))]
                for artist in related[:3]:
                    if artist["id"] in related_seen:
                        continue
                    related_seen.add(artist["id"])
                    try:
                        tops = _call_with_retry(
                            lambda a=artist["id"]: self.sp.artist_top_tracks(a)
                        )
                        for item in tops["tracks"][:4]:
                            _add_discovery(item)
                    except Exception:
                        continue
            except Exception:
                continue

        # --- Public playlist proxy ---
        # Mine crowd-curation signal from public playlists matching the
        # mood/genre context. Tracks that appear across multiple playlists
        # receive an IDF-normalized co-occurrence score that blends with
        # audio-feature mood proximity in the final ranking step below.
        proxy_tracks, proxy_scores = self._fetch_playlist_proxy_tracks(
            mood, genres, seen_ids
        )
        for t in proxy_tracks:
            if t.id not in familiar_ids and t.id not in discovery_ids:
                discovery.append(t)
                discovery_ids.add(t.id)

        # --- Genre post-filter (partial match with synonym expansion) ---
        # Expands each genre to related Spotify tags before matching so artists
        # like Slowdive (tagged "dream pop") pass the shoegaze filter.
        # Falls back to unfiltered pools only if nothing matches at all.
        if genres:
            all_candidates = familiar + [t for t in discovery if t.id not in familiar_ids]
            all_artist_ids = list({aid for t in all_candidates for aid in t.artist_ids})
            artist_genres_map: dict[str, list[str]] = {}
            for i in range(0, len(all_artist_ids), 50):
                batch = all_artist_ids[i : i + 50]
                try:
                    raw = _call_with_retry(lambda b=batch: self.sp.artists(b))
                    for a in raw["artists"]:
                        if a:
                            artist_genres_map[a["id"]] = a.get("genres", [])
                except Exception:
                    pass

            def _genre_matches(track: Track) -> bool:
                return any(
                    expanded & set(artist_genres_map.get(aid, []))
                    for aid in track.artist_ids
                )

            f_filtered = [t for t in familiar if _genre_matches(t)]
            d_filtered = [t for t in discovery if _genre_matches(t)]
            if f_filtered or d_filtered:
                familiar = f_filtered
                discovery = d_filtered

        # --- Blended ranking: mood proximity + playlist proxy signal ---
        # mood_goodness = 1 - _mood_score (converts cost→goodness, both in [0,1]).
        # proxy_scores maps track_id → IDF-normalized co-occurrence [0,1]; 0.0
        # for tracks not found in any proxy playlist.
        # PROXY_BLEND_WEIGHT controls how much crowd-curation pulls against
        # audio-feature mood proximity. Both pools are sorted descending so the
        # best combined candidates rise to the top before the ratio mix.
        mood_targets = MOOD_FEATURES.get(mood, {})
        all_ids = [t.id for t in familiar] + [t.id for t in discovery]
        features_map = self.get_audio_features(all_ids) if mood_targets else {}

        def _rank(t: Track) -> float:
            mood_goodness = 1.0 - _mood_score(features_map.get(t.id), mood_targets)
            return (1.0 - PROXY_BLEND_WEIGHT) * mood_goodness + PROXY_BLEND_WEIGHT * proxy_scores.get(t.id, 0.0)

        familiar.sort(key=_rank, reverse=True)
        discovery.sort(key=_rank, reverse=True)

        # Mix pools according to discovery_ratio (sorted order drives selection;
        # shuffle at the end handles presentation randomness)
        n_discovery = int(limit * discovery_ratio)
        n_familiar = limit - n_discovery
        mixed = familiar[:n_familiar] + discovery[:n_discovery]
        if len(mixed) < limit:
            used = {t.id for t in mixed}
            filler = [t for t in (discovery + familiar) if t.id not in used]
            mixed += filler[:limit - len(mixed)]
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
