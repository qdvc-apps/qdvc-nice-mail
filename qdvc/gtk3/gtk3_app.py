"""GTK3 Gtk.Application (spec §7, §8)."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gio, GLib, Gtk  # noqa: E402

from .. import APP_ID  # noqa: E402
from ..config import Config  # noqa: E402
from .gtk3_main_window import MainWindow  # noqa: E402

# Standard freedesktop themed icon present on typical GNOME/MATE installs.
ICON_NAME = "internet-mail"

# Load-bearing: makes X11 WM_CLASS match the .desktop StartupWMClass.
GLib.set_prgname("qdvc-nicemail")


class NiceMailApplication(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.HANDLES_OPEN,
        )
        self.config = Config()
        self.window: MainWindow | None = None

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)
        Gtk.Window.set_default_icon_name(ICON_NAME)

    def do_activate(self) -> None:
        if self.window is None:
            self.window = MainWindow(self, icon_name=ICON_NAME)
        self.window.present()
        # Optionally reopen last workspace.
        if self.config.get("reopen_last", True):
            last = self.config.get("last_workspace")
            if last:
                self.window.open_workspace(last)

    def do_open(self, files, n_files, hint) -> None:  # noqa: ANN001
        self.do_activate()
        if files:
            path = files[0].get_path()
            if path and self.window is not None:
                self.window.open_workspace(path)


def main(argv: list[str]) -> int:
    app = NiceMailApplication()
    return app.run(argv)
