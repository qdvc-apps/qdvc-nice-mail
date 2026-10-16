"""GTK3 shortcut reference (spec §10).

The actual accelerators are attached in ``gtk3_main_window`` via the window's
AccelGroup; this module exposes the shared table so a shortcuts reference can
be rendered consistently, and documents the GTK3 wiring in one place.
"""
from __future__ import annotations

from ..ui_prefs import shortcuts_for


def shortcut_rows() -> list[tuple[str, str]]:
    """(label, accelerator) pairs for display in a reference dialog."""
    return [(s.title, s.accels[0]) for s in shortcuts_for("gtk3")]
