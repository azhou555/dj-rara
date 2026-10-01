# DJ Rara

A lo-fi Spotify recommendation TUI. Mood-based discovery, track curation, playlist creation, and Music DNA stats — all in the terminal.

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue) ![License MIT](https://img.shields.io/badge/license-MIT-green)

## Install

**macOS / Linux**
```bash
pip install dj-rara
```

**Windows** (recommended)
```powershell
pip install pipx
pipx install dj-rara
```

`pipx` isolates the app and handles upgrades more cleanly on Windows. To upgrade later:
```powershell
pipx upgrade dj-rara
```

## Spotify Setup (one time)

1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) and create a free app
2. In the app settings, add `http://127.0.0.1:8888/callback` as a Redirect URI and save
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
| `k` / `x` | keep / skip the selected track |
| `u` | undo the last keep/skip decision on a track still displayed |
| `r` | replace skipped tracks from the remaining candidates |
| `Shift+r` | replace all unkept tracks, preserving kept tracks |
| `o` | preview track — plays 30s clip via default media player. Press again to stop (macOS/Linux only) |
| `c` | create playlist from kept tracks, or undecided tracks if none are kept; skipped tracks are always excluded |
| `s` | go to Stats |
| `esc` | back to Mood |

The create button shows the exact number of tracks to export. Skipped tracks are
excluded from new discoveries for seven days; keeping a track or undoing its skip
clears that cooldown. Replacements use already fetched candidates and never
repeat a track shown in the same session. If the reserve runs out, unmatched rows
stay in place.

Recommendations include at most two tracks per artist and filter duplicate
recordings. Results may be shorter than requested when there aren't enough
distinct candidates. Missing audio measurements receive a neutral score, and
ties are randomized before selection.

Exact artist genre tags take priority over related genres, including when tracks
are replaced. The screen reports broadened or unverifiable genre filtering.
The **Why this track** panel follows the selected row and shows its sources,
matched artist genres, and public playlist occurrences. It only reports a close
mood match when audio measurements support it.

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
Make sure `http://127.0.0.1:8888/callback` is added exactly as shown in your Spotify app's Redirect URIs settings.

**Try deleting `.cache`** if authentication gets stuck and re-run.

**No tracks found**
Try setting vibe to **new** and clearing genre selections — a very specific genre + familiar setting can sometimes return an empty pool.

**Preview not playing**
On macOS, `afplay` is used for terminal audio. On Linux, `cvlc` (VLC) is used if available. On Windows, the clip opens in your default media player.

**Windows upgrade issues (`.deleteme` files)**
Make sure DJ Rara is fully closed before upgrading. If you see errors about files in use, delete any `*.deleteme` files in `venv\Scripts\` then retry. Using `pipx` instead of a manual venv avoids this entirely.

## Requirements

- Python 3.11+
- macOS / Linux / Windows
- A free Spotify account + Spotify Developer app

## License

MIT

## Download statistics

The **PyPI download report** GitHub Actions workflow generates daily download totals, partial-window coverage, and an all-available-history total. See [download tracking](docs/analytics/README.md) for reports, local usage, retention, and release-level analysis. These statistics measure downloads rather than unique installations.
