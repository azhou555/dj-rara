#!/usr/bin/env python3
"""
Diagnostic script to check Spotify API access
"""

from spotify_auth import SpotifyAuthenticator

print("=" * 60)
print("Spotify API Diagnostic Tool")
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
    print(f"Country: {user.get('country', 'N/A')}")
    print(f"Product: {user.get('product', 'N/A')}")

    # Test available genres for recommendations
    print("\n" + "=" * 60)
    print("Testing Recommendations API Access...")
    print("=" * 60)

    try:
        # Try to get available genres
        genres = sp.recommendation_genre_seeds()
        print(f"\n✓ Can access recommendation genre seeds")
        print(f"  Available genres: {len(genres['genres'])} genres")
        print(f"  Sample genres: {', '.join(genres['genres'][:5])}")
    except Exception as e:
        print(f"\n✗ Cannot access recommendation genre seeds")
        print(f"  Error: {e}")

    # Try to get a simple recommendation with genre seeds instead of artist/track seeds
    print("\n" + "=" * 60)
    print("Testing Simple Genre-Based Recommendation...")
    print("=" * 60)

    try:
        results = sp.recommendations(seed_genres=['pop'], limit=5)
        print(f"\n✓ Successfully got recommendations using genre seeds")
        print(f"  Received {len(results['tracks'])} recommendations")
        if results['tracks']:
            print(f"  First recommendation: {results['tracks'][0]['name']} by {results['tracks'][0]['artists'][0]['name']}")
    except Exception as e:
        print(f"\n✗ Failed to get recommendations")
        print(f"  Error: {e}")
        print("\n⚠ IMPORTANT: This suggests your Spotify app may not have access to the Recommendations API")
        print("  This can happen if:")
        print("  1. Your app is in Development Mode but hasn't been properly configured")
        print("  2. Your account doesn't have the necessary permissions")
        print("  3. There's an issue with your Spotify app setup")

    # Check token scopes
    print("\n" + "=" * 60)
    print("Checking OAuth Scopes...")
    print("=" * 60)

    print(f"\nRequested scopes: {authenticator.scope}")

    print("\n" + "=" * 60)
    print("Diagnostic Complete")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ Error during diagnostics: {e}")
    import traceback
    traceback.print_exc()
