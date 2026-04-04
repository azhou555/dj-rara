#!/usr/bin/env python3
"""DJ Rara — entry point."""

import os
import sys

from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("♪ dj rara needs your spotify credentials.\n")
        print("  1. Copy .env.example to .env")
        print("  2. Add your SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET")
        print("  3. Get credentials at https://developer.spotify.com/dashboard")
        sys.exit(1)

    try:
        from spotify_auth import SpotifyAuthenticator
        sp = SpotifyAuthenticator().authenticate()
    except Exception as e:
        print(f"♪ authentication failed: {e}")
        print("  Try deleting .cache and running again.")
        sys.exit(1)

    from spotify_client import SpotifyClient
    from app import DJRaraApp

    client = SpotifyClient(sp)
    DJRaraApp(client).run()


if __name__ == "__main__":
    main()
