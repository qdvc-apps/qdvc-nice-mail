"""The Keyboard Shortcuts window (Ctrl+?), built from ``ui_prefs.SHORTCUTS``
(spec §10), listing the shortcuts that apply to GTK 4."""
from __future__ import annotations

from xml.sax.saxutils import escape

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from ..ui_prefs import shortcut_sections  # noqa: E402


def shortcuts_xml() -> str:
    groups = []
    for title, items in shortcut_sections("gtk4"):
        shortcuts = "".join(
            '<child><object class="GtkShortcutsShortcut">'
            f'<property name="title">{escape(s.title)}</property>'
            f'<property name="accelerator">{escape(s.accels[0])}</property>'
            "</object></child>"
            for s in items)
        groups.append('<child><object class="GtkShortcutsGroup">'
                      f'<property name="title">{escape(title)}</property>{shortcuts}'
                      "</object></child>")
    return ('<interface><object class="GtkShortcutsWindow" id="window">'
            '<property name="modal">1</property>'
            '<child><object class="GtkShortcutsSection">'
            '<property name="section-name">shortcuts</property>'
            '<property name="max-height">10</property>'
            f'{"".join(groups)}</object></child></object></interface>')


def shortcuts_window(parent: Gtk.Window) -> Gtk.Window:
    builder = Gtk.Builder.new_from_string(shortcuts_xml(), -1)
    window = builder.get_object("window")
    window.set_transient_for(parent)
    return window
