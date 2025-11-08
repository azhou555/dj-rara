"""
Spotify Authentication Module
Handles OAuth 2.0 authentication flow for Spotify Web API
"""

import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv


class SpotifyAuthenticator:
    """Manages Spotify API authentication"""

    def __init__(self):
        """Initialize authenticator with credentials from environment variables"""
        load_dotenv()

        self.client_id = os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        self.redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI', 'http://localhost:8888/callback')

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Missing Spotify credentials. Please set SPOTIFY_CLIENT_ID and "
                "SPOTIFY_CLIENT_SECRET in your .env file"
            )

        # Define the scopes needed for the recommendation engine
        self.scope = " ".join([
            "user-follow-read",           # Read followed artists
            "user-top-read",              # Read top tracks and artists
            "playlist-modify-public",     # Create and modify public playlists
            "playlist-modify-private",    # Create and modify private playlists
            "user-library-read"           # Read saved tracks
        ])

    def authenticate(self):
        """
        Authenticate with Spotify and return an authenticated Spotify client

        Returns:
            spotipy.Spotify: Authenticated Spotify client
        """
        auth_manager = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope=self.scope,
            cache_path=".cache"
        )

        return spotipy.Spotify(auth_manager=auth_manager)

    @staticmethod
    def get_authenticated_client():
        """
        Convenience method to get an authenticated Spotify client

        Returns:
            spotipy.Spotify: Authenticated Spotify client
        """
        authenticator = SpotifyAuthenticator()
        return authenticator.authenticate()
