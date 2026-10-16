"""GTK3 Gtk.Application (spec §7, §8)."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gio, GLib, Gtk  # noqa: E402

from .. import APP_ID, PRGNAME  # noqa: E402
from ..config import Config  # noqa: E402
from ..ui_prefs import bundled_icons_dir  # noqa: E402
from .gtk3_main_window import MainWindow  # noqa: E402

# The app's own icon: installed into the hicolor theme by scripts/build-app.sh,
# and found in data/icons when run from a checkout. When neither is present,
# the standard freedesktop themed icon present on typical GNOME/MATE installs.
ICON_NAME = APP_ID
FALLBACK_ICON_NAME = "internet-mail"

# Load-bearing: makes X11 WM_CLASS match the .desktop StartupWMClass.
GLib.set_prgname(PRGNAME)


def resolve_icon_name() -> str:
    """ICON_NAME if the theme (or data/icons) has it, else the stock icon."""
    theme = Gtk.IconTheme.get_default()
    if theme is None:
        return FALLBACK_ICON_NAME
    icons = bundled_icons_dir()
    if icons:
        theme.append_search_path(icons)
    return ICON_NAME if theme.has_icon(ICON_NAME) else FALLBACK_ICON_NAME


class NiceMailApplication(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.HANDLES_OPEN,
        )
        self.config = Config()
        self.window: MainWindow | None = None
        self.icon_name = FALLBACK_ICON_NAME

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)
        self.icon_name = resolve_icon_name()
        Gtk.Window.set_default_icon_name(self.icon_name)
        # app.quit, reachable over D-Bus (org.gtk.Actions): scripts/build-app.sh
        # uses it to close a running copy before reinstalling, in either UI.
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self._quit())
        self.add_action(quit_action)

    def _quit(self) -> None:
        if self.window is not None:
            self.window.close()  # delete-event saves the window size
        self.quit()

    def do_activate(self) -> None:
        if self.window is None:
            self.window = MainWindow(self, icon_name=self.icon_name)
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
