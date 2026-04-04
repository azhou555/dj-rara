#!/usr/bin/env python3
"""
Test script to debug Spotify OAuth redirect URI
"""

import os
from dotenv import load_dotenv

load_dotenv()

client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI')

print("=" * 60)
print("Spotify OAuth Configuration Test")
print("=" * 60)
print(f"\nClient ID: {client_id}")
print(f"Client Secret: {'*' * 20}{client_secret[-4:] if client_secret else 'NOT SET'}")
print(f"Redirect URI: {redirect_uri}")
print("\n" + "=" * 60)
print("\nWhat you need to add in Spotify Dashboard:")
print("=" * 60)
print(f"\n{redirect_uri}\n")
print("=" * 60)
print("\nSteps:")
print("1. Go to: https://developer.spotify.com/dashboard")
print("2. Click your app")
print("3. Click 'Settings'")
print("4. In 'Redirect URIs', paste EXACTLY:")
print(f"   {redirect_uri}")
print("5. Click 'Add'")
print("6. Click 'Save' at the bottom")
print("=" * 60)
