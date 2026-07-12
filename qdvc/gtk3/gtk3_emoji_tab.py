"""GTK3 Emoji tab (spec §8)."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GObject, Gtk  # noqa: E402

from ..ui_prefs import EMOJI_BLOCKS, SKIN_TONE_LABELS  # noqa: E402


class EmojiTab(Gtk.Box):
    """Table of emoji. Columns: symbol, name (id shown as tooltip)."""

    __gsignals__ = {
        "status": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    COL_ID = 0
    COL_SYMBOL = 1
    COL_NAME = 2
    COL_LABEL = 3

    def __init__(self, window) -> None:  # noqa: ANN001
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window = window
        self.block = "favourites"
        self.skin_tone = "none"
        self.query = ""

        # id, symbol(display), name, user label
        self.store = Gtk.ListStore(str, str, str, str)
        self.view = Gtk.TreeView(model=self.store)
        self.view.set_headers_visible(True)
        self.view.set_rubber_banding(False)
        sel = self.view.get_selection()
        sel.set_mode(Gtk.SelectionMode.SINGLE)

        symbol_renderer = Gtk.CellRendererText()
        symbol_renderer.set_property("scale", 1.6)
        col_symbol = Gtk.TreeViewColumn("Emoji", symbol_renderer, text=self.COL_SYMBOL)
        col_symbol.set_min_width(70)
        self.view.append_column(col_symbol)

        name_renderer = Gtk.CellRendererText()
        col_name = Gtk.TreeViewColumn("Name", name_renderer, text=self.COL_NAME)
        col_name.set_expand(True)
        self.view.append_column(col_name)

        label_renderer = Gtk.CellRendererText()
        col_label = Gtk.TreeViewColumn("User label", label_renderer, text=self.COL_LABEL)
        col_label.set_min_width(140)
        self.view.append_column(col_label)

        # Ctrl+C to copy the selected emoji.
        self.view.connect("key-press-event", self._on_key_press)
        # Right-click context menu -> favourites.
        self.view.connect("button-press-event", self._on_button_press)
        # Double-click also copies (convenience).
        self.view.connect("row-activated", lambda *_: self.copy_selected())

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroller.add(self.view)
        self.pack_start(scroller, True, True, 0)

    # ---- toolbar-provided state ------------------------------------------
    def set_block(self, block_id: str) -> None:
        self.block = block_id
        self.reload()

    def set_skin_tone(self, tone_id: str) -> None:
        self.skin_tone = tone_id
        self.reload()

    def set_query(self, text: str) -> None:
        self.query = text or ""
        self.reload()

    # ---- data population -------------------------------------------------
    def reload(self) -> None:
        self.store.clear()
        ws = self.window.workspace
        if ws is None:
            self.emit("status", "Open a workspace to see emoji.")
            return

        if self.block == "favourites":
            emoji = ws.favourite_emoji()
        else:
            emoji = ws.catalogue.all()

        q = self.query.strip().lower()
        if q:
            emoji = [
                e for e in emoji
                if q in e.name.lower()
                or q in e.id
                or q in ws.favourite_label(e.id).lower()
            ]

        for e in emoji:
            self.store.append(
                [e.id, e.display(self.skin_tone), e.name, ws.favourite_label(e.id)]
            )

        self.emit("status", f"{len(emoji)} emoji shown ({self.block}).")

    # ---- selection helpers ----------------------------------------------
    def _selected_iter(self):
        model, tree_iter = self.view.get_selection().get_selected()
        return model, tree_iter

    def selected_emoji_id(self) -> str | None:
        model, tree_iter = self._selected_iter()
        if tree_iter is None:
            return None
        return model.get_value(tree_iter, self.COL_ID)

    def copy_selected(self) -> None:
        model, tree_iter = self._selected_iter()
        if tree_iter is None:
            return
        symbol = model.get_value(tree_iter, self.COL_SYMBOL)
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(symbol, -1)
        clipboard.store()
        self.emit("status", f"Copied {symbol} to clipboard.")

    # ---- events ----------------------------------------------------------
    def _on_key_press(self, _widget, event) -> bool:  # noqa: ANN001
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        if ctrl and event.keyval in (Gdk.KEY_c, Gdk.KEY_C):
            self.copy_selected()
            return True
        return False

    def _on_button_press(self, _widget, event) -> bool:  # noqa: ANN001
        if event.button != 3:  # right-click only
            return False
        path_info = self.view.get_path_at_pos(int(event.x), int(event.y))
        if path_info is None:
            return False
        path = path_info[0]
        self.view.get_selection().select_path(path)
        self._show_context_menu(event)
        return True

    def _show_context_menu(self, event) -> None:  # noqa: ANN001
        ws = self.window.workspace
        emoji_id = self.selected_emoji_id()
        if ws is None or emoji_id is None:
            return
        menu = Gtk.Menu()
        is_fav = emoji_id in ws.favourite_ids
        if is_fav:
            item = Gtk.MenuItem(label="Remove from Favourites")
            item.connect("activate", lambda *_: self._remove_favourite(emoji_id))
        else:
            item = Gtk.MenuItem(label="Add to Favourites")
            item.connect("activate", lambda *_: self._add_favourite(emoji_id))
        menu.append(item)

        if is_fav:
            label_item = Gtk.MenuItem(label="Set User Label…")
            label_item.connect("activate", lambda *_: self._set_label(emoji_id))
            menu.append(label_item)

            menu.append(Gtk.SeparatorMenuItem())
            up_item = Gtk.MenuItem(label="Move Up")
            up_item.connect("activate", lambda *_: self.move_selected(-1))
            menu.append(up_item)
            down_item = Gtk.MenuItem(label="Move Down")
            down_item.connect("activate", lambda *_: self.move_selected(1))
            menu.append(down_item)

        menu.append(Gtk.SeparatorMenuItem())
        copy_item = Gtk.MenuItem(label="Copy")
        copy_item.connect("activate", lambda *_: self.copy_selected())
        menu.append(copy_item)

        menu.show_all()
        menu.popup_at_pointer(event)

    def _add_favourite(self, emoji_id: str) -> None:
        ws = self.window.workspace
        if ws and ws.add_favourite(emoji_id):
            self.emit("status", f"Added {emoji_id} to favourites.")
            if self.block == "favourites":
                self.reload()

    def _remove_favourite(self, emoji_id: str) -> None:
        ws = self.window.workspace
        if ws and ws.remove_favourite(emoji_id):
            self.emit("status", f"Removed {emoji_id} from favourites.")
            if self.block == "favourites":
                self.reload()

    def _set_label(self, emoji_id: str) -> None:
        ws = self.window.workspace
        if ws is None:
            return
        current = ws.favourite_label(emoji_id)
        dialog = Gtk.Dialog(title="Set User Label", transient_for=self.window, modal=True)
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK,
        )
        box = dialog.get_content_area()
        box.set_spacing(6)
        box.set_border_width(10)
        entry = Gtk.Entry()
        entry.set_text(current)
        entry.set_activates_default(True)
        entry.set_width_chars(32)
        dialog.set_default_response(Gtk.ResponseType.OK)
        box.add(entry)
        dialog.show_all()
        resp = dialog.run()
        text = entry.get_text()
        dialog.destroy()
        if resp == Gtk.ResponseType.OK:
            ws.set_favourite_label(emoji_id, text)
            self.reload()
            self._reselect(emoji_id)
            self.emit("status", f"Label updated for {emoji_id}.")

    def move_selected(self, delta: int) -> None:
        """Move the selected favourite up (-1) or down (+1)."""
        ws = self.window.workspace
        emoji_id = self.selected_emoji_id()
        if ws is None or emoji_id is None or self.block != "favourites":
            return
        if ws.move_favourite(emoji_id, delta):
            self.reload()
            self._reselect(emoji_id)

    def _reselect(self, emoji_id: str) -> None:
        tree_iter = self.store.get_iter_first()
        while tree_iter is not None:
            if self.store.get_value(tree_iter, self.COL_ID) == emoji_id:
                self.view.get_selection().select_iter(tree_iter)
                self.view.scroll_to_cell(self.store.get_path(tree_iter), None, False, 0, 0)
                break
            tree_iter = self.store.iter_next(tree_iter)
