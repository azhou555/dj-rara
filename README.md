# DJ Rara

A lo-fi Spotify recommendation TUI. Mood-based discovery, track curation, playlist creation, and Music DNA stats — all in the terminal.

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue) ![License MIT](https://img.shields.io/badge/license-MIT-green)

## Install

```bash
pip install dj-rara
```

## Spotify Setup (one time)

1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) and create a free app
2. In the app settings, add `http://localhost:8888/callback` as a Redirect URI and save(May need to use `http://127.0.0.1:8888/callback` instead)
3. Note your **Client ID** and **Client Secret**

On first run, DJ Rara will open a setup screen where you paste these in. After that, a browser window opens for Spotify login — authorize it and you're done. Credentials are saved locally in `.env`.

## Usage

```bash
dj-rara
```

Or if running from source:

```bash
python -m dj_rara
```

## Screens

### Mood Screen (home)
Pick your settings and hit **♫ discover**:

| Setting | Description |
|---|---|
| **mood** | chill / energetic / focus / melancholy — shapes search keywords |
| **genre** | Your top genres from Spotify + a few random ones to explore |
| **time range** | last 4 weeks / 6 months / all time — which era of your taste to draw from |
| **vibe** | familiar → mostly your artists' catalogues · new → mostly search-based discovery |
| **how many** | number of tracks to generate (1–100) |

### Recommendations Screen
Browse and curate the generated tracks before saving.

| Key | Action |
|---|---|
| `↑ ↓` | navigate tracks |
| `space` | toggle keep (green) / skip (strikethrough) |
| `o` | preview track — plays 30s audio in terminal via iTunes, or opens Spotify if unavailable. Press again to stop |
| `c` | create playlist from kept tracks (falls back to all tracks if none kept) |
| `s` | go to Stats |
| `esc` | back to Mood |

### Stats Screen — Music DNA
Genre bars, audio profile, and top artists for your listening history.

| Key | Action |
|---|---|
| `t` | cycle time range (last 4 weeks / 6 months / all time) |
| `p` | go to Playlists |
| `esc` | back |

### Playlists Screen
Browse all DJ Rara playlists you've created. Highlights show mood, genre, and track count.

| Key | Action |
|---|---|
| `↑ ↓` | navigate playlists |
| `enter` | open selected playlist in Spotify |
| `esc` | back |

## Themes

Press `ctrl+p` → **Themes** to switch:

| Theme | Description |
|---|---|
| `spotify` | Deep black, Spotify green, teal accents (default) |
| `apple-music` | Light gray, red accent — clean light mode |
| `lofi-cafe` | Warm dark brown, muted gold, cream text |
| `midnight` | Dark navy, soft purple, moonlight blue |
| `amoled` | Pure black, neon green — minimal |

## How Recommendations Work

Since Spotify deprecated their recommendations API for new apps in late 2024, DJ Rara builds your queue from three sources:

1. **Artist top tracks** — fetches the most-played tracks from your top artists (personalized, possibly new-to-you songs)
2. **Saved library** — your liked songs
3. **Mood + genre search** — keyword searches like `"shoegaze chill"` or `"lo-fi indie"` to surface discovery tracks

The **vibe** slider controls the mix:
- **familiar** (10% discovery) — mostly sources 1 & 2
- **mixed** (50/50, default)
- **new** (90% discovery) — mostly source 3

Tracks you've already curated into a DJ Rara playlist are filtered out automatically so you don't see the same songs twice.

## Troubleshooting

**Auth failed / redirect URI mismatch**
Make sure `http://localhost:8888/callback` is added exactly as shown in your Spotify app's Redirect URIs settings.

**Try deleting `.cache`** if authentication gets stuck and re-run.

**No tracks found**
Try setting vibe to **new** and clearing genre selections — a very specific genre + familiar setting can sometimes return an empty pool.

**Preview not playing**
`afplay` is used for terminal audio on macOS. On other platforms the track opens in Spotify instead.

## Requirements

- Python 3.11+
- macOS / Linux / Windows
- A free Spotify account + Spotify Developer app

## License

MIT
