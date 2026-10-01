#!/usr/bin/env python3
"""DJ Rara — entry point."""

import os
import sys

from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

    from .app import DJRaraApp

    # No credentials — launch setup wizard instead of erroring
    if not client_id or not client_secret:
        DJRaraApp(client=None).run()
        return

    try:
        from .spotify_auth import SpotifyAuthenticator
        from .spotify_client import SpotifyClient
        sp = SpotifyAuthenticator().authenticate()
        client = SpotifyClient(sp)
    except Exception as e:
        print(f"♪ authentication failed: {e}")
        print("  Check your Spotify credentials and connection, then try again.")
        sys.exit(1)

    DJRaraApp(client).run()


if __name__ == "__main__":
    main()
