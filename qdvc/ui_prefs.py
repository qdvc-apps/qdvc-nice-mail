"""Toolkit-independent UI helpers shared by front-ends (spec §8/§10)."""
from __future__ import annotations

# (action_id, label, accelerator, scope)
SHORTCUTS: list[tuple[str, str, str, str]] = [
    ("open_workspace", "Open Workspace", "<Primary>o", "app"),
    ("quit", "Quit", "<Primary>q", "app"),
    ("preferences", "Preferences", "<Primary>comma", "app"),
    ("copy", "Copy (current tab)", "<Primary>c", "context"),
    ("view_emoji", "Emoji Tab", "<Alt>1", "view"),
    ("view_phrases", "Phrases Tab", "<Alt>2", "view"),
    ("view_signature", "Signature Tab", "<Alt>3", "view"),
    ("refresh", "Refresh (current tab)", "<Primary>r", "context"),
    ("refresh_ref", "New Message Ref", "F5", "context"),
]

# Dropdown option labels reused by the view.
EMOJI_BLOCKS = [("favourites", "Favourites"), ("all", "All Emoji")]

SKIN_TONE_LABELS = [
    ("none", "Default"),
    ("light", "Light"),
    ("medium_light", "Medium-Light"),
    ("medium", "Medium"),
    ("medium_dark", "Medium-Dark"),
    ("dark", "Dark"),
]


def toolbar_style_is_below(value: str) -> bool:
    return str(value).lower() == "below"
