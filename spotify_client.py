import random
import time
from datetime import date

import spotipy

from history import get_seen_track_ids
from models import Artist, Playlist, Track

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
        raw = _call_with_retry(lambda: self.sp.audio_features(track_ids))
        return {f["id"]: f for f in raw if f is not None}

    def get_recommendations(
        self,
        seed_artist_ids: list[str],
        seed_track_ids: list[str],
        mood: str,
        genres: list[str],
        limit: int = 30,
    ) -> list[Track]:
        features = mood_to_features(mood)
        seen_ids = get_seen_track_ids()
        results: list[Track] = []
        seen_in_session: set[str] = set()

        artists = list(seed_artist_ids)
        tracks_pool = list(seed_track_ids)
        random.shuffle(artists)
        random.shuffle(tracks_pool)

        # Reserve 1 genre seed slot if genres provided; rest split between artists/tracks
        genre_seeds = genres[:1] if genres else []
        remaining = 5 - len(genre_seeds)
        max_artists = min(3, remaining, len(artists))
        max_tracks = min(remaining - max_artists, len(tracks_pool))

        iterations = max((limit // 50) + 2, 3)

        for i in range(iterations):
            if len(results) >= limit:
                break

            a_start = (i * max(max_artists, 1)) % max(len(artists), 1)
            t_start = (i * max(max_tracks, 1)) % max(len(tracks_pool), 1)

            batch_artists = artists[a_start : a_start + max_artists]
            batch_tracks = tracks_pool[t_start : t_start + max_tracks]

            if not batch_artists and not batch_tracks and not genre_seeds:
                break

            params: dict = {"limit": min(100, limit), **features}
            if batch_artists:
                params["seed_artists"] = batch_artists
            if batch_tracks:
                params["seed_tracks"] = batch_tracks
            if genre_seeds:
                params["seed_genres"] = genre_seeds

            try:
                raw = _call_with_retry(lambda p=params: self.sp.recommendations(**p))
            except Exception:
                continue

            for item in raw["tracks"]:
                tid = item["id"]
                if tid not in seen_ids and tid not in seen_in_session:
                    results.append(_parse_track(item))
                    seen_in_session.add(tid)

        return results[:limit]

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
