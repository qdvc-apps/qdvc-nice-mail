"""Emoji catalogue (pure).

The full emoji list is derived at runtime from Python's built-in
``unicodedata`` so no third-party emoji package is required (spec §4:
third-party libs SHOULD be optional). Each emoji gets a stable snake_case
id from its Unicode name.
"""
from __future__ import annotations

import sys
import unicodedata
from dataclasses import dataclass, field

from .naming import emoji_id

# Skin-tone modifiers (Fitzpatrick). "none" means no modifier applied.
SKIN_TONES: dict[str, str] = {
    "none": "",
    "light": "\U0001F3FB",
    "medium_light": "\U0001F3FC",
    "medium": "\U0001F3FD",
    "medium_dark": "\U0001F3FE",
    "dark": "\U0001F3FF",
}

# Base codepoints that accept an emoji-modifier (people/body parts). This is a
# pragmatic subset check: characters in these ranges are modifier bases.
_MODIFIER_BASE_RANGES = (
    (0x261D, 0x261D), (0x26F9, 0x26F9),
    (0x270A, 0x270D),
    (0x1F385, 0x1F385), (0x1F3C2, 0x1F3C4), (0x1F3C7, 0x1F3C7),
    (0x1F3CA, 0x1F3CC), (0x1F442, 0x1F443), (0x1F446, 0x1F450),
    (0x1F466, 0x1F478), (0x1F47C, 0x1F47C), (0x1F481, 0x1F483),
    (0x1F485, 0x1F487), (0x1F48F, 0x1F48F), (0x1F491, 0x1F491),
    (0x1F4AA, 0x1F4AA), (0x1F574, 0x1F575), (0x1F57A, 0x1F57A),
    (0x1F590, 0x1F590), (0x1F595, 0x1F596), (0x1F645, 0x1F647),
    (0x1F64B, 0x1F64F), (0x1F6A3, 0x1F6A3), (0x1F6B4, 0x1F6B6),
    (0x1F6C0, 0x1F6C0), (0x1F6CC, 0x1F6CC), (0x1F918, 0x1F91F),
    (0x1F926, 0x1F926), (0x1F930, 0x1F939), (0x1F93C, 0x1F93E),
    (0x1F977, 0x1F977), (0x1F9B5, 0x1F9B6), (0x1F9B8, 0x1F9B9),
    (0x1F9BB, 0x1F9BB), (0x1F9CD, 0x1F9CF), (0x1F9D1, 0x1F9DD),
)

# Ranges scanned for candidate emoji code points.
_SCAN_RANGES = (
    (0x1F300, 0x1FAFF),  # misc symbols, emoticons, transport, supplemental, extended-A
    (0x2600, 0x27BF),    # misc symbols + dingbats
    (0x2190, 0x21FF),    # arrows (a few are emoji-presented)
    (0x2B00, 0x2BFF),    # stars, etc.
)


@dataclass(frozen=True)
class Emoji:
    id: str
    char: str          # base character (no modifier)
    name: str          # human-readable Unicode name (Title Case)

    def display(self, skin_tone: str = "none") -> str:
        """The character with an optional skin-tone modifier applied."""
        mod = SKIN_TONES.get(skin_tone, "")
        if mod and accepts_skin_tone(self.char):
            return self.char + mod
        return self.char


def accepts_skin_tone(char: str) -> bool:
    if not char:
        return False
    cp = ord(char[0])
    return any(lo <= cp <= hi for lo, hi in _MODIFIER_BASE_RANGES)


def _iter_candidate_chars():
    for lo, hi in _SCAN_RANGES:
        for cp in range(lo, hi + 1):
            try:
                ch = chr(cp)
            except ValueError:
                continue
            yield ch


class EmojiCatalogue:
    """Builds and holds the full emoji list, keyed by snake_case id."""

    def __init__(self) -> None:
        self._by_id: dict[str, Emoji] = {}
        self._ordered: list[Emoji] = []
        self._build()

    def _build(self) -> None:
        seen_ids: set[str] = set()
        for ch in _iter_candidate_chars():
            try:
                name = unicodedata.name(ch)
            except ValueError:
                continue  # unnamed code point -> not a usable emoji
            base_id = emoji_id(name)
            uid = base_id
            n = 2
            while uid in seen_ids:
                uid = f"{base_id}_{n}"
                n += 1
            seen_ids.add(uid)
            em = Emoji(id=uid, char=ch, name=name.title())
            self._by_id[uid] = em
            self._ordered.append(em)

    # ---- queries ---------------------------------------------------------
    def all(self) -> list[Emoji]:
        return list(self._ordered)

    def get(self, uid: str) -> Emoji | None:
        return self._by_id.get(uid)

    def search(self, query: str) -> list[Emoji]:
        """Match on name/description or id (case-insensitive substring)."""
        q = query.strip().lower()
        if not q:
            return self.all()
        out = []
        for em in self._ordered:
            if q in em.name.lower() or q in em.id:
                out.append(em)
        return out


# The single default favourite required by the spec.
DEFAULT_FAVOURITE_CHAR = "\U0001F60A"  # 😊
