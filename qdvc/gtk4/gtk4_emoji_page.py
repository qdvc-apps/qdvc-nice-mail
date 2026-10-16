"""The Emoji page: a searchable table of emoji (symbol, name, user label).

    Gtk.Box
      Adw.ToolbarView
        top:     [ Favourites | All Emoji ]  [ search entry ]
        content: Gtk.Stack ── "list": ScrolledWindow(Gtk.ColumnView)
                            ├ "no-workspace" / "no-favourites" / "no-results"
        bottom:  Gtk.ActionBar  [★ favourite] [✎ label]        [↑][↓]
      Gtk.PopoverMenu (right-click / long-press menu)

The rows come from ``ui_prefs.emoji_block_items`` and are filtered with
``ui_prefs.emoji_matches``, the rules the GTK 3 tab uses. Copying happens
from the header bar's Copy button, Ctrl+C, Enter or a double-click, and
Enter in the search box copies the first match.
"""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Graphene", "1.0")
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Graphene, Gtk, Pango  # noqa: E402

from ..ui_prefs import emoji_block_items, emoji_display_name, emoji_matches  # noqa: E402
from . import gtk4_dialogs as dialogs  # noqa: E402
from .gtk4_widgets import copy_text, icon_button, no_workspace_page, status_page  # noqa: E402


class EmojiItem(GObject.Object):
    __gtype_name__ = "QdvcNiceMailEmojiItem"

    def __init__(self, emoji, glyph: str, name: str, label: str, favourite: bool) -> None:  # noqa: ANN001
        super().__init__()
        self.emoji = emoji
        self.glyph = glyph
        self.name = name
        self.label = label
        self.favourite = favourite


