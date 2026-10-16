"""Dialogs. Everything is asynchronous (spec §9: no dialog.run()): each one
calls back with the user's answer."""
from __future__ import annotations

from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402


def alert(parent: Gtk.Widget, heading: str, body: str) -> Adw.AlertDialog:
    dialog = Adw.AlertDialog(heading=heading, body=body)
    dialog.add_response("ok", "OK")
    dialog.set_default_response("ok")
    dialog.set_close_response("ok")
    dialog.present(parent)
    return dialog


def confirm(parent: Gtk.Widget, heading: str, body: str, ok_label: str,
            on_ok: Callable[[], None], destructive: bool = False) -> Adw.AlertDialog:
    dialog = Adw.AlertDialog(heading=heading, body=body)
    dialog.add_response("cancel", "Cancel")
    dialog.add_response("ok", ok_label)
    dialog.set_response_appearance(
        "ok", Adw.ResponseAppearance.DESTRUCTIVE if destructive
        else Adw.ResponseAppearance.SUGGESTED)
    # A destructive choice is never the default (Enter cancels).
    dialog.set_default_response("cancel" if destructive else "ok")
    dialog.set_close_response("cancel")

    def done(_dialog, response: str) -> None:
        if response == "ok":
            on_ok()
    dialog.connect("response", done)
    dialog.present(parent)
    return dialog


def prompt_text(parent: Gtk.Widget, heading: str, body: str, ok_label: str,
                on_ok: Callable[[str], None], initial: str = "", placeholder: str = "",
                width_chars: int = 32) -> Adw.AlertDialog:
    """An alert with a one-line entry. Enter in the entry answers ``ok``
    (the default response button is the dialog's default widget).

    The ``ok`` response stays enabled even for empty text, so Enter always
    has a sensitive default to activate; ``on_ok`` decides what blank means.
    """
    dialog = Adw.AlertDialog(heading=heading, body=body)
    entry = Gtk.Entry(text=initial, placeholder_text=placeholder, activates_default=True,
                      width_chars=width_chars)
    dialog.set_extra_child(entry)
    dialog.add_response("cancel", "Cancel")
    dialog.add_response("ok", ok_label)
    dialog.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
    dialog.set_default_response("ok")
    dialog.set_close_response("cancel")

    def done(_dialog, response: str) -> None:
        if response == "ok":
            on_ok(entry.get_text())
    dialog.connect("response", done)
    dialog.present(parent)
    entry.grab_focus()
    return dialog
