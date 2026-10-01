"""
Spotify Authentication Module
Handles OAuth 2.0 authentication flow for Spotify Web API
"""

import os
import sys
from pathlib import Path
import spotipy
from spotipy.exceptions import SpotifyOauthError
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv


class SpotifyAuthenticator:
    """Manages Spotify API authentication"""

    def __init__(self):
        """Initialize authenticator with credentials from environment variables"""
        load_dotenv()

        self.client_id = os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        self.redirect_uri = "http://127.0.0.1:8888/callback"

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

        # Spotipy otherwise defers OAuth until the first API request, outside
        # the startup authentication error handler.
        try:
            auth_manager.get_access_token(as_dict=False)
        except SpotifyOauthError as error:
            cache_path = Path(".cache")
            if error.error != "invalid_grant" or not cache_path.is_file():
                raise
            # A revoked refresh token cannot be reused. Clear only the token
            # cache and retry authorization once; retain app credentials.
            cache_path.unlink()
            print("♪ Spotify login expired or was revoked. Please sign in again.", file=sys.stderr)
            auth_manager.get_access_token(as_dict=False)

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
