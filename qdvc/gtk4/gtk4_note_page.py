"""The Note to Self page: write a note and save it as a self-addressed .eml.

    Adw.Clamp > Box
      Adw.PreferencesGroup: From / To (persisted) · Subject
      "Message" + a card holding the body Gtk.TextView
      a green callout: "This note to self will be assigned Message ref. …" [⟳]

Send (header bar) builds the message with ``note.build_note_eml`` (pure,
shared with GTK 3) and asks where to save it, suggesting
``note.default_note_filename``. After saving, the subject and body are
cleared and a new message reference is drawn. Works without a workspace.
"""
from __future__ import annotations

import os

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from ..naming import generate_message_ref  # noqa: E402
from ..note import build_note_eml, default_note_filename  # noqa: E402
from . import gtk4_dialogs as dialogs  # noqa: E402
from .gtk4_widgets import CUSTOM_FONT_CLASS, icon_button, set_class  # noqa: E402


class NotePage(Gtk.ScrolledWindow):
    def __init__(self, window) -> None:  # noqa: ANN001
        super().__init__(hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.window = window
        self.message_ref = generate_message_ref()
        self._save_folder: str | None = None

        fields = Adw.PreferencesGroup()
        self.address_row = Adw.EntryRow(title="From / To",
                                        input_purpose=Gtk.InputPurpose.EMAIL)
        self.address_row.set_text(window.config.get("note_email", "") or "")
        self.address_row.connect("changed", self._on_address_changed)
        fields.add(self.address_row)
        self.subject_row = Adw.EntryRow(title="Subject")
        fields.add(self.subject_row)

        heading = Gtk.Label(label="Message", xalign=0.0)
        heading.add_css_class("heading")
        self.body_buffer = Gtk.TextBuffer()
        self.body_view = Gtk.TextView(buffer=self.body_buffer, wrap_mode=Gtk.WrapMode.WORD_CHAR,
                                      top_margin=12, bottom_margin=12, left_margin=14,
                                      right_margin=14, accepts_tab=False)
        self.body_view.add_css_class("note-body")
        self.body_view.update_property([Gtk.AccessibleProperty.LABEL], ["Message"])
        body_scroller = Gtk.ScrolledWindow(child=self.body_view, vexpand=True,
                                           min_content_height=180,
                                           hscrollbar_policy=Gtk.PolicyType.NEVER)
        card = Gtk.Frame(child=body_scroller, vexpand=True)
        card.add_css_class("view")
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, vexpand=True)
        body.append(heading)
        body.append(card)

        callout = Gtk.Box(spacing=12)
        callout.add_css_class("callout")
        icon = Gtk.Image(icon_name="emblem-ok-symbolic", pixel_size=24,
                         valign=Gtk.Align.CENTER)
        icon.add_css_class("callout-icon")
        callout.append(icon)
        self.callout_label = Gtk.Label(xalign=0.0, wrap=True, hexpand=True, use_markup=True)
        callout.append(self.callout_label)
        callout.append(icon_button("view-refresh-symbolic", "New Reference (F5)",
                                   "win.new-ref", flat=True))

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18, margin_top=24,
                      margin_bottom=24, margin_start=12, margin_end=12, vexpand=True)
        box.append(fields)
        box.append(body)
        box.append(callout)
        self.set_child(Adw.Clamp(maximum_size=760, child=box, vexpand=True))
        self._update_callout()

    def header_widgets(self) -> list[Gtk.Widget]:
        send = Gtk.Button(child=Adw.ButtonContent(icon_name="document-save-symbolic",
                                                  label="Send…"),
                          action_name="win.send-note",
                          tooltip_text="Save the Note as an .eml File to Send to Yourself")
        send.add_css_class("suggested-action")
        return [send]

    # ------------------------------------------------------------------ state

    def reload(self) -> None:
        """Re-read the persisted address (kept for parity with the other pages)."""
        saved = self.window.config.get("note_email", "") or ""
        if self.address_row.get_text() != saved:
            self.address_row.set_text(saved)
        self._update_callout()

    def _on_address_changed(self, row: Adw.EntryRow) -> None:
        self.window.config.set("note_email", row.get_text().strip())

    def set_custom_font(self, custom: bool) -> None:
        for widget in (self.address_row, self.subject_row, self.body_view):
            set_class(widget, CUSTOM_FONT_CLASS, custom)

    def refresh_message_ref(self) -> None:
        self.message_ref = generate_message_ref()
        self._update_callout()
        self.window.toast(f"New message reference {self.message_ref}")

    def _update_callout(self) -> None:
        ref = GLib.markup_escape_text(self.message_ref)
        self.callout_label.set_markup(
            f"This note to self will be assigned <b>Message ref. {ref}</b>")

    def _body_text(self) -> str:
        start, end = self.body_buffer.get_bounds()
        return self.body_buffer.get_text(start, end, False)

    # ------------------------------------------------------------------ send

    def send(self) -> None:
        """Build the .eml now (date = now), then ask where to save it."""
        eml = build_note_eml(address=self.address_row.get_text().strip(),
                             subject=self.subject_row.get_text().strip(),
                             text=self._body_text(), message_ref=self.message_ref)
        dialog = Gtk.FileDialog(title="Save Note as EML", modal=True, accept_label="Save",
                                initial_name=default_note_filename(self.message_ref))
        if self._save_folder and os.path.isdir(self._save_folder):
            dialog.set_initial_folder(Gio.File.new_for_path(self._save_folder))

        def done(d: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
            try:
                gfile = d.save_finish(result)
            except GLib.Error:
                return  # cancelled
            path = gfile.get_path() if gfile is not None else None
            if not path:
                return
            try:
                with open(path, "wb") as fh:
                    fh.write(eml)
            except OSError as exc:
                dialogs.alert(self.window, "Could Not Save the Note", str(exc))
                return
            self._save_folder = os.path.dirname(path)
            # Clear the note and draw a fresh reference for the next one.
            self.subject_row.set_text("")
            self.body_buffer.set_text("")
            self.message_ref = generate_message_ref()
            self._update_callout()
            self.window.toast(f"Saved {os.path.basename(path)}")
        dialog.save(self.window, None, done)
