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
        sp = SpotifyAuthenticator().authenticate()
    except Exception as e:
        print(f"♪ authentication failed: {e}")
        print("  Try deleting .cache and running again.")
        sys.exit(1)

    from .spotify_client import SpotifyClient
    DJRaraApp(SpotifyClient(sp)).run()


if __name__ == "__main__":
    main()
