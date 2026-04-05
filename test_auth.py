#!/usr/bin/env python3
"""
Smoke test for Spotify credentials and OAuth flow.
Run this to verify your Client ID, Client Secret, and Redirect URI are working.

Usage:
    python test_auth.py [path/to/.env]

If no .env path is given, loads from .env in the current directory.
"""

import os
import sys

# Allow passing a custom .env path
env_path = sys.argv[1] if len(sys.argv) > 1 else ".env"

try:
    from dotenv import load_dotenv
except ImportError:
    print("ERROR: python-dotenv not installed. Run: pip install python-dotenv")
    sys.exit(1)

try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
except ImportError:
    print("ERROR: spotipy not installed. Run: pip install spotipy")
    sys.exit(1)

load_dotenv(env_path)

client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
redirect_uri = "http://127.0.0.1:8888/callback"

print("=" * 60)
print("DJ Rara — Spotify Auth Smoke Test")
print("=" * 60)
print(f"  .env path:     {env_path}")
print(f"  Client ID:     {client_id or 'NOT SET'}")
print(f"  Client Secret: {'*' * 16 + client_secret[-4:] if client_secret else 'NOT SET'}")
print(f"  Redirect URI:  {redirect_uri}  (hardcoded)")
print("=" * 60)

if not client_id or not client_secret:
    print("\nERROR: Missing credentials. Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in your .env file.")
    sys.exit(1)

print("\nOpening browser for Spotify login...")
print("After authorizing, you will be redirected to localhost — paste that full URL back here if prompted.\n")

try:
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope="user-top-read user-library-read",
        cache_path=".cache-test",
    ))

    me = sp.current_user()
    print("=" * 60)
    print("  Auth successful!")
    print(f"  Logged in as: {me['display_name']} ({me['id']})")
    print(f"  Account type: {me.get('product', 'unknown')}")
    print("=" * 60)
    print("\nSetup looks good. You can delete .cache-test if you don't need it.")

except spotipy.SpotifyOauthError as e:
    print(f"\nERROR: OAuth failed — {e}")
    print("\nCommon fixes:")
    print(f"  - Make sure '{redirect_uri}' is added exactly as a Redirect URI in your Spotify app settings")
    print("  - Double-check your Client ID and Client Secret")
    sys.exit(1)
except Exception as e:
    print(f"\nERROR: {e}")
    sys.exit(1)
