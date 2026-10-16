"""The Phrases page: your reusable phrases, alphabetical, with a search box.

    Gtk.Box
      Adw.ToolbarView
        top:     [ search entry ]
        content: Gtk.Stack ── "list": ScrolledWindow(Gtk.ListView)
                            ├ "no-workspace" / "no-phrases" / "no-results"
        bottom:  Gtk.ActionBar  [✎ Edit…] [🗑 Delete…]
      Gtk.PopoverMenu (right-click / long-press menu)

Rows follow ``ui_prefs.phrase_listing`` (alphabetical) and are filtered with
``ui_prefs.phrase_matches``. Enter or a double-click copies a phrase.
"""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Graphene", "1.0")
from gi.repository import Adw, Gdk, Gio, GObject, Graphene, Gtk, Pango  # noqa: E402

from ..ui_prefs import phrase_listing, phrase_matches  # noqa: E402
from . import gtk4_dialogs as dialogs  # noqa: E402
from .gtk4_widgets import copy_text, icon_button, no_workspace_page, status_page  # noqa: E402


class PhraseItem(GObject.Object):
    __gtype_name__ = "QdvcNiceMailPhraseItem"

    def __init__(self, phrase) -> None:  # noqa: ANN001
        super().__init__()
        self.phrase = phrase


