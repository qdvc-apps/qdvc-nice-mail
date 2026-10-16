"""Preferences (Ctrl+,), applied as you change them (spec §9: no Save/Cancel).

The GTK 3 dialog's toolbar-style choice is omitted (there is no toolbar);
the backend selector takes effect on the next launch (spec §3). Keys are
shared with GTK 3: ``skin_tone``, ``signature_font``, ``reopen_last``,
``ui_backend``.
"""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Pango  # noqa: E402

from ..ui_prefs import BACKEND_LABELS, SKIN_TONE_LABELS, skin_tone_sample  # noqa: E402

DEFAULT_FONT = "Monospace 11"   # shown in the font button while no font is chosen


class PreferencesDialog(Adw.PreferencesDialog):
    def __init__(self, window) -> None:  # noqa: ANN001
        super().__init__(title="Preferences", search_enabled=False)
        self.main_window = window
        self.config = window.config
        self._updating = False

        page = Adw.PreferencesPage(title="General", icon_name="preferences-system-symbolic")

        emoji = Adw.PreferencesGroup(title="Emoji")
        tones = [t for t, _ in SKIN_TONE_LABELS]
        self.tone_row = Adw.ComboRow(
            title="Skin Tone", subtitle="For emoji of people and hands",
            model=Gtk.StringList.new([f"{skin_tone_sample(t)}  {label}"
                                      for t, label in SKIN_TONE_LABELS]))
        current = self.config.get("skin_tone", "none") or "none"
        self.tone_row.set_selected(tones.index(current) if current in tones else 0)
        self.tone_row.connect("notify::selected", self._on_tone_changed)
        emoji.add(self.tone_row)
        page.add(emoji)

        text = Adw.PreferencesGroup(
            title="Text", description="Used by the signature preview and the Note to Self fields")
        self.font_row = Adw.ActionRow(title="Font")
        self.font_button = Gtk.FontDialogButton(dialog=Gtk.FontDialog(title="Choose a Font"),
                                                valign=Gtk.Align.CENTER)
        self.font_button.connect("notify::font-desc", self._on_font_changed)
        self.reset_button = Gtk.Button(icon_name="edit-undo-symbolic", valign=Gtk.Align.CENTER,
                                       tooltip_text="Use the Default Font")
        self.reset_button.add_css_class("flat")
        self.reset_button.connect("clicked", self._on_font_reset)
        self.font_row.add_suffix(self.font_button)
        self.font_row.add_suffix(self.reset_button)
        text.add(self.font_row)
        page.add(text)

        general = Adw.PreferencesGroup(title="General")
        self.reopen_row = Adw.SwitchRow(title="Reopen the Last Workspace at Launch",
                                        active=bool(self.config.get("reopen_last", True)))
        self.reopen_row.connect("notify::active", lambda r, _p: self.config.set(
            "reopen_last", r.get_active()))
        general.add(self.reopen_row)
        backends = [b for b, _ in BACKEND_LABELS]
        self.backend_row = Adw.ComboRow(
            title="Interface", subtitle="Takes effect after restarting the app",
            model=Gtk.StringList.new([label for _, label in BACKEND_LABELS]))
        self.backend_row.set_selected(backends.index(self.config.ui_backend))
        self.backend_row.connect("notify::selected", lambda r, _p: self.config.set(
            "ui_backend", backends[r.get_selected()]))
        general.add(self.backend_row)
        page.add(general)

        self.add(page)
        self._show_font(self.config.get("signature_font", "") or "")

    # ------------------------------------------------------------------ handlers

    def _on_tone_changed(self, row: Adw.ComboRow, _pspec) -> None:  # noqa: ANN001
        tone = SKIN_TONE_LABELS[row.get_selected()][0]
        self.config.set("skin_tone", tone)
        self.main_window.emoji_page.set_skin_tone(tone)

    def _show_font(self, font: str) -> None:
        self._updating = True
        try:
            self.font_button.set_font_desc(Pango.FontDescription.from_string(font or DEFAULT_FONT))
        finally:
            self._updating = False
        self.font_row.set_subtitle(font if font else "Default (monospace for the signature)")
        self.reset_button.set_sensitive(bool(font))

    def _on_font_changed(self, button: Gtk.FontDialogButton, _pspec) -> None:  # noqa: ANN001
        if self._updating:
            return
        desc = button.get_font_desc()
        font = desc.to_string() if desc is not None else ""
        self._apply_font(font)

    def _on_font_reset(self, _button) -> None:  # noqa: ANN001
        self._apply_font("")
        self._show_font("")

    def _apply_font(self, font: str) -> None:
        self.config.set("signature_font", font)
        self.main_window.apply_font(font)
        self.font_row.set_subtitle(font if font else "Default (monospace for the signature)")
        self.reset_button.set_sensitive(bool(font))
