"""
Spotify Recommendation Engine
Generates personalized music recommendations based on user's listening habits
"""

from typing import List, Dict, Set
import random


class SpotifyRecommendationEngine:
    """Core recommendation engine for Spotify"""

    def __init__(self, spotify_client):
        """
        Initialize the recommendation engine

        Args:
            spotify_client: Authenticated Spotipy client
        """
        self.sp = spotify_client
        self.user_id = self.sp.current_user()['id']

    def get_followed_artists(self, limit: int = 50) -> List[Dict]:
        """
        Fetch user's followed artists

        Args:
            limit: Maximum number of artists to fetch

        Returns:
            List of artist dictionaries
        """
        print(f"Fetching followed artists...")
        artists = []
        results = self.sp.current_user_followed_artists(limit=limit)

        while results:
            artists.extend(results['artists']['items'])
            if results['artists']['next']:
                results = self.sp.next(results['artists'])
            else:
                break

        print(f"Found {len(artists)} followed artists")
        return artists

    def get_top_tracks(self, time_range: str = 'medium_term', limit: int = 50) -> List[Dict]:
        """
        Fetch user's top tracks

        Args:
            time_range: Time range for top tracks ('short_term', 'medium_term', 'long_term')
            limit: Maximum number of tracks to fetch

        Returns:
            List of track dictionaries
        """
        print(f"Fetching top tracks (time range: {time_range})...")
        tracks = []
        offset = 0

        while len(tracks) < limit:
            results = self.sp.current_user_top_tracks(
                limit=min(50, limit - len(tracks)),
                offset=offset,
                time_range=time_range
            )

            if not results['items']:
                break

            tracks.extend(results['items'])
            offset += len(results['items'])

            if len(results['items']) < 50:
                break

        print(f"Found {len(tracks)} top tracks")
        return tracks

    def get_top_artists(self, time_range: str = 'medium_term', limit: int = 50) -> List[Dict]:
        """
        Fetch user's top artists

        Args:
            time_range: Time range for top artists ('short_term', 'medium_term', 'long_term')
            limit: Maximum number of artists to fetch

        Returns:
            List of artist dictionaries
        """
        print(f"Fetching top artists (time range: {time_range})...")
        artists = []
        offset = 0

        while len(artists) < limit:
            results = self.sp.current_user_top_artists(
                limit=min(50, limit - len(artists)),
                offset=offset,
                time_range=time_range
            )

            if not results['items']:
                break

            artists.extend(results['items'])
            offset += len(results['items'])

            if len(results['items']) < 50:
                break

        print(f"Found {len(artists)} top artists")
        return artists

    def get_recommendations(
        self,
        seed_artists: List[str] = None,
        seed_tracks: List[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get recommendations based on seed artists and tracks

        Args:
            seed_artists: List of artist IDs (max 5 combined with seed_tracks)
            seed_tracks: List of track IDs (max 5 combined with seed_artists)
            limit: Number of recommendations to fetch

        Returns:
            List of recommended track dictionaries
        """
        seed_artists = seed_artists or []
        seed_tracks = seed_tracks or []

        # Spotify API limits: max 5 seeds total, max 100 recommendations
        total_seeds = len(seed_artists) + len(seed_tracks)
        if total_seeds > 5:
            # Balance between artists and tracks
            artist_ratio = len(seed_artists) / total_seeds
            max_artists = max(1, min(4, int(5 * artist_ratio)))
            max_tracks = 5 - max_artists

            seed_artists = seed_artists[:max_artists]
            seed_tracks = seed_tracks[:max_tracks]

        print(f"Getting recommendations based on {len(seed_artists)} artists and {len(seed_tracks)} tracks...")

        recommendations = []
        remaining = limit

        # Fetch in batches of 100 (API limit)
        while remaining > 0:
            batch_limit = min(100, remaining)

            results = self.sp.recommendations(
                seed_artists=seed_artists if seed_artists else None,
                seed_tracks=seed_tracks if seed_tracks else None,
                limit=batch_limit
            )

            recommendations.extend(results['tracks'])
            remaining -= len(results['tracks'])

            # If we got fewer results than requested, we've exhausted recommendations
            if len(results['tracks']) < batch_limit:
                break

        print(f"Found {len(recommendations)} recommendations")
        return recommendations

    def generate_personalized_recommendations(
        self,
        num_recommendations: int = 50,
        use_top_tracks: bool = True,
        use_top_artists: bool = True,
        use_followed_artists: bool = True
    ) -> List[Dict]:
        """
        Generate personalized recommendations based on user's listening habits

        Args:
            num_recommendations: Number of recommendations to generate
            use_top_tracks: Include top tracks as seeds
            use_top_artists: Include top artists as seeds
            use_followed_artists: Include followed artists as seeds

        Returns:
            List of recommended tracks
        """
        print("\n=== Generating Personalized Recommendations ===\n")

        seed_artist_ids: Set[str] = set()
        seed_track_ids: Set[str] = set()

        # Gather seed artists
        if use_followed_artists:
            followed = self.get_followed_artists(limit=20)
            seed_artist_ids.update([artist['id'] for artist in followed[:10]])

        if use_top_artists:
            top_artists = self.get_top_artists(limit=20)
            seed_artist_ids.update([artist['id'] for artist in top_artists[:10]])

        # Gather seed tracks
        if use_top_tracks:
            top_tracks = self.get_top_tracks(limit=20)
            seed_track_ids.update([track['id'] for track in top_tracks[:10]])

        # Convert sets to lists and shuffle
        seed_artists = list(seed_artist_ids)
        seed_tracks = list(seed_track_ids)
        random.shuffle(seed_artists)
        random.shuffle(seed_tracks)

        # Generate multiple batches of recommendations with different seed combinations
        all_recommendations = []
        seen_track_ids = set()

        # Create multiple seed combinations to diversify recommendations
        iterations = (num_recommendations // 50) + 1

        for i in range(iterations):
            # Rotate seeds for variety
            start_idx = (i * 2) % max(len(seed_artists), len(seed_tracks), 1)
            batch_artists = seed_artists[start_idx:start_idx + 3] if seed_artists else []
            batch_tracks = seed_tracks[start_idx:start_idx + 2] if seed_tracks else []

            if not batch_artists and not batch_tracks:
                break

            recommendations = self.get_recommendations(
                seed_artists=batch_artists,
                seed_tracks=batch_tracks,
                limit=50
            )

            # Filter out duplicates
            for track in recommendations:
                if track['id'] not in seen_track_ids:
                    all_recommendations.append(track)
                    seen_track_ids.add(track['id'])

                    if len(all_recommendations) >= num_recommendations:
                        break

            if len(all_recommendations) >= num_recommendations:
                break

        print(f"\n=== Generated {len(all_recommendations)} unique recommendations ===\n")
        return all_recommendations[:num_recommendations]

    def create_playlist(
        self,
        playlist_name: str,
        tracks: List[Dict],
        description: str = None,
        public: bool = True
    ) -> Dict:
        """
        Create a new playlist with recommended tracks

        Args:
            playlist_name: Name for the new playlist
            tracks: List of track dictionaries to add
            description: Playlist description
            public: Whether playlist should be public

        Returns:
            Created playlist dictionary
        """
        if not tracks:
            raise ValueError("Cannot create playlist with no tracks")

        # Create playlist
        playlist = self.sp.user_playlist_create(
            user=self.user_id,
            name=playlist_name,
            public=public,
            description=description or f"Personalized recommendations - {len(tracks)} tracks"
        )

        print(f"\nCreated playlist: {playlist_name}")
        print(f"Playlist ID: {playlist['id']}")
        print(f"URL: {playlist['external_urls']['spotify']}")

        # Add tracks in batches of 100 (API limit)
        track_uris = [track['uri'] for track in tracks]

        for i in range(0, len(track_uris), 100):
            batch = track_uris[i:i + 100]
            self.sp.playlist_add_items(playlist['id'], batch)
            print(f"Added {len(batch)} tracks to playlist")

        print(f"\n✓ Successfully added {len(tracks)} tracks to playlist!")
        return playlist

    def display_recommendations(self, tracks: List[Dict], max_display: int = 20):
        """
        Display recommendations in a readable format

        Args:
            tracks: List of track dictionaries
            max_display: Maximum number of tracks to display
        """
        print(f"\n=== Top {min(len(tracks), max_display)} Recommendations ===\n")

        for i, track in enumerate(tracks[:max_display], 1):
            artists = ", ".join([artist['name'] for artist in track['artists']])
            print(f"{i}. {track['name']}")
            print(f"   Artist(s): {artists}")
            print(f"   Album: {track['album']['name']}")
            print(f"   Popularity: {track['popularity']}/100")
            print()
