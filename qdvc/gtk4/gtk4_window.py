"""The main window (spec §9).

    Adw.ApplicationWindow
      Adw.ToastOverlay
        Adw.ToolbarView
          top:     Adw.HeaderBar
                     start: the visible page's own buttons (Copy, Add, Send…)
                     title: Adw.ViewSwitcher  (Adw.WindowTitle when narrow)
                     end:   primary menu
          content: Adw.ViewStack ── Emoji · Phrases · Signature · Note to Self
          bottom:  Adw.ViewSwitcherBar (revealed when narrow)

The GTK 3 window's tab bar + per-tab toolbars become a view switcher and
per-page header buttons; its statusbar messages become toasts. Every command
is a ``win.*`` action (gtk4_actions).
"""
from __future__ import annotations

import os

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from .. import APP_NAME, APP_SUMMARY  # noqa: E402
from ..ui_prefs import PAGES, accelerators  # noqa: E402
from ..workspace import Workspace, looks_like_workspace  # noqa: E402
from . import gtk4_actions as actions  # noqa: E402
from . import gtk4_dialogs as dialogs  # noqa: E402
from .gtk4_emoji_page import EmojiPage  # noqa: E402
from .gtk4_note_page import NotePage  # noqa: E402
from .gtk4_phrases_page import PhrasesPage  # noqa: E402
from .gtk4_signature_page import SignaturePage  # noqa: E402
from .gtk4_widgets import FontStyler  # noqa: E402

