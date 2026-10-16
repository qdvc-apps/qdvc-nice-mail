"""The GTK 4 / libadwaita application (spec §7, §9).

An ``Adw.Application`` owns the application id (single instance: launching
again raises the window), the accelerators of the ``win.*`` actions (from
``ui_prefs.SHORTCUTS``), the stylesheet and the icon. ``qdvc-nicemail
<folder>`` opens that workspace.
"""
from __future__ import annotations

import os
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

from .. import APP_ID, APP_NAME, PRGNAME  # noqa: E402
from ..config import Config  # noqa: E402
from ..ui_prefs import accelerators, bundled_icons_dir  # noqa: E402
from .gtk4_window import MainWindow  # noqa: E402

# The app's own icon: installed into the hicolor theme by scripts/build-app.sh,
# and found in data/icons when run from a checkout. If neither is present,
# the first stock themed icon the theme has.
ICON_NAME = APP_ID
FALLBACK_ICON_NAMES = ("internet-mail", "mail-send", "mail-message-new-symbolic")

# Load-bearing for X11: WM_CLASS must match the launcher's StartupWMClass.
# (On Wayland GNOME Shell matches the application id to qdvc.NiceMail.desktop.)
GLib.set_prgname(PRGNAME)
GLib.set_application_name(APP_NAME)

HERE = os.path.dirname(os.path.abspath(__file__))


def resolve_icon_name(display) -> str:  # noqa: ANN001
    theme = Gtk.IconTheme.get_for_display(display)
    icons = bundled_icons_dir()
    if icons:
        # data/icons is laid out like hicolor, so its icons are themed.
        theme.add_search_path(icons)
    for name in (ICON_NAME, *FALLBACK_ICON_NAMES):
        if theme.has_icon(name):
            return name
    return FALLBACK_ICON_NAMES[-1]


class Application(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_OPEN)
        self.config = Config()
        self.window: MainWindow | None = None
        self.icon_name = FALLBACK_ICON_NAMES[-1]

    def do_startup(self) -> None:
        Adw.Application.do_startup(self)
        display = Gdk.Display.get_default()
        self.icon_name = resolve_icon_name(display)
        Gtk.Window.set_default_icon_name(self.icon_name)
        css = Gtk.CssProvider()
        css.load_from_path(os.path.join(HERE, "style.css"))
        Gtk.StyleContext.add_provider_for_display(display, css,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self._quit())
        self.add_action(quit_action)
        for action, accels in accelerators("gtk4").items():
            self.set_accels_for_action(action, accels)

    def _ensure_window(self, reopen: bool = True) -> MainWindow:
        if self.window is None:
            self.window = MainWindow(self, self.config, self.icon_name)
            if reopen:
                self.window.reopen_last()
        return self.window

    def do_activate(self) -> None:
        self._ensure_window().present()

    def do_open(self, files, n_files, hint) -> None:  # noqa: ANN001
        folders = [f.get_path() for f in files if f.get_path() and os.path.isdir(f.get_path())]
        win = self._ensure_window(reopen=not folders)
        win.present()
        if folders:
            win.open_path(folders[0])

    def _quit(self) -> None:
        if self.window is not None:
            self.window.close()
        self.quit()


def main(argv: list[str] | None = None) -> int:
    return Application().run(argv if argv is not None else sys.argv)
