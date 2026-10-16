"""Every command of the window, as a ``win.*`` ``Gio.SimpleAction`` (spec §9).

Header-bar buttons, the primary menu, context menus, action bars and the
keyboard shortcuts (``ui_prefs.SHORTCUTS``) all name these actions, so one
action drives every surface, and :func:`update` greys them all at once (the
GTK 4 counterpart of GTK 3's ``_update_actions_sensitivity``).
"""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib  # noqa: E402

from .. import APP_NAME  # noqa: E402
from ..ui_prefs import home_relative  # noqa: E402


def install(win) -> None:  # noqa: ANN001
    win.actions = {}
    plain = {
        # Workspace
        "open-workspace": win.choose_workspace,
        "clear-recents": win.clear_recents,
        "show-in-files": win.show_in_files,
        "refresh": win.refresh,
        # Page-adaptive commands
        "copy": win.copy_current,
        "find": win.find,
        "new-ref": win.new_ref,
        # Emoji page
        "add-custom-emoji": lambda: win.emoji_page.add_custom(),
        "toggle-favourite": lambda: win.emoji_page.toggle_favourite(),
        "set-emoji-label": lambda: win.emoji_page.set_label(),
        "move-emoji-up": lambda: win.emoji_page.move_selected(-1),
        "move-emoji-down": lambda: win.emoji_page.move_selected(1),
        # Phrases page
        "new-phrase": lambda: win.phrases_page.add_phrase(),
        "edit-phrase": lambda: win.phrases_page.edit_phrase(),
        "delete-phrase": lambda: win.phrases_page.delete_phrase(),
        # Note to Self page
        "send-note": lambda: win.note_page.send(),
        # General
        "preferences": win.show_preferences,
        "shortcuts": win.show_shortcuts,
        "about": win.show_about,
    }
    for name, fn in plain.items():
        _add(win, name, lambda _a, _p, fn=fn: fn())

    for name, fn in {"open-recent": win.open_path, "show-page": win.show_page}.items():
        _add(win, name, lambda _a, p, fn=fn: fn(p.get_string()), GLib.VariantType.new("s"))

    # The Emoji page's block (Favourites | All Emoji): a radio choice.
    block = Gio.SimpleAction.new_stateful("emoji-block", GLib.VariantType.new("s"),
                                          GLib.Variant("s", "favourites"))

    def change_block(action: Gio.SimpleAction, value: GLib.Variant) -> None:
        action.set_state(value)
        win.emoji_page.set_block(value.get_string())
    block.connect("change-state", change_block)
    win.add_action(block)
    win.actions["emoji-block"] = block


def _add(win, name: str, handler, ptype: GLib.VariantType | None = None) -> None:  # noqa: ANN001
    action = Gio.SimpleAction.new(name, ptype)
    action.connect("activate", handler)
    win.add_action(action)
    win.actions[name] = action


def update(win) -> None:  # noqa: ANN001
    """Enable or disable every action for the current page, workspace and
    selection."""
    if not getattr(win, "pages_ready", False):
        return
    a = win.actions
    ws = win.workspace is not None
    page = win.current_page()
    emoji = win.emoji_page
    item = emoji.selected_item()
    phrase = win.phrases_page.selected_phrase()

    for name in ("show-in-files", "refresh", "emoji-block", "add-custom-emoji",
                 "new-phrase"):
        a[name].set_enabled(ws)
    a["clear-recents"].set_enabled(bool(win.config.get("recent_workspaces", [])))

    copyable = {
        "emoji": item is not None,
        "phrases": phrase is not None,
        "signature": ws,
    }
    a["copy"].set_enabled(copyable.get(page, False))
    a["find"].set_enabled(ws and page in ("emoji", "phrases"))
    a["new-ref"].set_enabled(page == "note" or (page == "signature" and ws))

    a["toggle-favourite"].set_enabled(ws and item is not None)
    a["set-emoji-label"].set_enabled(ws and item is not None and item.favourite)
    a["move-emoji-up"].set_enabled(ws and emoji.can_move(-1))
    a["move-emoji-down"].set_enabled(ws and emoji.can_move(1))
    a["edit-phrase"].set_enabled(ws and phrase is not None)
    a["delete-phrase"].set_enabled(ws and phrase is not None)


def primary_menu(recents: list[str]) -> Gio.Menu:
    """The primary menu; the HIG's Preferences / Keyboard Shortcuts / About
    section comes last (spec §9). Rebuilt when the recent list changes."""
    menu = Gio.Menu()
    workspace = Gio.Menu()
    workspace.append("Open Workspace…", "win.open-workspace")
    if recents:
        recent = Gio.Menu()
        paths = Gio.Menu()
        for path in recents[:8]:
            item = Gio.MenuItem.new(home_relative(path), None)
            item.set_action_and_target_value("win.open-recent", GLib.Variant("s", path))
            paths.append_item(item)
        recent.append_section(None, paths)
        clear = Gio.Menu()
        clear.append("Clear List", "win.clear-recents")
        recent.append_section(None, clear)
        workspace.append_submenu("Open Recent", recent)
    workspace.append("Show in Files", "win.show-in-files")
    workspace.append("Refresh from Disk", "win.refresh")
    menu.append_section(None, workspace)

    general = Gio.Menu()
    general.append("Preferences", "win.preferences")
    general.append("Keyboard Shortcuts", "win.shortcuts")
    general.append(f"About {APP_NAME}", "win.about")
    menu.append_section(None, general)
    return menu