REPOSITORY_URL = "https://github.com/qdvc-apps/qdvc-nice-mail"
# Below this width the view switcher moves to a bar at the bottom.
NARROW_BREAKPOINT = "max-width: 620sp"


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app, config, icon_name: str) -> None:  # noqa: ANN001
        super().__init__(application=app, title=APP_NAME)
        self.config = config
        self.icon_name = icon_name
        self.workspace: Workspace | None = None
        self.pages_ready = False
        self.set_icon_name(icon_name)

        # A minimum size is required with breakpoints (GNOME's phone size).
        self.set_size_request(360, 294)
        width, height = (config.get("window") or [900, 600])[:2]
        self.set_default_size(int(width), int(height))
        if config.get("window_maximized", False):
            self.maximize()

        self.fonts = FontStyler(self.get_display())
        actions.install(self)
        self._install_bubble_shortcuts()
        self._build()
        self.apply_font(config.get("signature_font", "") or "")
        self.connect("close-request", self._on_close_request)
        self.pages_ready = True
        self.reload_pages()

    # ------------------------------------------------------------------ building

    def _build(self) -> None:
        self.emoji_page = EmojiPage(self)
        self.phrases_page = PhrasesPage(self)
        self.signature_page = SignaturePage(self)
        self.note_page = NotePage(self)
        self.pages = {"emoji": self.emoji_page, "phrases": self.phrases_page,
                      "signature": self.signature_page, "note": self.note_page}

        self.stack = Adw.ViewStack(vexpand=True)
        for page_id, title, icon in PAGES:
            self.stack.add_titled_with_icon(self.pages[page_id], page_id, title, icon)

        header = Adw.HeaderBar()
        # The visible page's own buttons, at the start of the header bar.
        self.header_boxes: dict[str, Gtk.Box] = {}
        for page_id, page in self.pages.items():
            box = Gtk.Box(spacing=6)
            for widget in page.header_widgets():
                box.append(widget)
            self.header_boxes[page_id] = box
            header.pack_start(box)
        menu_button = Gtk.MenuButton(icon_name="open-menu-symbolic", primary=True,
                                     tooltip_text="Main Menu")
        self.menu_button = menu_button
        header.pack_end(menu_button)
        self._refresh_menu()

        self.switcher = Adw.ViewSwitcher(policy=Adw.ViewSwitcherPolicy.WIDE, stack=self.stack)
        self.narrow_title = Adw.WindowTitle(title=APP_NAME, visible=False)
        title_box = Gtk.Box()
        title_box.append(self.switcher)
        title_box.append(self.narrow_title)
        header.set_title_widget(title_box)

        switcher_bar = Adw.ViewSwitcherBar(stack=self.stack)
        view = Adw.ToolbarView()
        view.add_top_bar(header)
        view.set_content(self.stack)
        view.add_bottom_bar(switcher_bar)
        self.toasts = Adw.ToastOverlay(child=view)
        self.set_content(self.toasts)

        narrow = Adw.Breakpoint.new(Adw.BreakpointCondition.parse(NARROW_BREAKPOINT))
        narrow.add_setter(switcher_bar, "reveal", True)
        narrow.add_setter(self.switcher, "visible", False)
        narrow.add_setter(self.narrow_title, "visible", True)
        self.add_breakpoint(narrow)

        self.stack.connect("notify::visible-child-name", self._on_page_changed)
        self._on_page_changed()

    def _install_bubble_shortcuts(self) -> None:
        """Ctrl+C runs win.copy only when the focused widget did not use it
        (a search box or the note body copies its own selection first):
        a bubble-phase controller on the window sees a key last."""
        controller = Gtk.ShortcutController(propagation_phase=Gtk.PropagationPhase.BUBBLE)
        for action, accels in accelerators("gtk4", bubble=True).items():
            trigger = Gtk.ShortcutTrigger.parse_string("|".join(accels))
            if trigger is not None:
                controller.add_shortcut(Gtk.Shortcut.new(trigger, Gtk.NamedAction.new(action)))
        self.add_controller(controller)

    def _refresh_menu(self) -> None:
        # A new model each time (GTK 4.14 popovers cope badly with submenus
        # changing under them).
        self.menu_button.set_menu_model(
            actions.primary_menu(list(self.config.get("recent_workspaces", []) or [])))

    # ------------------------------------------------------------------ pages

    def current_page(self) -> str:
        return self.stack.get_visible_child_name() or "emoji"

    def show_page(self, page_id: str) -> None:
        if page_id in self.pages:
            self.stack.set_visible_child_name(page_id)

    def _on_page_changed(self, *_args) -> None:
        page = self.current_page()
        for page_id, box in self.header_boxes.items():
            box.set_visible(page_id == page)
        self.narrow_title.set_title(dict((p[0], p[1]) for p in PAGES).get(page, APP_NAME))
        self.update_actions()

    def update_actions(self) -> None:
        actions.update(self)

    def reload_pages(self) -> None:
        for page in self.pages.values():
            page.reload()
        self.update_actions()

    # ------------------------------------------------------------------ workspace

    def choose_workspace(self) -> None:
        dialog = Gtk.FileDialog(title="Open Workspace Folder", modal=True, accept_label="Open")
        if self.workspace is not None:
            parent = os.path.dirname(self.workspace.path)
            if os.path.isdir(parent):
                dialog.set_initial_folder(Gio.File.new_for_path(parent))

        def done(d: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
            try:
                folder = d.select_folder_finish(result)
            except GLib.Error:
                return  # cancelled
            if folder is not None and folder.get_path():
                self.open_path(folder.get_path())
        dialog.select_folder(self, None, done)

    def open_path(self, path: str) -> None:
        """Open a workspace, asking before starting one in an unrelated folder."""
        if not path or not os.path.isdir(path):
            dialogs.alert(self, "Folder Not Found", f"“{path}” is not a folder.")
            return
        if looks_like_workspace(path):
            self._open(path)
            return
        name = os.path.basename(os.path.abspath(path)) or path
        dialogs.confirm(
            self, "Start a Workspace Here?",
            f"“{name}” has no favourite_emoji.csv, phrases.csv or mailsigs folder "
            "yet. They will be created there with sample content, as plain text files you "
            "can edit.", "Create", lambda: self._open(path))

    def reopen_last(self) -> None:
        if not self.config.get("reopen_last", True):
            return
        last = self.config.get("last_workspace")
        if last and os.path.isdir(last):
            self._open(last, quiet=True)

    def _open(self, path: str, quiet: bool = False) -> None:
        path = os.path.abspath(path)
        try:
            ws = Workspace(path)
            ws.ensure_scaffold()
            ws.scan()
        except OSError as exc:
            if not quiet:
                dialogs.alert(self, "Could Not Open the Workspace", str(exc))
            return
        self.workspace = ws
        self.config.set("last_workspace", path)
        recent = [p for p in self.config.get("recent_workspaces", []) or [] if p != path]
        self.config.set("recent_workspaces", [path, *recent][:10])
        self._refresh_menu()
        self.set_title(f"{os.path.basename(path) or path} — {APP_NAME}")
        self.reload_pages()

    def clear_recents(self) -> None:
        self.config.set("recent_workspaces", [])
        self._refresh_menu()
        self.update_actions()

    def show_in_files(self) -> None:
        if self.workspace is None:
            return
        launcher = Gtk.FileLauncher.new(Gio.File.new_for_path(self.workspace.path))
        launcher.launch(self, None, None)

    def refresh(self) -> None:
        """Re-read the workspace; Signature and Note also get a new reference
        (as View → Refresh does in GTK 3)."""
        if self.workspace is not None:
            self.workspace.scan()
        self.reload_pages()
        page = self.current_page()
        if page == "signature":
            self.signature_page.refresh_message_ref()
        elif page == "note":
            self.note_page.refresh_message_ref()
        if page not in ("signature", "note"):
            self.toast("Reloaded from disk")

    # ------------------------------------------------------------------ page commands

    def copy_current(self) -> None:
        page = self.current_page()
        if page == "emoji":
            self.emoji_page.copy_selected()
        elif page == "phrases":
            self.phrases_page.copy_selected()
        elif page == "signature":
            self.signature_page.copy_signature()

    def find(self) -> None:
        page = self.current_page()
        if page in ("emoji", "phrases"):
            self.pages[page].focus_search()

    def new_ref(self) -> None:
        if self.current_page() == "note":
            self.note_page.refresh_message_ref()
        else:
            self.signature_page.refresh_message_ref()

    # ------------------------------------------------------------------ preferences

    def apply_font(self, font: str) -> None:
        """The signature font: the Signature preview and the Note fields."""
        self.fonts.set_font(font)
        self.signature_page.set_custom_font(bool(font))
        self.note_page.set_custom_font(bool(font))

    def show_preferences(self) -> None:
        from .gtk4_preferences import PreferencesDialog
        PreferencesDialog(self).present(self)

    def show_shortcuts(self) -> None:
        from .gtk4_shortcuts import shortcuts_window
        shortcuts_window(self).present()

    def show_about(self) -> None:
        # Spec §8.1: the app icon, name and description; no version or licence.
        about = Adw.AboutDialog(application_name=APP_NAME, application_icon=self.icon_name,
                                developer_name="QDVC", comments=APP_SUMMARY + ".",
                                website=REPOSITORY_URL)
        about.present(self)

    # ------------------------------------------------------------------ misc

    def toast(self, text: str) -> None:
        self.toasts.add_toast(Adw.Toast(title=GLib.markup_escape_text(text), timeout=2))

    def _on_close_request(self, *_args) -> bool:
        maximized = self.is_maximized()
        if not maximized:
            width, height = self.get_default_size()
            if width > 0 and height > 0:
                self.config.set("window", [width, height])
        self.config.set("window_maximized", maximized)
        return False
