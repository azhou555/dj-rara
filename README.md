# DJ Rara - Spotify Recommendation Engine

A Python-based Spotify recommendation engine that analyzes your listening habits and creates personalized playlists filled with new music recommendations.

## Features

- **OAuth 2.0 Authentication**: Secure login to your Spotify account
- **Personalized Analysis**: Analyzes your followed artists, top tracks, and top artists
- **Smart Recommendations**: Uses Spotify's recommendation API to find music you'll love
- **Automatic Playlist Creation**: Creates a playlist with your recommendations
- **Flexible Configuration**: Customize the number of recommendations and data sources
- **CLI Interface**: Easy-to-use command-line interface

## Prerequisites

- Python 3.7 or higher
- A Spotify account (Free or Premium)
- Spotify Developer Application credentials

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/azhou555/dj-rara.git
cd dj-rara
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Or using a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Create a Spotify Application

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Log in with your Spotify account
3. Click "Create an App"
4. Fill in the app name (e.g., "DJ Rara") and description
5. Accept the terms and click "Create"
6. Click "Edit Settings"
7. Add `http://localhost:8888/callback` to the Redirect URIs
8. Click "Save"
9. Note your **Client ID** and **Client Secret**

### 4. Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your credentials:
   ```
   SPOTIFY_CLIENT_ID=your_client_id_here
   SPOTIFY_CLIENT_SECRET=your_client_secret_here
   SPOTIFY_REDIRECT_URI=http://localhost:8888/callback
   ```

## Usage

### Basic Usage

Generate 50 recommendations and create a playlist:

```bash
python main.py
```

On first run, your browser will open asking you to authorize the application. After authorization, you'll be redirected to a URL. Copy the entire URL from your browser and paste it back into the terminal.

### Advanced Usage

**Specify number of recommendations:**
```bash
python main.py --recommendations 100
```

**Custom playlist name:**
```bash
python main.py --playlist-name "My Awesome Discoveries"
```

**Create a public playlist:**
```bash
python main.py --public
```

**Only display recommendations without creating a playlist:**
```bash
python main.py --no-playlist
```

**Customize recommendation sources:**
```bash
# Use only top tracks (exclude followed and top artists)
python main.py --no-followed-artists --no-top-artists

# Use only followed and top artists (exclude top tracks)
python main.py --no-top-tracks
```

**Display more recommendations in console:**
```bash
python main.py --display 50
```

### All Options

```
Options:
  -h, --help                     Show help message and exit
  -n, --recommendations N        Number of recommendations to generate (default: 50)
  -p, --playlist-name NAME       Name for the created playlist
  --public                       Make the playlist public (default: private)
  --no-followed-artists          Don't use followed artists for recommendations
  --no-top-artists               Don't use top artists for recommendations
  --no-top-tracks                Don't use top tracks for recommendations
  --display N                    Number of recommendations to display (default: 20)
  --no-playlist                  Skip creating playlist, only display recommendations
```

## How It Works

1. **Authentication**: The app authenticates with Spotify using OAuth 2.0
2. **Data Collection**: Fetches your:
   - Followed artists
   - Top tracks (based on recent listening)
   - Top artists (based on recent listening)
3. **Seed Selection**: Selects a diverse mix of artists and tracks as "seeds"
4. **Recommendation Generation**: Uses Spotify's recommendation algorithm to find similar music
5. **Playlist Creation**: Creates a new playlist with the recommendations
6. **Deduplication**: Ensures no duplicate tracks in your playlist

## Project Structure

```
dj-rara/
├── main.py                    # CLI entry point
├── spotify_auth.py            # Authentication module
├── recommendation_engine.py   # Core recommendation logic
├── requirements.txt           # Python dependencies
├── .env.example              # Example environment configuration
├── .gitignore                # Git ignore rules
└── README.md                 # This file
```

## API Rate Limits

The Spotify Web API has rate limits. If you encounter rate limit errors:
- Reduce the number of recommendations
- Wait a few minutes before trying again
- Check [Spotify's rate limit documentation](https://developer.spotify.com/documentation/web-api/concepts/rate-limits)

## Troubleshooting

### "Missing Spotify credentials" Error
- Ensure your `.env` file exists and contains valid credentials
- Double-check your Client ID and Client Secret from the Spotify Dashboard

### Authentication Issues
- Make sure `http://localhost:8888/callback` is added to your app's Redirect URIs
- Try deleting the `.cache` file and re-authenticating

### No Recommendations Found
- Listen to more music on Spotify to build your profile
- Follow more artists
- Try using different recommendation sources

### Import Errors
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check that you're using Python 3.7 or higher: `python --version`

## Dependencies

- **spotipy** (2.23.0): Spotify Web API Python library
- **python-dotenv** (1.0.0): Environment variable management

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Acknowledgments

- Built with [Spotipy](https://github.com/spotipy-dev/spotipy)
- Uses the [Spotify Web API](https://developer.spotify.com/documentation/web-api)

## Support

If you encounter any issues or have questions:
1. Check the Troubleshooting section above
2. Review the [Spotify API Documentation](https://developer.spotify.com/documentation/web-api)
3. Open an issue on GitHub

---

Enjoy discovering new music with DJ Rara! 🎵
