from textual.theme import Theme

SPOTIFY = Theme(
    name="spotify",
    primary="#1db954",
    secondary="#1db954",
    accent="#80cbc4",
    background="#0d0d0d",
    surface="#111111",
    panel="#1a1a1a",
    foreground="#e0e0e0",
    dark=True,
    variables={
        "chip-active-bg": "#1a2e1f",
        "muted": "#555555",
        "dim": "#444444",
        "subtle-border": "#222222",
    },
)

APPLE_MUSIC = Theme(
    name="apple-music",
    primary="#fc3c44",
    secondary="#fa2d55",
    accent="#1c1c1e",
    background="#f5f5f7",
    surface="#ffffff",
    panel="#e8e8ed",
    foreground="#1c1c1e",
    dark=False,
    variables={
        "chip-active-bg": "#fde8e9",
        "muted": "#8e8e93",
        "dim": "#aeaeb2",
        "subtle-border": "#d1d1d6",
    },
)

LOFI_CAFE = Theme(
    name="lofi-cafe",
    primary="#c9a84c",
    secondary="#b5866e",
    accent="#b5866e",
    background="#1a1208",
    surface="#24190d",
    panel="#2e2110",
    foreground="#e8d5b7",
    dark=True,
    variables={
        "chip-active-bg": "#3a2e14",
        "muted": "#7a6440",
        "dim": "#5a4a30",
        "subtle-border": "#3a2e18",
    },
)

MIDNIGHT = Theme(
    name="midnight",
    primary="#9b59b6",
    secondary="#8e44ad",
    accent="#5dade2",
    background="#0a0a14",
    surface="#12121f",
    panel="#1a1a2e",
    foreground="#e8e8f5",
    dark=True,
    variables={
        "chip-active-bg": "#1e1830",
        "muted": "#5a5a7a",
        "dim": "#3a3a5a",
        "subtle-border": "#1e1e34",
    },
)

AMOLED = Theme(
    name="amoled",
    primary="#00e676",
    secondary="#00c853",
    accent="#40c4ff",
    background="#000000",
    surface="#0a0a0a",
    panel="#111111",
    foreground="#ffffff",
    dark=True,
    variables={
        "chip-active-bg": "#001a0d",
        "muted": "#666666",
        "dim": "#444444",
        "subtle-border": "#1a1a1a",
    },
)

ALL_THEMES = [SPOTIFY, APPLE_MUSIC, LOFI_CAFE, MIDNIGHT, AMOLED]
