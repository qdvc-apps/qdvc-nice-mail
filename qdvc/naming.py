"""Naming / id helpers (pure)."""
from __future__ import annotations

import re
import secrets

# Deliberately excludes ambiguous glyphs (0/O, 1/l/I, 2/Z, 5/S, o/0, etc.).
MSGREF_ALPHABET = "346789ABCDEFGHJKLMNPQRTUVWXYabcdefghijkmnpqrtwxyz"
MSGREF_LENGTH = 10


def emoji_id(name: str) -> str:
    """Snake_case unique id from an emoji's Unicode name/description.

    'GRINNING FACE WITH SMILING EYES' -> 'grinning_face_with_smiling_eyes'
    Non-alphanumeric runs collapse to a single underscore.
    """
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return s or "emoji"


def custom_emoji_id(char: str) -> str:
    """Stable snake_case id for a user-supplied (pasted) glyph.

    Derived from the glyph's code points so it is deterministic and unique per
    glyph, e.g. '\u2764\ufe0f\u200d\U0001fa79' -> 'custom_2764_fe0f_200d_1fa79'.
    """
    cps = "_".join(f"{ord(c):x}" for c in char)
    return f"custom_{cps}" if cps else "custom_emoji"


def generate_message_ref() -> str:
    """A 10-char id from the reduced (unambiguous) alphabet."""
    return "".join(secrets.choice(MSGREF_ALPHABET) for _ in range(MSGREF_LENGTH))
