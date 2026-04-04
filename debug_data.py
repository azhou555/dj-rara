#!/usr/bin/env python3
"""
Debug script to show what data is being fetched from Spotify
"""

from spotify_auth import SpotifyAuthenticator
from recommendation_engine import SpotifyRecommendationEngine

print("=" * 60)
print("Spotify Data Fetch Debug")
print("=" * 60)

try:
    # Authenticate
    authenticator = SpotifyAuthenticator()
    sp = authenticator.authenticate()

    print("\n✓ Authentication successful!")

    # Get user info
    user = sp.current_user()
    print(f"\nUser: {user['display_name']}")
    print(f"User ID: {user['id']}")

    # Initialize engine
    engine = SpotifyRecommendationEngine(sp)

    # Get followed artists
    print("\n" + "=" * 60)
    print("FOLLOWED ARTISTS")
    print("=" * 60)

    followed = engine.get_followed_artists(limit=20)
    print(f"\nTotal followed artists: {len(followed)}")

    if followed:
        print("\nFirst 10 followed artists:")
        for i, artist in enumerate(followed[:10], 1):
            print(f"{i}. {artist['name']}")
            print(f"   ID: {artist['id']}")
            print(f"   Genres: {', '.join(artist['genres'][:3]) if artist['genres'] else 'No genres listed'}")
    else:
        print("No followed artists found")

    # Get top artists
    print("\n" + "=" * 60)
    print("TOP ARTISTS")
    print("=" * 60)

    top_artists = engine.get_top_artists(limit=20)
    print(f"\nTotal top artists: {len(top_artists)}")

    if top_artists:
        print("\nFirst 10 top artists:")
        for i, artist in enumerate(top_artists[:10], 1):
            print(f"{i}. {artist['name']}")
            print(f"   ID: {artist['id']}")
            print(f"   Genres: {', '.join(artist['genres'][:3]) if artist['genres'] else 'No genres listed'}")
    else:
        print("No top artists found")

    # Get top tracks
    print("\n" + "=" * 60)
    print("TOP TRACKS")
    print("=" * 60)

    top_tracks = engine.get_top_tracks(limit=20)
    print(f"\nTotal top tracks: {len(top_tracks)}")

    if top_tracks:
        print("\nFirst 10 top tracks:")
        for i, track in enumerate(top_tracks[:10], 1):
            artists = ", ".join([a['name'] for a in track['artists']])
            print(f"{i}. {track['name']} - {artists}")
            print(f"   ID: {track['id']}")
            print(f"   Album: {track['album']['name']}")
    else:
        print("No top tracks found")

    # Test a simple recommendation call with one of the artist IDs
    if top_artists:
        print("\n" + "=" * 60)
        print("TESTING SINGLE ARTIST RECOMMENDATION")
        print("=" * 60)

        test_artist_id = top_artists[0]['id']
        test_artist_name = top_artists[0]['name']

        print(f"\nTrying to get recommendations based on: {test_artist_name}")
        print(f"Artist ID: {test_artist_id}")

        try:
            results = sp.recommendations(seed_artists=[test_artist_id], limit=5)
            print(f"\n✓ Success! Got {len(results['tracks'])} recommendations")

            if results['tracks']:
                print("\nRecommendations:")
                for i, track in enumerate(results['tracks'], 1):
                    artists = ", ".join([a['name'] for a in track['artists']])
                    print(f"{i}. {track['name']} - {artists}")
        except Exception as e:
            print(f"\n✗ Failed to get recommendations")
            print(f"Error: {e}")

    print("\n" + "=" * 60)
    print("Debug Complete")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
