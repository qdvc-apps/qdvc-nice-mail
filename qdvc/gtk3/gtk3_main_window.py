"""GTK3 MainWindow (spec §8).

Layout, top to bottom:
    menubar
    notebook tab bar (tabs only; pages are empty placeholders)
    per-tab toolbar (a Gtk.Stack swapped on tab switch)
    content area (the active tab's widget, shown in a Gtk.Stack)
    statusbar

The notebook exists only to render the tab BAR above the toolbar; the actual
tab content lives in a separate Gtk.Stack below the toolbar so the toolbar can
sit between the tab bar and the content, as required.
"""
from __future__ import annotations

import os

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk  # noqa: E402

from .. import APP_NAME, __version__  # noqa: E402
from ..platform_utils import reveal_in_file_manager  # noqa: E402
from ..ui_prefs import EMOJI_BLOCKS, SKIN_TONE_LABELS, SHORTCUTS  # noqa: E402
from ..workspace import Workspace  # noqa: E402
from .gtk3_emoji_tab import EmojiTab  # noqa: E402
from .gtk3_phrases_tab import PhrasesTab  # noqa: E402
from .gtk3_signature_tab import SignatureTab  # noqa: E402

TAB_EMOJI = 0
TAB_PHRASES = 1
TAB_SIGNATURE = 2


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, app, icon_name: str = "internet-mail") -> None:  # noqa: ANN001
        super().__init__(application=app, title=APP_NAME)
        self.app = app
        self.config = app.config
        self.workspace: Workspace | None = None

        self.set_icon_name(icon_name)
        w, h = self.config.get("window", [900, 600])
        self.set_default_size(int(w), int(h))
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect("delete-event", self._on_delete)

        self.accel_group = Gtk.AccelGroup()
        self.add_accel_group(self.accel_group)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(root)

        root.pack_start(self._build_menubar(), False, False, 0)

        # --- tab bar (above toolbar) --------------------------------------
        self.notebook = Gtk.Notebook()
        self.notebook.set_show_border(False)
        for label in ("Emoji", "Phrases", "Signature"):
            # Empty page: real content is rendered in self.content_stack below.
            tab_label = Gtk.Label(label=label)
            tab_label.set_margin_top(2)
            tab_label.set_margin_bottom(2)
            tab_label.set_margin_start(2)
            tab_label.set_margin_end(2)
            self.notebook.append_page(Gtk.Box(), tab_label)
        self.notebook.connect("switch-page", self._on_switch_page)
        root.pack_start(self.notebook, False, False, 0)

        # --- per-tab toolbar (swapped by a stack) -------------------------
        self.toolbar_stack = Gtk.Stack()
        root.pack_start(self.toolbar_stack, False, False, 0)
        root.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)

        # --- content area -------------------------------------------------
        self.content_stack = Gtk.Stack()
        root.pack_start(self.content_stack, True, True, 0)

        # --- statusbar ----------------------------------------------------
        self.statusbar = Gtk.Statusbar()
        self._status_ctx = self.statusbar.get_context_id("main")
        root.pack_start(self.statusbar, False, False, 0)

        # Build the three tabs + their toolbars.
        self.emoji_tab = EmojiTab(self)
        self.phrases_tab = PhrasesTab(self)
        self.signature_tab = SignatureTab(self)
        for t in (self.emoji_tab, self.phrases_tab, self.signature_tab):
            t.connect("status", lambda _w, msg: self.set_status(msg))

        self.content_stack.add_named(self.emoji_tab, "emoji")
        self.content_stack.add_named(self.phrases_tab, "phrases")
        self.content_stack.add_named(self.signature_tab, "signature")

        self.toolbar_stack.add_named(self._build_emoji_toolbar(), "emoji")
        self.toolbar_stack.add_named(self._build_phrases_toolbar(), "phrases")
        self.toolbar_stack.add_named(self._build_signature_toolbar(), "signature")

        self._wire_accelerators()
        self._show_tab(TAB_EMOJI)
        self._update_actions_sensitivity()
        self.show_all()

    # ---- menubar ---------------------------------------------------------
    # Fallback chains for icon names that some themes lack, tried in order.
    _ICON_FALLBACKS = {
        "help-about": ["help-about", "help-browser", "help-contents", "dialog-information"],
    }

    def _resolve_icon(self, name: str) -> str | None:
        """Return the first icon name present in the theme, or None if none are."""
        theme = Gtk.IconTheme.get_default()
        for candidate in self._ICON_FALLBACKS.get(name, [name]):
            if theme.has_icon(candidate):
                return candidate
        return None

    def _menu_item(
        self,
        label: str,
        icon: str | None = None,
        accel: tuple[int, int] | None = None,
    ) -> Gtk.MenuItem:
        """A menu item with a fixed icon slot, label, and optional accel hint.

        `accel` is a (keyval, modifier) pair; when given, the accelerator is
        both attached to the item and displayed right-aligned, and the item is
        returned ready to have its `activate` handler connected.
        """
        item = Gtk.MenuItem()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        # Fixed-width icon slot keeps every label left-aligned to the same x,
        # whether or not the item has an icon (fixes uneven left padding).
        icon_slot = Gtk.Box()
        icon_slot.set_size_request(16, 16)
        resolved = self._resolve_icon(icon) if icon else None
        if resolved:
            icon_slot.pack_start(
                Gtk.Image.new_from_icon_name(resolved, Gtk.IconSize.MENU),
                False, False, 0,
            )
        box.pack_start(icon_slot, False, False, 0)

        box.pack_start(Gtk.Label(label=label, xalign=0.0), True, True, 0)

        if accel is not None:
            keyval, mods = accel
            accel_label = Gtk.Label(label=Gtk.accelerator_get_label(keyval, mods))
            accel_label.get_style_context().add_class("accelerator")
            accel_label.set_sensitive(False)
            box.pack_end(accel_label, False, False, 0)
            item.add_accelerator(
                "activate", self.accel_group, keyval, mods, Gtk.AccelFlags.VISIBLE,
            )

        item.add(box)
        return item

    def _build_menubar(self) -> Gtk.MenuBar:
        menubar = Gtk.MenuBar()

        # File
        file_menu = Gtk.Menu()
        file_item = Gtk.MenuItem(label="File")
        file_item.set_submenu(file_menu)

        self.mi_open = self._menu_item(
            "Open Workspace…", "document-open",
            accel=(Gdk.KEY_o, Gdk.ModifierType.CONTROL_MASK),
        )
        self.mi_open.connect("activate", lambda *_: self.choose_workspace())
        file_menu.append(self.mi_open)

        self.mi_reveal = self._menu_item("Reveal Workspace in File Manager", "folder")
        self.mi_reveal.connect("activate", lambda *_: self._reveal_workspace())
        file_menu.append(self.mi_reveal)

        file_menu.append(Gtk.SeparatorMenuItem())
        mi_quit = self._menu_item(
            "Quit", "application-exit",
            accel=(Gdk.KEY_q, Gdk.ModifierType.CONTROL_MASK),
        )
        mi_quit.connect("activate", lambda *_: self.app.quit())
        file_menu.append(mi_quit)
        menubar.append(file_item)

        # Edit
        edit_menu = Gtk.Menu()
        edit_item = Gtk.MenuItem(label="Edit")
        edit_item.set_submenu(edit_menu)

        mi_copy = self._menu_item(
            "Copy", "edit-copy",
            accel=(Gdk.KEY_c, Gdk.ModifierType.CONTROL_MASK),
        )
        mi_copy.connect("activate", lambda *_: self.copy_current_tab())
        edit_menu.append(mi_copy)
        edit_menu.append(Gtk.SeparatorMenuItem())

        mi_prefs = self._menu_item(
            "Preferences", "preferences-system",
            accel=(Gdk.KEY_comma, Gdk.ModifierType.CONTROL_MASK),
        )
        mi_prefs.connect("activate", lambda *_: self._open_preferences())
        edit_menu.append(mi_prefs)
        menubar.append(edit_item)

        # View
        view_menu = Gtk.Menu()
        view_item = Gtk.MenuItem(label="View")
        view_item.set_submenu(view_menu)
        for idx, (label, key) in enumerate((
            ("Emoji", Gdk.KEY_1), ("Phrases", Gdk.KEY_2), ("Signature", Gdk.KEY_3),
        )):
            mi = self._menu_item(label, accel=(key, Gdk.ModifierType.MOD1_MASK))
            mi.connect("activate", lambda _w, i=idx: self._show_tab(i))
            view_menu.append(mi)
        view_menu.append(Gtk.SeparatorMenuItem())
        mi_refresh = self._menu_item(
            "Refresh", "view-refresh",
            accel=(Gdk.KEY_r, Gdk.ModifierType.CONTROL_MASK),
        )
        mi_refresh.connect("activate", lambda *_: self.refresh_current_tab())
        view_menu.append(mi_refresh)
        menubar.append(view_item)

        # Help
        help_menu = Gtk.Menu()
        help_item = Gtk.MenuItem(label="Help")
        help_item.set_submenu(help_menu)
        mi_about = self._menu_item("About", "help-about")
        mi_about.connect("activate", lambda *_: self._show_about())
        help_menu.append(mi_about)
        menubar.append(help_item)

        return menubar

    # ---- toolbars --------------------------------------------------------
    def _apply_toolbar_style(self, toolbar: Gtk.Toolbar) -> None:
        below = self.config.toolbar_style == "below"
        toolbar.set_style(Gtk.ToolbarStyle.BOTH if below else Gtk.ToolbarStyle.BOTH_HORIZ)

    def _build_emoji_toolbar(self) -> Gtk.Toolbar:
        tb = Gtk.Toolbar()
        self._apply_toolbar_style(tb)

        # Block dropdown (Favourites / All Emoji).
        block_item = Gtk.ToolItem()
        block_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        block_box.pack_start(Gtk.Label(label="Block:"), False, False, 2)
        self.block_combo = Gtk.ComboBoxText()
        for bid, blabel in EMOJI_BLOCKS:
            self.block_combo.append(bid, blabel)
        self.block_combo.set_active_id("favourites")
        # Pin width so focus/prelight states can't relayout the toolbar.
        self.block_combo.set_size_request(130, -1)
        self.block_combo.connect(
            "changed", lambda c: self.emoji_tab.set_block(c.get_active_id() or "favourites")
        )
        block_box.pack_start(self.block_combo, False, False, 0)
        block_item.add(block_box)
        tb.insert(block_item, -1)

        # Skin tone dropdown.
        tone_item = Gtk.ToolItem()
        tone_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        tone_box.pack_start(Gtk.Label(label="Skin tone:"), False, False, 2)
        self.tone_combo = Gtk.ComboBoxText()
        for tid, tlabel in SKIN_TONE_LABELS:
            self.tone_combo.append(tid, tlabel)
        self.tone_combo.set_active_id("none")
        # Pin width so hovering the dropdown does not resize other items.
        self.tone_combo.set_size_request(140, -1)
        self.tone_combo.connect(
            "changed", lambda c: self.emoji_tab.set_skin_tone(c.get_active_id() or "none")
        )
        tone_box.pack_start(self.tone_combo, False, False, 0)
        tone_item.add(tone_box)
        tb.insert(tone_item, -1)

        tb.insert(Gtk.SeparatorToolItem(), -1)

        # Add a custom (pasted) emoji to favourites.
        custom_btn = Gtk.ToolButton(label="Add Custom")
        custom_btn.set_icon_name("list-add")
        custom_btn.set_is_important(True)
        custom_btn.set_tooltip_text(
            "Add a pasted emoji to favourites (e.g. one not in the list)"
        )
        custom_btn.connect("clicked", lambda *_: self.emoji_tab.add_custom_favourite())
        tb.insert(custom_btn, -1)

        tb.insert(Gtk.SeparatorToolItem(), -1)

        # Search entry.
        search_item = Gtk.ToolItem()
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search name, description or label…")
        self.search_entry.set_width_chars(28)
        self.search_entry.connect(
            "search-changed", lambda e: self.emoji_tab.set_query(e.get_text())
        )
        search_item.add(self.search_entry)
        search_item.set_expand(True)
        tb.insert(search_item, -1)

        # Move up/down (reorders favourites).
        up_btn = Gtk.ToolButton(label="Move Up")
        up_btn.set_icon_name("go-up")
        up_btn.set_is_important(True)
        up_btn.connect("clicked", lambda *_: self.emoji_tab.move_selected(-1))
        tb.insert(up_btn, -1)

        down_btn = Gtk.ToolButton(label="Move Down")
        down_btn.set_icon_name("go-down")
        down_btn.set_is_important(True)
        down_btn.connect("clicked", lambda *_: self.emoji_tab.move_selected(1))
        tb.insert(down_btn, -1)

        tb.insert(Gtk.SeparatorToolItem(), -1)

        # Copy button.
        copy_btn = Gtk.ToolButton(label="Copy")
        copy_btn.set_icon_name("edit-copy")
        copy_btn.set_is_important(True)
        copy_btn.connect("clicked", lambda *_: self.emoji_tab.copy_selected())
        tb.insert(copy_btn, -1)

        return tb

    def _build_phrases_toolbar(self) -> Gtk.Toolbar:
        tb = Gtk.Toolbar()
        self._apply_toolbar_style(tb)

        add_btn = Gtk.ToolButton(label="Add")
        add_btn.set_icon_name("list-add")
        add_btn.set_is_important(True)
        add_btn.connect("clicked", lambda *_: self.phrases_tab.add_phrase())
        tb.insert(add_btn, -1)

        edit_btn = Gtk.ToolButton(label="Edit")
        edit_btn.set_icon_name("document-edit")
        edit_btn.set_is_important(True)
        edit_btn.connect("clicked", lambda *_: self.phrases_tab.edit_phrase())
        tb.insert(edit_btn, -1)

        del_btn = Gtk.ToolButton(label="Delete")
        del_btn.set_icon_name("list-remove")
        del_btn.set_is_important(True)
        del_btn.connect("clicked", lambda *_: self.phrases_tab.delete_phrase())
        tb.insert(del_btn, -1)

        tb.insert(Gtk.SeparatorToolItem(), -1)

        up_btn = Gtk.ToolButton(label="Move Up")
        up_btn.set_icon_name("go-up")
        up_btn.set_is_important(True)
        up_btn.connect("clicked", lambda *_: self.phrases_tab.move_selected(-1))
        tb.insert(up_btn, -1)

        down_btn = Gtk.ToolButton(label="Move Down")
        down_btn.set_icon_name("go-down")
        down_btn.set_is_important(True)
        down_btn.connect("clicked", lambda *_: self.phrases_tab.move_selected(1))
        tb.insert(down_btn, -1)

        tb.insert(Gtk.SeparatorToolItem(), -1)

        copy_btn = Gtk.ToolButton(label="Copy")
        copy_btn.set_icon_name("edit-copy")
        copy_btn.set_is_important(True)
        copy_btn.connect("clicked", lambda *_: self.phrases_tab.copy_selected())
        tb.insert(copy_btn, -1)

        return tb

    def _build_signature_toolbar(self) -> Gtk.Toolbar:
        tb = Gtk.Toolbar()
        self._apply_toolbar_style(tb)

        # Profile dropdown.
        prof_item = Gtk.ToolItem()
        prof_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        prof_box.pack_start(Gtk.Label(label="Profile:"), False, False, 2)
        self.profile_combo = Gtk.ComboBoxText()
        self.profile_combo.connect("changed", self._on_profile_changed)
        prof_box.pack_start(self.profile_combo, False, False, 0)
        prof_item.add(prof_box)
        tb.insert(prof_item, -1)

        tb.insert(Gtk.SeparatorToolItem(), -1)

        # Disclaimer toggle.
        self.disclaimer_toggle = Gtk.ToggleToolButton(label="Disclaimer")
        self.disclaimer_toggle.set_icon_name("dialog-information")
        self.disclaimer_toggle.set_is_important(True)
        self.disclaimer_toggle.set_active(bool(self.config.get("include_disclaimer", True)))
        self.disclaimer_toggle.connect("toggled", self._on_disclaimer_toggled)
        tb.insert(self.disclaimer_toggle, -1)

        # Refresh message ref.
        refresh_btn = Gtk.ToolButton(label="New Ref")
        refresh_btn.set_icon_name("view-refresh")
        refresh_btn.set_is_important(True)
        refresh_btn.connect("clicked", lambda *_: self.signature_tab.refresh_message_ref())
        tb.insert(refresh_btn, -1)

        tb.insert(Gtk.SeparatorToolItem(), -1)

        copy_btn = Gtk.ToolButton(label="Copy")
        copy_btn.set_icon_name("edit-copy")
        copy_btn.set_is_important(True)
        copy_btn.connect("clicked", lambda *_: self.signature_tab.copy_signature())
        tb.insert(copy_btn, -1)

        return tb

    def _on_profile_changed(self, combo: Gtk.ComboBoxText) -> None:
        self.signature_tab.set_profile(combo.get_active_id())

    def _on_disclaimer_toggled(self, btn: Gtk.ToggleToolButton) -> None:
        self.config.set("include_disclaimer", btn.get_active())
        self.signature_tab.set_include_disclaimer(btn.get_active())

    # ---- accelerators ----------------------------------------------------
    def _wire_accelerators(self) -> None:
        # F5 -> refresh message ref (context-scoped, window-level binding).
        self.accel_group.connect(
            Gdk.KEY_F5, 0, Gtk.AccelFlags.VISIBLE,
            lambda *a: (self.signature_tab.refresh_message_ref() or True),
        )

    # ---- tab switching ---------------------------------------------------
    def _show_tab(self, index: int) -> None:
        self.notebook.set_current_page(index)

    def _on_switch_page(self, _notebook, _page, index: int) -> None:  # noqa: ANN001
        name = {TAB_EMOJI: "emoji", TAB_PHRASES: "phrases", TAB_SIGNATURE: "signature"}[index]
        self.content_stack.set_visible_child_name(name)
        self.toolbar_stack.set_visible_child_name(name)
        self._update_actions_sensitivity()

    def _current_tab_index(self) -> int:
        return self.notebook.get_current_page()

    def copy_current_tab(self) -> None:
        """Edit -> Copy: behaviour depends on the active tab."""
        idx = self._current_tab_index()
        if idx == TAB_EMOJI:
            self.emoji_tab.copy_selected()
        elif idx == TAB_PHRASES:
            self.phrases_tab.copy_selected()
        elif idx == TAB_SIGNATURE:
            self.signature_tab.copy_signature()

    def refresh_current_tab(self) -> None:
        """View -> Refresh: reload from disk; Signature also gets a new ref."""
        if self.workspace is not None:
            self.workspace.scan()
        idx = self._current_tab_index()
        if idx == TAB_EMOJI:
            self.emoji_tab.reload()
        elif idx == TAB_PHRASES:
            self.phrases_tab.reload()
        elif idx == TAB_SIGNATURE:
            # Reload from disk and generate a fresh message ref.
            self.signature_tab.refresh_message_ref()

    # ---- workspace -------------------------------------------------------
    def choose_workspace(self) -> None:
        dialog = Gtk.FileChooserDialog(
            title="Open Workspace Folder",
            transient_for=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK,
        )
        resp = dialog.run()
        path = dialog.get_filename()
        dialog.destroy()
        if resp == Gtk.ResponseType.OK and path:
            self.open_workspace(path)

    def open_workspace(self, path: str) -> None:
        if not path or not os.path.isdir(path):
            self.set_status("Workspace folder not found.")
            return
        self.workspace = Workspace(path)
        self.workspace.ensure_scaffold()
        self.workspace.scan()
        self.config.set("last_workspace", path)
        recent = list(self.config.get("recent_workspaces", []))
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self.config.set("recent_workspaces", recent[:10])

        # Repopulate profile dropdown.
        self.profile_combo.remove_all()
        for prof in self.workspace.profiles:
            self.profile_combo.append(prof.name, prof.name)
        if self.workspace.profiles:
            saved = self.config.get("profile")
            names = [p.name for p in self.workspace.profiles]
            self.profile_combo.set_active_id(saved if saved in names else names[0])

        self.emoji_tab.reload()
        self.phrases_tab.reload()
        self.signature_tab.reload()
        self._update_actions_sensitivity()
        self.set_status(f"Workspace: {path}")

    def _reveal_workspace(self) -> None:
        if self.workspace:
            reveal_in_file_manager(self.workspace.path)

    # ---- misc ------------------------------------------------------------
    def _update_actions_sensitivity(self) -> None:
        has_ws = self.workspace is not None
        self.mi_reveal.set_sensitive(has_ws)

    def _open_preferences(self) -> None:
        from .gtk3_preferences import PreferencesDialog
        dlg = PreferencesDialog(self)
        dlg.run()
        dlg.destroy()
        # Re-apply toolbar style live by rebuilding toolbars.
        self._rebuild_toolbars()

    def _rebuild_toolbars(self) -> None:
        for name in ("emoji", "phrases", "signature"):
            child = self.toolbar_stack.get_child_by_name(name)
            if child is not None:
                self.toolbar_stack.remove(child)
        self.toolbar_stack.add_named(self._build_emoji_toolbar(), "emoji")
        self.toolbar_stack.add_named(self._build_phrases_toolbar(), "phrases")
        self.toolbar_stack.add_named(self._build_signature_toolbar(), "signature")
        # Restore profile list if a workspace is open.
        if self.workspace:
            for prof in self.workspace.profiles:
                self.profile_combo.append(prof.name, prof.name)
            if self.workspace.profiles:
                self.profile_combo.set_active(0)
        self.toolbar_stack.show_all()
        idx = self.notebook.get_current_page()
        self._on_switch_page(self.notebook, None, idx)

    def set_status(self, msg: str) -> None:
        self.statusbar.pop(self._status_ctx)
        self.statusbar.push(self._status_ctx, msg)

    def _show_about(self) -> None:
        about = Gtk.AboutDialog(transient_for=self, modal=True)
        about.set_program_name(APP_NAME)
        about.set_version(__version__)
        about.set_comments("Write emails faster with reusable components.")
        about.run()
        about.destroy()

    def _on_delete(self, *_a) -> bool:
        alloc = self.get_allocation()
        self.config.set("window", [alloc.width, alloc.height])
        return False
