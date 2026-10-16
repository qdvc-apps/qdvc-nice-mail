"""Toolkit-independent UI helpers shared by both front-ends (spec §1, §10, §14).

Holds the keyboard-shortcuts table, the page and dropdown vocabularies, and
the list-building rules (which emoji or phrases a page shows for a block and a
search query), so GTK 3 and GTK 4 call one implementation.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Pages (GTK 3 notebook tabs / GTK 4 view-stack pages), in display order.
# (id, title, GTK 4 symbolic icon)
PAGES: list[tuple[str, str, str]] = [
    ("emoji", "Emoji", "face-smile-symbolic"),
    ("phrases", "Phrases", "view-list-bullet-symbolic"),
    ("signature", "Signature", "x-office-address-book-symbolic"),
    ("note", "Note to Self", "mail-message-new-symbolic"),
]
PAGE_IDS = [p[0] for p in PAGES]


# ---------------------------------------------------------------------------
# Keyboard shortcuts (spec §10).

@dataclass(frozen=True)
class Shortcut:
    """One keyboard shortcut, shared by both front-ends.

    ``accels`` are GTK accelerator strings; the first is the one displayed.
    ``toolkit`` is "both", "gtk3" or "gtk4" for shortcuts meaningful in only
    one front-end (spec §10: no artificial parity).

    GTK 4 wiring: ``action`` is the detailed action name the accelerator
    triggers (None: the key is handled by a widget and is only listed in the
    Keyboard Shortcuts window). ``bubble`` marks keys that must not pre-empt
    a focused text field (Ctrl+C): GTK 4 application accelerators run before
    the focused widget, so these are installed on a bubble-phase controller
    on the window instead, and fire only when the focused widget ignored them.
    """

    title: str
    accels: tuple[str, ...]
    section: str
    action: str | None = None
    toolkit: str = "both"
    bubble: bool = False

    def applies_to(self, toolkit: str) -> bool:
        return self.toolkit in ("both", toolkit)


SHORTCUT_SECTIONS = ["Workspace", "Pages", "Editing", "General"]

SHORTCUTS: list[Shortcut] = [
    # Workspace
    Shortcut("Open workspace", ("<Primary>o",), "Workspace", "win.open-workspace"),
    Shortcut("Refresh from disk", ("<Primary>r",), "Workspace", "win.refresh"),
    # Pages
    Shortcut("Emoji", ("<Alt>1",), "Pages", "win.show-page::emoji"),
    Shortcut("Phrases", ("<Alt>2",), "Pages", "win.show-page::phrases"),
    Shortcut("Signature", ("<Alt>3",), "Pages", "win.show-page::signature"),
    Shortcut("Note to Self", ("<Alt>4",), "Pages", "win.show-page::note"),
    # Editing
    Shortcut("Copy the selected emoji or phrase, or the signature", ("<Primary>c",),
             "Editing", "win.copy", bubble=True),
    Shortcut("Copy the activated emoji or phrase", ("Return",), "Editing"),
    Shortcut("Search emoji or phrases", ("<Primary>f",), "Editing", "win.find"),
    Shortcut("New message reference", ("F5",), "Editing", "win.new-ref"),
    # General
    Shortcut("Preferences", ("<Primary>comma",), "General", "win.preferences"),
    Shortcut("Keyboard shortcuts", ("<Primary>question",), "General", "win.shortcuts",
             toolkit="gtk4"),
    Shortcut("Close window", ("<Primary>w",), "General", "window.close", toolkit="gtk4"),
    Shortcut("Quit", ("<Primary>q",), "General", "app.quit"),
]


def shortcuts_for(toolkit: str) -> list[Shortcut]:
    return [s for s in SHORTCUTS if s.applies_to(toolkit)]


def shortcut_sections(toolkit: str) -> list[tuple[str, list[Shortcut]]]:
    """The shortcuts of one toolkit, grouped by section, in display order."""
    rows = shortcuts_for(toolkit)
    return [(sec, [s for s in rows if s.section == sec]) for sec in SHORTCUT_SECTIONS
            if any(s.section == sec for s in rows)]


def accelerators(toolkit: str = "gtk4", bubble: bool = False) -> dict[str, list[str]]:
    """Action name -> accelerators, for ``set_accels_for_action``.

    With ``bubble=True``, the accelerators to install on the window's
    bubble-phase controller instead (see :class:`Shortcut`).
    """
    out: dict[str, list[str]] = {}
    for s in shortcuts_for(toolkit):
        if s.action and s.bubble == bubble:
            out.setdefault(s.action, []).extend(s.accels)
    return out


# ---------------------------------------------------------------------------
# Dropdown option labels reused by the views.

EMOJI_BLOCKS = [("favourites", "Favourites"), ("all", "All Emoji")]

SKIN_TONE_LABELS = [
    ("none", "Default"),
    ("light", "Light"),
    ("medium_light", "Medium-Light"),
    ("medium", "Medium"),
    ("medium_dark", "Medium-Dark"),
    ("dark", "Dark"),
]

BACKEND_LABELS = [
    ("gtk3", "GTK 3 (classic)"),
    ("gtk4", "GTK 4 (GNOME)"),
]

# A modifier base used to preview each skin tone (waving hand).
SKIN_TONE_SAMPLE = "\U0001F44B"

CUSTOM_EMOJI_NOTE = "custom emoji from your favourites"


def toolbar_style_is_below(value: str) -> bool:
    return str(value).lower() == "below"


def skin_tone_sample(tone: str) -> str:
    """The sample hand shown in the given skin tone."""
    from .emoji import SKIN_TONES
    return SKIN_TONE_SAMPLE + SKIN_TONES.get(tone, "")


# ---------------------------------------------------------------------------
# What the list pages show.

def emoji_display_name(emoji) -> str:  # noqa: ANN001
    """The Name column text; custom (pasted) glyphs are flagged as such."""
    if getattr(emoji, "custom", False):
        return f"{emoji.name}  — {CUSTOM_EMOJI_NOTE}"
    return emoji.name


def emoji_block_items(ws, block: str) -> list:  # noqa: ANN001
    """Every emoji of a block, in display order, before any search.

    ``block`` is "favourites" (the user's order) or "all" (custom favourites,
    which have no catalogue entry, first, then the Unicode-derived catalogue).
    """
    if block == "favourites":
        return ws.favourite_emoji()
    return ws.custom_favourites() + ws.catalogue.all()


def emoji_matches(ws, emoji, query: str) -> bool:  # noqa: ANN001
    """Search rule: the Unicode name, the id or the user label contains the
    query, case-insensitively. An empty query matches everything."""
    q = (query or "").strip().lower()
    if not q:
        return True
    return q in emoji.name.lower() or q in emoji.id or q in ws.favourite_label(emoji.id).lower()


def emoji_listing(ws, block: str, query: str = "") -> list:  # noqa: ANN001
    """The emoji the Emoji page lists for a block and a search, in order."""
    return [e for e in emoji_block_items(ws, block) if emoji_matches(ws, e, query)]


def phrase_matches(phrase, query: str) -> bool:  # noqa: ANN001
    q = (query or "").strip().lower()
    return not q or q in phrase.text.lower()


def phrase_listing(ws, query: str = "") -> list:  # noqa: ANN001
    """The phrases the Phrases page lists: alphabetical, filtered by text."""
    phrases = sorted(ws.phrases, key=lambda p: p.text.lower())
    return [p for p in phrases if phrase_matches(p, query)]


def font_css(selector: str, family: str | None, size_pt: float | None,
             weight: int | None = None, italic: bool = False) -> str:
    """A CSS rule applying a font (from a parsed font description) to
    ``selector``; empty when there is nothing to apply."""
    decls = []
    if family:
        fams = [f.strip() for f in family.split(",") if f.strip()]
        decls.append("font-family: " + ", ".join(
            '"' + f.replace("\\", "\\\\").replace('"', '\\"') + '"' for f in fams) + ";")
    if size_pt:
        decls.append(f"font-size: {size_pt:g}pt;")
    if weight and weight != 400:
        decls.append(f"font-weight: {int(weight)};")
    if italic:
        decls.append("font-style: italic;")
    return f"{selector} {{ {' '.join(decls)} }}\n" if decls else ""


def plural(n: int, one: str, many: str | None = None) -> str:
    return f"{n} {one if n == 1 else (many or one + 's')}"


# ---------------------------------------------------------------------------
# Bundled resources.

def data_dir() -> str:
    """The checkout's (or installed copy's) ``data/`` folder."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def bundled_icons_dir() -> str | None:
    """``data/icons`` (a hicolor-style theme root) if present, else None."""
    path = os.path.join(data_dir(), "icons")
    return path if os.path.isdir(path) else None


def home_relative(path: str) -> str:
    """``/home/me/x`` -> ``~/x`` for display."""
    home = os.path.expanduser("~")
    if path == home or path.startswith(home + os.sep):
        return "~" + path[len(home):]
    return path
