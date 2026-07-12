"""GTK3 Preferences dialog (spec §5, §8)."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402


class PreferencesDialog(Gtk.Dialog):
    def __init__(self, window) -> None:  # noqa: ANN001
        super().__init__(title="Preferences", transient_for=window, modal=True)
        self.main_window = window
        self.config = window.config
        self.add_button(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
        self.set_default_size(380, -1)

        grid = Gtk.Grid(column_spacing=12, row_spacing=10, border_width=14)
        self.get_content_area().add(grid)

        # Toolbar style.
        grid.attach(Gtk.Label(label="Toolbar style:", xalign=0.0), 0, 0, 1, 1)
        self.toolbar_combo = Gtk.ComboBoxText()
        self.toolbar_combo.append("beside", "Labels beside icons")
        self.toolbar_combo.append("below", "Labels below icons")
        self.toolbar_combo.set_active_id(self.config.toolbar_style)
        self.toolbar_combo.connect("changed", self._on_toolbar_changed)
        grid.attach(self.toolbar_combo, 1, 0, 1, 1)

        # UI backend selector (GTK4 not implemented at this stage).
        grid.attach(Gtk.Label(label="UI backend:", xalign=0.0), 0, 1, 1, 1)
        self.backend_combo = Gtk.ComboBoxText()
        self.backend_combo.append("gtk3", "GTK 3 (only backend available)")
        self.backend_combo.set_active_id("gtk3")
        self.backend_combo.set_sensitive(False)
        grid.attach(self.backend_combo, 1, 1, 1, 1)

        grid.attach(
            Gtk.Label(
                label="Takes effect after restart.",
                xalign=0.0, wrap=True,
            ),
            1, 2, 1, 1,
        )

        # Reopen last workspace.
        self.reopen_check = Gtk.CheckButton(label="Reopen last workspace on launch")
        self.reopen_check.set_active(bool(self.config.get("reopen_last", True)))
        self.reopen_check.connect(
            "toggled", lambda c: self.config.set("reopen_last", c.get_active())
        )
        grid.attach(self.reopen_check, 0, 3, 2, 1)

        self.show_all()

    def _on_toolbar_changed(self, combo: Gtk.ComboBoxText) -> None:
        self.config.set("toolbar_style", combo.get_active_id() or "beside")