class PhrasesPage(Gtk.Box):
    def __init__(self, window) -> None:  # noqa: ANN001
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.window = window
        self.query = ""

        self.store = Gio.ListStore(item_type=PhraseItem)
        self.filter = Gtk.CustomFilter.new(
            lambda item, _data: phrase_matches(item.phrase, self.query), None)
        self.filtered = Gtk.FilterListModel(model=self.store, filter=self.filter)
        self.selection = Gtk.SingleSelection(model=self.filtered, autoselect=True)
        self.selection.connect("notify::selected", lambda *_: self.window.update_actions())

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._setup_row)
        factory.connect("bind", self._bind_row)
        self.view = Gtk.ListView(model=self.selection, factory=factory)
        self.view.connect("activate", lambda _v, pos: self.copy_at(pos))
        scroller = Gtk.ScrolledWindow(child=self.view, vexpand=True,
                                      hscrollbar_policy=Gtk.PolicyType.NEVER)

        self.stack = Gtk.Stack()
        self.stack.add_named(scroller, "list")
        self.stack.add_named(no_workspace_page("view-list-bullet-symbolic", "your phrases"),
                             "no-workspace")
        self.stack.add_named(status_page(
            "view-list-bullet-symbolic", "No Phrases Yet",
            "Keep the sentences you type again and again here, ready to copy into an email.",
            "New Phrase…", "win.new-phrase"), "no-phrases")
        self.stack.add_named(status_page("edit-find-symbolic", "No Results",
                                         "No phrase contains the search text."), "no-results")

        self.toolbar = Adw.ToolbarView(top_bar_style=Adw.ToolbarStyle.RAISED,
                                       bottom_bar_style=Adw.ToolbarStyle.RAISED,
                                       vexpand=True)
        self.toolbar.add_top_bar(self._build_search_strip())
        self.toolbar.set_content(self.stack)
        self.toolbar.add_bottom_bar(self._build_action_bar())
        self.append(self.toolbar)

        self.popover = Gtk.PopoverMenu.new_from_model(None)
        self.popover.set_has_arrow(False)
        self.popover.set_halign(Gtk.Align.START)
        self.popover.set_parent(self)

    # ------------------------------------------------------------------ building

    def _build_search_strip(self) -> Gtk.Widget:
        strip = Gtk.Box()
        strip.add_css_class("toolbar")
        self.search_entry = Gtk.SearchEntry(placeholder_text="Search phrases", hexpand=True)
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_entry.connect("activate", lambda *_: self.copy_selected())
        self.search_entry.connect("stop-search", lambda e: e.set_text(""))
        self.search_entry.set_key_capture_widget(self)
        strip.append(self.search_entry)
        return strip

    def _build_action_bar(self) -> Gtk.Widget:
        bar = Gtk.ActionBar()
        bar.pack_start(icon_button("document-edit-symbolic", "Edit Phrase…",
                                   "win.edit-phrase"))
        bar.pack_start(icon_button("user-trash-symbolic", "Delete Phrase…",
                                   "win.delete-phrase"))
        return bar

    def header_widgets(self) -> list[Gtk.Widget]:
        return [
            icon_button("edit-copy-symbolic", "Copy Phrase (Ctrl+C)", "win.copy"),
            icon_button("list-add-symbolic", "New Phrase…", "win.new-phrase"),
        ]

    def _setup_row(self, _factory, list_item) -> None:  # noqa: ANN001
        label = Gtk.Label(xalign=0.0, wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR,
                          hexpand=True)
        label.add_css_class("phrase-row")
        list_item.set_child(label)
        click = Gtk.GestureClick(button=Gdk.BUTTON_SECONDARY)
        click.connect("pressed", lambda _g, _n, x, y: self._popup_menu(label, list_item, x, y))
        label.add_controller(click)
        press = Gtk.GestureLongPress(touch_only=True)
        press.connect("pressed", lambda _g, x, y: self._popup_menu(label, list_item, x, y))
        label.add_controller(press)

    def _bind_row(self, _factory, list_item) -> None:  # noqa: ANN001
        list_item.get_child().set_text(list_item.get_item().phrase.text)

    # ------------------------------------------------------------------ data

    def reload(self, keep_id: str | None = None) -> None:
        ws = self.window.workspace
        keep = keep_id or self.selected_id()
        if ws is None:
            self.store.remove_all()
        else:
            items = [PhraseItem(p) for p in phrase_listing(ws)]
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
        elif self.store.get_n_items() == 0:
            name = "no-phrases"
        elif self.filtered.get_n_items() == 0:
            name = "no-results"
        else:
            name = "list"
        self.stack.set_visible_child_name(name)
        self.window.update_actions()

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        self.query = entry.get_text()
        self.filter.changed(Gtk.FilterChange.DIFFERENT)
        self._update_state()

    def focus_search(self) -> None:
        self.search_entry.grab_focus()

    # ------------------------------------------------------------------ selection

    def selected_phrase(self):  # noqa: ANN201
        item = self.selection.get_selected_item()
        return item.phrase if isinstance(item, PhraseItem) else None

    def selected_id(self) -> str | None:
        phrase = self.selected_phrase()
        return phrase.id if phrase else None

    def select_id(self, phrase_id: str) -> None:
        for pos in range(self.filtered.get_n_items()):
            if self.filtered.get_item(pos).phrase.id == phrase_id:
                self.selection.set_selected(pos)
                self.view.scroll_to(pos, Gtk.ListScrollFlags.NONE, None)
                return

    # ------------------------------------------------------------------ commands

    def copy_at(self, pos: int) -> None:
        item = self.filtered.get_item(pos)
        if item is not None:
            copy_text(self, item.phrase.text)
            self.window.toast("Phrase copied")

    def copy_selected(self) -> None:
        pos = self.selection.get_selected()
        if pos != Gtk.INVALID_LIST_POSITION:
            self.copy_at(pos)

    def add_phrase(self) -> None:
        ws = self.window.workspace
        if ws is None:
            return

        def apply(text: str) -> None:
            if text.strip():
                phrase = ws.add_phrase(text)
                self.search_entry.set_text("")
                self.reload(keep_id=phrase.id)
                self.window.toast("Phrase added")
        dialogs.prompt_text(self.window, "New Phrase",
                            "A sentence you use often, ready to copy into an email.",
                            "Add", apply, width_chars=48)

    def edit_phrase(self) -> None:
        ws = self.window.workspace
        phrase = self.selected_phrase()
        if ws is None or phrase is None:
            return

        def apply(text: str) -> None:
            if text.strip():
                ws.edit_phrase(phrase.id, text)
                self.reload(keep_id=phrase.id)
                self.window.toast("Phrase updated")
        dialogs.prompt_text(self.window, "Edit Phrase", "", "Save", apply,
                            initial=phrase.text, width_chars=48)

    def delete_phrase(self) -> None:
        ws = self.window.workspace
        phrase = self.selected_phrase()
        if ws is None or phrase is None:
            return
        preview = phrase.text if len(phrase.text) <= 80 else phrase.text[:77] + "…"

        def apply() -> None:
            ws.delete_phrase(phrase.id)
            self.reload()
            self.window.toast("Phrase deleted")
        dialogs.confirm(self.window, "Delete Phrase?",
                        f"“{preview}” will be removed from phrases.csv.",
                        "Delete", apply, destructive=True)

    # ------------------------------------------------------------------ context menu

    def _popup_menu(self, widget: Gtk.Widget, list_item, x: float, y: float) -> None:  # noqa: ANN001
        pos = list_item.get_position()
        if pos == Gtk.INVALID_LIST_POSITION:
            return
        self.selection.set_selected(pos)
        menu = Gio.Menu()
        first = Gio.Menu()
        first.append("Copy", "win.copy")
        menu.append_section(None, first)
        second = Gio.Menu()
        second.append("Edit…", "win.edit-phrase")
        second.append("Delete…", "win.delete-phrase")
        menu.append_section(None, second)
        ok, point = widget.compute_point(self, Graphene.Point().init(x, y))
        if not ok:
            return
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = int(point.x), int(point.y), 1, 1
        self.popover.set_menu_model(menu)
        self.popover.set_pointing_to(rect)
        self.popover.popup()
