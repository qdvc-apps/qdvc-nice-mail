"""GTK3 Preferences dialog (spec §5, §8)."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from ..ui_prefs import SKIN_TONE_LABELS  # noqa: E402


class PreferencesDialog(Gtk.Dialog):
    def __init__(self, window) -> None:  # noqa: ANN001
        super().__init__(title="Preferences", transient_for=window, modal=True)
        self.main_window = window
        self.config = window.config
        self.add_button(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
        self.set_default_size(420, -1)

        grid = Gtk.Grid(column_spacing=12, row_spacing=10, border_width=14)
        self.get_content_area().add(grid)

        row = 0

        # Toolbar style.
        grid.attach(Gtk.Label(label="Toolbar style:", xalign=0.0), 0, row, 1, 1)
        self.toolbar_combo = Gtk.ComboBoxText()
        self.toolbar_combo.append("beside", "Labels beside icons")
        self.toolbar_combo.append("below", "Labels below icons")
        self.toolbar_combo.set_active_id(self.config.toolbar_style)
        self.toolbar_combo.connect("changed", self._on_toolbar_changed)
        grid.attach(self.toolbar_combo, 1, row, 1, 1)
        row += 1

        # Emoji skin tone (moved here from the emoji toolbar; persistent).
        grid.attach(Gtk.Label(label="Emoji skin tone:", xalign=0.0), 0, row, 1, 1)
        self.tone_combo = Gtk.ComboBoxText()
        for tid, tlabel in SKIN_TONE_LABELS:
            self.tone_combo.append(tid, tlabel)
        self.tone_combo.set_active_id(self.config.get("skin_tone", "none") or "none")
        self.tone_combo.connect("changed", self._on_skin_tone_changed)
        grid.attach(self.tone_combo, 1, row, 1, 1)
        row += 1

        # Signature preview font.
        grid.attach(Gtk.Label(label="Signature font:", xalign=0.0), 0, row, 1, 1)
        font_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.font_button = Gtk.FontButton()
        current_font = self.config.get("signature_font", "") or ""
        if current_font:
            self.font_button.set_font(current_font)
        self.font_button.connect("font-set", self._on_font_set)
        font_box.pack_start(self.font_button, True, True, 0)
        reset_btn = Gtk.Button(label="Default")
        reset_btn.connect("clicked", self._on_font_reset)
        font_box.pack_start(reset_btn, False, False, 0)
        grid.attach(font_box, 1, row, 1, 1)
        row += 1

        # UI backend selector (GTK4 not implemented at this stage).
        grid.attach(Gtk.Label(label="UI backend:", xalign=0.0), 0, row, 1, 1)
        self.backend_combo = Gtk.ComboBoxText()
        self.backend_combo.append("gtk3", "GTK 3 (only backend available)")
        self.backend_combo.set_active_id("gtk3")
        self.backend_combo.set_sensitive(False)
        grid.attach(self.backend_combo, 1, row, 1, 1)
        row += 1

        grid.attach(
            Gtk.Label(
                label="Toolbar/backend changes take effect after restart.",
                xalign=0.0, wrap=True,
            ),
            1, row, 1, 1,
        )
        row += 1

        # Reopen last workspace.
        self.reopen_check = Gtk.CheckButton(label="Reopen last workspace on launch")
        self.reopen_check.set_active(bool(self.config.get("reopen_last", True)))
        self.reopen_check.connect(
            "toggled", lambda c: self.config.set("reopen_last", c.get_active())
        )
        grid.attach(self.reopen_check, 0, row, 2, 1)

        self.show_all()

    def _on_toolbar_changed(self, combo: Gtk.ComboBoxText) -> None:
        self.config.set("toolbar_style", combo.get_active_id() or "beside")

    def _on_skin_tone_changed(self, combo: Gtk.ComboBoxText) -> None:
        tone = combo.get_active_id() or "none"
        self.config.set("skin_tone", tone)
        # Apply live to the emoji tab.
        self.main_window.emoji_tab.set_skin_tone(tone)

    def _on_font_set(self, button: Gtk.FontButton) -> None:
        font = button.get_font() or ""
        self.config.set("signature_font", font)
        self.main_window.signature_tab.set_font(font)
        self.main_window.note_tab.set_font(font)

    def _on_font_reset(self, _button) -> None:  # noqa: ANN001
        self.config.set("signature_font", "")
        self.font_button.set_font("")
        self.main_window.signature_tab.set_font("")
        self.main_window.note_tab.set_font("")
