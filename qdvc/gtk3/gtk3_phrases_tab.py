"""GTK3 Phrases tab (spec §8)."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GObject, Gtk  # noqa: E402


class PhrasesTab(Gtk.Box):
    __gsignals__ = {
        "status": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    COL_ID = 0
    COL_TEXT = 1

    def __init__(self, window) -> None:  # noqa: ANN001
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window = window
        self.query = ""

        self.store = Gtk.ListStore(str, str)
        self.view = Gtk.TreeView(model=self.store)
        self.view.get_selection().set_mode(Gtk.SelectionMode.SINGLE)

        renderer = Gtk.CellRendererText()
        col = Gtk.TreeViewColumn("Phrase", renderer, text=self.COL_TEXT)
        col.set_expand(True)
        col.set_resizable(True)
        self.view.append_column(col)

        self.view.connect("key-press-event", self._on_key_press)
        self.view.connect("row-activated", lambda *_: self.copy_selected())

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroller.add(self.view)
        self.pack_start(scroller, True, True, 0)

    # ---- search ----------------------------------------------------------
    def set_query(self, text: str) -> None:
        self.query = text or ""
        self.reload()

    # ---- data ------------------------------------------------------------
    def reload(self) -> None:
        self.store.clear()
        ws = self.window.workspace
        if ws is None:
            self.emit("status", "Open a workspace to see phrases.")
            return
        # Alphabetical (case-insensitive) by phrase text.
        phrases = sorted(ws.phrases, key=lambda p: p.text.lower())
        q = self.query.strip().lower()
        if q:
            phrases = [p for p in phrases if q in p.text.lower()]
        for p in phrases:
            self.store.append([p.id, p.text])
        if q:
            self.emit("status", f"{len(phrases)} phrases match.")
        else:
            self.emit("status", f"{len(ws.phrases)} phrases.")

    def _selected(self):
        model, tree_iter = self.view.get_selection().get_selected()
        if tree_iter is None:
            return None, None
        return model.get_value(tree_iter, self.COL_ID), model.get_value(tree_iter, self.COL_TEXT)

    def copy_selected(self) -> None:
        _pid, text = self._selected()
        if text is None:
            return
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(text, -1)
        clipboard.store()
        self.emit("status", "Phrase copied to clipboard.")

    def _on_key_press(self, _widget, event) -> bool:  # noqa: ANN001
        if event.state & Gdk.ModifierType.CONTROL_MASK and event.keyval in (Gdk.KEY_c, Gdk.KEY_C):
            self.copy_selected()
            return True
        return False

    # ---- CRUD (invoked from toolbar) ------------------------------------
    def _prompt_text(self, title: str, initial: str = "") -> str | None:
        dialog = Gtk.Dialog(title=title, transient_for=self.window, modal=True)
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK,
        )
        box = dialog.get_content_area()
        box.set_spacing(6)
        box.set_border_width(10)
        entry = Gtk.Entry()
        entry.set_text(initial)
        entry.set_activates_default(True)
        entry.set_width_chars(48)
        dialog.set_default_response(Gtk.ResponseType.OK)
        box.add(entry)
        dialog.show_all()
        resp = dialog.run()
        text = entry.get_text().strip()
        dialog.destroy()
        if resp == Gtk.ResponseType.OK and text:
            return text
        return None

    def add_phrase(self) -> None:
        ws = self.window.workspace
        if ws is None:
            return
        text = self._prompt_text("Add Phrase")
        if text:
            ws.add_phrase(text)
            self.reload()
            self.emit("status", "Phrase added.")

    def edit_phrase(self) -> None:
        ws = self.window.workspace
        pid, current = self._selected()
        if ws is None or pid is None:
            return
        text = self._prompt_text("Edit Phrase", current or "")
        if text:
            ws.edit_phrase(pid, text)
            self.reload()
            self.emit("status", "Phrase updated.")

    def delete_phrase(self) -> None:
        ws = self.window.workspace
        pid, _ = self._selected()
        if ws is None or pid is None:
            return
        confirm = Gtk.MessageDialog(
            transient_for=self.window, modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="Delete this phrase?",
        )
        resp = confirm.run()
        confirm.destroy()
        if resp == Gtk.ResponseType.OK:
            ws.delete_phrase(pid)
            self.reload()
            self.emit("status", "Phrase deleted.")