class EmojiPage(Gtk.Box):
    def __init__(self, window) -> None:  # noqa: ANN001
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.window = window
        self.block = "favourites"
        self.skin_tone = window.config.get("skin_tone", "none") or "none"
        self.query = ""

        # Model: store -> filter -> single selection.
        self.store = Gio.ListStore(item_type=EmojiItem)
        self.filter = Gtk.CustomFilter.new(lambda item, _data: self._match(item), None)
        self.filtered = Gtk.FilterListModel(model=self.store, filter=self.filter)
        self.selection = Gtk.SingleSelection(model=self.filtered, autoselect=True)
        self.selection.connect("notify::selected", self._on_selection_changed)

        self.view = Gtk.ColumnView(model=self.selection, show_column_separators=False,
                                   reorderable=False)
        self.view.add_css_class("data-table")
        self._add_column("Emoji", "glyph", fixed_width=76)
        self._add_column("Name", "name", expand=True)
        self._add_column("User Label", "label", fixed_width=180)
        self.view.connect("activate", lambda _v, pos: self.copy_at(pos))
        scroller = Gtk.ScrolledWindow(child=self.view, vexpand=True)

        self.stack = Gtk.Stack()
        self.stack.add_named(scroller, "list")
        self.stack.add_named(no_workspace_page("face-smile-symbolic", "your emoji"),
                             "no-workspace")
        self.stack.add_named(status_page(
            "non-starred-symbolic", "No Favourites Yet",
            "Find the emoji you use most in All Emoji and star them: they will be listed "
            "here, in the order you choose.",
            "Show All Emoji", "win.emoji-block", GLib.Variant("s", "all")), "no-favourites")
        self.no_results = status_page("edit-find-symbolic", "No Results",
                                      "No emoji name, description or user label matches.")
        self.stack.add_named(self.no_results, "no-results")

        self.toolbar = Adw.ToolbarView(top_bar_style=Adw.ToolbarStyle.RAISED,
                                       bottom_bar_style=Adw.ToolbarStyle.RAISED,
                                       vexpand=True)
        self.toolbar.add_top_bar(self._build_search_strip())
        self.toolbar.set_content(self.stack)
        self.toolbar.add_bottom_bar(self._build_action_bar())
        self.append(self.toolbar)

        # Context menu, parented to this Box so it is unparented with it.
        self.popover = Gtk.PopoverMenu.new_from_model(None)
        self.popover.set_has_arrow(False)
        self.popover.set_halign(Gtk.Align.START)
        self.popover.set_parent(self)

    # ------------------------------------------------------------------ building

    def _build_search_strip(self) -> Gtk.Widget:
        strip = Gtk.Box(spacing=6)
        strip.add_css_class("toolbar")
        blocks = Gtk.Box()
        blocks.add_css_class("linked")
        for block_id, title in (("favourites", "Favourites"), ("all", "All Emoji")):
            blocks.append(Gtk.ToggleButton(
                label=title, action_name="win.emoji-block",
                action_target=GLib.Variant("s", block_id)))
        strip.append(blocks)
        self.search_entry = Gtk.SearchEntry(
            placeholder_text="Search name, description or label", hexpand=True)
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_entry.connect("activate", lambda *_: self.copy_selected())
        self.search_entry.connect("stop-search", lambda e: e.set_text(""))
        # Typing anywhere on the page searches.
        self.search_entry.set_key_capture_widget(self)
        strip.append(self.search_entry)
        return strip

    def _build_action_bar(self) -> Gtk.Widget:
        bar = Gtk.ActionBar()
        self.favourite_button = icon_button("non-starred-symbolic", "Add to Favourites",
                                            "win.toggle-favourite")
        bar.pack_start(self.favourite_button)
        bar.pack_start(icon_button("document-edit-symbolic", "Set User Label…",
                                   "win.set-emoji-label"))
        move = Gtk.Box()
        move.add_css_class("linked")
        move.append(icon_button("go-up-symbolic", "Move Up", "win.move-emoji-up"))
        move.append(icon_button("go-down-symbolic", "Move Down", "win.move-emoji-down"))
        bar.pack_end(move)
        return bar

    def header_widgets(self) -> list[Gtk.Widget]:
        return [
            icon_button("edit-copy-symbolic", "Copy Emoji (Ctrl+C)", "win.copy"),
            icon_button("list-add-symbolic", "Add Custom Emoji…", "win.add-custom-emoji"),
        ]

    def _add_column(self, title: str, attr: str, expand: bool = False,
                    fixed_width: int = -1) -> None:
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._setup_cell, attr)
        factory.connect("bind", self._bind_cell, attr)
        column = Gtk.ColumnViewColumn(title=title, factory=factory, expand=expand,
                                      resizable=True)
        if fixed_width > 0:
            column.set_fixed_width(fixed_width)
        self.view.append_column(column)

    def _setup_cell(self, _factory, cell, attr: str) -> None:  # noqa: ANN001
        label = Gtk.Label(xalign=0.0, hexpand=True)
        if attr == "glyph":
            label.add_css_class("emoji-glyph")
        else:
            label.set_ellipsize(Pango.EllipsizeMode.END)
        if attr == "label":
            label.add_css_class("dim-label")
        cell.set_child(label)
        click = Gtk.GestureClick(button=Gdk.BUTTON_SECONDARY)
        click.connect("pressed", lambda _g, _n, x, y: self._popup_menu(label, cell, x, y))
        label.add_controller(click)
        press = Gtk.GestureLongPress(touch_only=True)
        press.connect("pressed", lambda _g, x, y: self._popup_menu(label, cell, x, y))
        label.add_controller(press)

    def _bind_cell(self, _factory, cell, attr: str) -> None:  # noqa: ANN001
        item = cell.get_item()
        label = cell.get_child()
        label.set_text(getattr(item, attr))
        if attr == "name":
            label.set_tooltip_text(item.emoji.id)

    # ------------------------------------------------------------------ data

    def _match(self, item: EmojiItem) -> bool:
        ws = self.window.workspace
        return ws is not None and emoji_matches(ws, item.emoji, self.query)

    def reload(self, keep_id: str | None = None) -> None:
        """Rebuild the rows from the workspace (block, skin tone, labels)."""
        ws = self.window.workspace
        keep = keep_id or self.selected_id()
        if ws is None:
            self.store.remove_all()
        else:
            favourites = set(ws.favourite_ids)
            items = [EmojiItem(e, e.display(self.skin_tone), emoji_display_name(e),
                               ws.favourite_label(e.id), e.id in favourites)
                     for e in emoji_block_items(ws, self.block)]
            self.store.splice(0, self.store.get_n_items(), items)
        if keep:
            self.select_id(keep)
        self._update_state()

    def _update_state(self) -> None:
        ws = self.window.workspace
        self.toolbar.set_reveal_top_bars(ws is not None)
        self.toolbar.set_reveal_bottom_bars(ws is not None)
        if ws is None:
            name = "no-workspace"
        elif self.store.get_n_items() == 0 and self.block == "favourites":
            name = "no-favourites"
        elif self.filtered.get_n_items() == 0:
            name = "no-results"
            self.no_results.set_description(
                "No emoji name, description or user label matches. Search All Emoji "
                "for more." if self.block == "favourites" else
                "No emoji name, description or user label matches.")
        else:
            name = "list"
        self.stack.set_visible_child_name(name)
        self._on_selection_changed()

    def set_block(self, block: str) -> None:
        if block != self.block:
            self.block = block
            self.reload()

    def set_skin_tone(self, tone: str) -> None:
        self.skin_tone = tone or "none"
        self.reload()

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        self.query = entry.get_text()
        self.filter.changed(Gtk.FilterChange.DIFFERENT)
        self._update_state()

    def focus_search(self) -> None:
        self.search_entry.grab_focus()

    # ------------------------------------------------------------------ selection

    def selected_item(self) -> EmojiItem | None:
        item = self.selection.get_selected_item()
        return item if isinstance(item, EmojiItem) else None

    def selected_id(self) -> str | None:
        item = self.selected_item()
        return item.emoji.id if item else None

    def select_id(self, emoji_id: str) -> None:
        for pos in range(self.filtered.get_n_items()):
            if self.filtered.get_item(pos).emoji.id == emoji_id:
                self.selection.set_selected(pos)
                self.view.scroll_to(pos, None, Gtk.ListScrollFlags.NONE, None)
                return

    def _on_selection_changed(self, *_args) -> None:
        item = self.selected_item()
        fav = bool(item and item.favourite)
        self.favourite_button.set_icon_name("starred-symbolic" if fav else "non-starred-symbolic")
        self.favourite_button.set_tooltip_text("Remove from Favourites" if fav
                                               else "Add to Favourites")
        self.window.update_actions()

    def can_move(self, delta: int) -> bool:
        ws = self.window.workspace
        item = self.selected_item()
        if ws is None or item is None or self.block != "favourites" or not item.favourite:
            return False
        i = ws.favourite_ids.index(item.emoji.id)
        return 0 <= i + delta < len(ws.favourite_ids)

    # ------------------------------------------------------------------ commands

    def copy_at(self, pos: int) -> None:
        item = self.filtered.get_item(pos)
        if item is not None:
            copy_text(self, item.glyph)
            self.window.toast(f"Copied {item.glyph}")

    def copy_selected(self) -> None:
        pos = self.selection.get_selected()
        if pos != Gtk.INVALID_LIST_POSITION:
            self.copy_at(pos)

    def toggle_favourite(self) -> None:
        ws = self.window.workspace
        item = self.selected_item()
        if ws is None or item is None:
            return
        eid = item.emoji.id
        if item.favourite:
            ws.remove_favourite(eid)
            self.window.toast(f"Removed {item.glyph} from Favourites")
        else:
            ws.add_favourite(eid)
            self.window.toast(f"Added {item.glyph} to Favourites")
        self.reload(keep_id=eid)

    def set_label(self) -> None:
        ws = self.window.workspace
        item = self.selected_item()
        if ws is None or item is None or not item.favourite:
            return
        eid = item.emoji.id

        def apply(text: str) -> None:
            ws.set_favourite_label(eid, text)
            self.reload(keep_id=eid)
        dialogs.prompt_text(
            self.window, "Set User Label",
            f"A label of your own for {item.glyph} {item.emoji.name}. Search finds emoji by "
            "their labels too. Leave it empty to remove the label.",
            "Set Label", apply, initial=ws.favourite_label(eid))

    def add_custom(self) -> None:
        ws = self.window.workspace
        if ws is None:
            return

        def apply(text: str) -> None:
            glyph = text.strip()
            if not glyph:
                return
            new_id = ws.add_custom_favourite(glyph)
            if new_id is None:
                self.window.toast(f"{glyph} is already a favourite")
                return
            if self.block != "favourites":
                self.window.activate_action("win.emoji-block", GLib.Variant("s", "favourites"))
            self.reload(keep_id=new_id)
            self.window.toast(f"Added {glyph} to Favourites")
        dialogs.prompt_text(
            self.window, "Add Custom Emoji",
            "Paste an emoji that is not in the list, such as one made of several parts "
            "(❤️‍\U0001fa79). Ctrl+. opens the emoji chooser.",
            "Add to Favourites", apply, width_chars=12)

    def move_selected(self, delta: int) -> None:
        ws = self.window.workspace
        item = self.selected_item()
        if ws is None or item is None or not self.can_move(delta):
            return
        if ws.move_favourite(item.emoji.id, delta):
            self.reload(keep_id=item.emoji.id)

    # ------------------------------------------------------------------ context menu

    def _popup_menu(self, widget: Gtk.Widget, cell, x: float, y: float) -> None:  # noqa: ANN001
        pos = cell.get_position()
        if pos == Gtk.INVALID_LIST_POSITION:
            return
        self.selection.set_selected(pos)
        item = self.selected_item()
        if item is None:
            return
        menu = Gio.Menu()
        main = Gio.Menu()
        main.append("Copy", "win.copy")
        main.append("Remove from Favourites" if item.favourite else "Add to Favourites",
                    "win.toggle-favourite")
        menu.append_section(None, main)
        if item.favourite:
            fav = Gio.Menu()
            fav.append("Set User Label…", "win.set-emoji-label")
            if self.block == "favourites":
                fav.append("Move Up", "win.move-emoji-up")
                fav.append("Move Down", "win.move-emoji-down")
            menu.append_section(None, fav)
        ok, point = widget.compute_point(self, Graphene.Point().init(x, y))
        if not ok:
            return
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = int(point.x), int(point.y), 1, 1
        self.popover.set_menu_model(menu)
        self.popover.set_pointing_to(rect)
        self.popover.popup()
