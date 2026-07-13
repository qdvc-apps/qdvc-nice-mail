"""GTK3 Note to Self tab.

A self-addressed note: the user types an address (persisted), a subject, and a
plaintext body, then clicks Send to generate a self-addressed .eml (From == To)
whose body carries a message-ref trailer. The message-ref is independent of the
Signature tab's.
"""
from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import GLib, GObject, Gtk, Pango  # noqa: E402

from ..naming import generate_message_ref  # noqa: E402
from ..note import build_note_eml, default_note_filename  # noqa: E402


class NoteToSelfTab(Gtk.Box):
    __gsignals__ = {
        "status": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, window) -> None:  # noqa: ANN001
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.window = window
        self.set_border_width(10)
        self.message_ref = generate_message_ref()

        grid = Gtk.Grid(column_spacing=8, row_spacing=8)
        self.pack_start(grid, False, False, 0)

        # From/To address (persisted).
        grid.attach(Gtk.Label(label="From / To:", xalign=0.0), 0, 0, 1, 1)
        self.address_entry = Gtk.Entry()
        self.address_entry.set_placeholder_text("your.email@example.com")
        self.address_entry.set_hexpand(True)
        self.address_entry.set_text(self.window.config.get("note_email", "") or "")
        self.address_entry.connect("changed", self._on_address_changed)
        grid.attach(self.address_entry, 1, 0, 1, 1)

        # Subject.
        grid.attach(Gtk.Label(label="Subject:", xalign=0.0), 0, 1, 1, 1)
        self.subject_entry = Gtk.Entry()
        self.subject_entry.set_hexpand(True)
        grid.attach(self.subject_entry, 1, 1, 1, 1)

        # Body.
        self.body_buffer = Gtk.TextBuffer()
        self.body_view = Gtk.TextView(buffer=self.body_buffer)
        self.body_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.body_view.set_left_margin(6)
        self.body_view.set_right_margin(6)
        self.body_view.set_top_margin(6)
        body_scroller = Gtk.ScrolledWindow()
        body_scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        body_scroller.set_shadow_type(Gtk.ShadowType.IN)
        body_scroller.add(self.body_view)
        self.pack_start(body_scroller, True, True, 0)

        # Callout notice above the status bar. GTK3 has no "success" message
        # type (only info/warning/question/error), so we use INFO and paint it
        # green via a CSS provider keyed on the theme's @success_color. Also a
        # 24x24 icon and partly-bold text.
        self.callout = Gtk.InfoBar()
        self.callout.set_message_type(Gtk.MessageType.INFO)
        self._apply_success_style(self.callout)
        callout_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        icon = Gtk.Image.new_from_icon_name("emblem-default", Gtk.IconSize.LARGE_TOOLBAR)
        icon.set_pixel_size(24)
        callout_box.pack_start(icon, False, False, 0)
        self.callout_label = Gtk.Label(xalign=0.0)
        self.callout_label.set_use_markup(True)
        callout_box.pack_start(self.callout_label, False, False, 0)
        self.callout.get_content_area().add(callout_box)
        self.pack_start(self.callout, False, False, 0)

        # Apply the shared signature preview font to all three fields.
        self.set_font(self.window.config.get("signature_font", "") or "")
        self._update_callout()

    # ---- styling ---------------------------------------------------------
    @staticmethod
    def _apply_success_style(info_bar: Gtk.InfoBar) -> None:
        """Tint the InfoBar green using the theme's success palette.

        GTK3 InfoBars only style .info/.warning/.question/.error, none of which
        is guaranteed green. We add a CSS class and a provider that colours it
        with the stylesheet-exported @success_color, falling back to a fixed
        green if the theme doesn't define it.
        """
        css = b"""
        infobar.qdvc-success > revealer > box {
            background-color: @success_color;
            background-image: none;
            color: #ffffff;
        }
        infobar.qdvc-success {
            background-color: @success_color;
        }
        """
        provider = Gtk.CssProvider()
        try:
            provider.load_from_data(css)
        except Exception:
            provider.load_from_data(
                b"infobar.qdvc-success, "
                b"infobar.qdvc-success > revealer > box "
                b"{ background-color: #2e7d32; color: #ffffff; }"
            )
        ctx = info_bar.get_style_context()
        ctx.add_class("qdvc-success")
        ctx.add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    # ---- font ------------------------------------------------------------
    def set_font(self, font_desc: str) -> None:
        """Match the Signature preview font (empty = default)."""
        desc = Pango.FontDescription(font_desc) if font_desc else None
        for widget in (self.address_entry, self.subject_entry, self.body_view):
            widget.override_font(desc)

    # ---- message ref -----------------------------------------------------
    def refresh_message_ref(self) -> None:
        self.message_ref = generate_message_ref()
        self._update_callout()
        self.emit("status", f"New message ref: {self.message_ref}")

    def _update_callout(self) -> None:
        ref = GLib.markup_escape_text(self.message_ref)
        self.callout_label.set_markup(
            f"This note to self will be assigned <b>Message ref. {ref}</b>"
        )

    # ---- persistence -----------------------------------------------------
    def _on_address_changed(self, entry: Gtk.Entry) -> None:
        self.window.config.set("note_email", entry.get_text().strip())

    # ---- reload (kept for parity with other tabs) ------------------------
    def reload(self) -> None:
        self.address_entry.set_text(self.window.config.get("note_email", "") or "")
        self._update_callout()

    # ---- send ------------------------------------------------------------
    def _body_text(self) -> str:
        start, end = self.body_buffer.get_bounds()
        return self.body_buffer.get_text(start, end, False)

    def send(self) -> None:
        """Generate the .eml and let the user choose where to save it."""
        address = self.address_entry.get_text().strip()
        subject = self.subject_entry.get_text().strip()
        eml = build_note_eml(
            address=address,
            subject=subject,
            text=self._body_text(),
            message_ref=self.message_ref,
        )
        dialog = Gtk.FileChooserDialog(
            title="Save Note as EML",
            transient_for=self.window,
            action=Gtk.FileChooserAction.SAVE,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK,
        )
        dialog.set_do_overwrite_confirmation(True)
        dialog.set_current_name(default_note_filename(self.message_ref))
        resp = dialog.run()
        path = dialog.get_filename()
        dialog.destroy()
        if resp != Gtk.ResponseType.OK or not path:
            return
        try:
            with open(path, "wb") as fh:
                fh.write(eml)
        except OSError as exc:
            self.emit("status", f"Could not save EML: {exc}")
            return
        # Clear the composed note and start a fresh message ref for the next one.
        self.subject_entry.set_text("")
        self.body_buffer.set_text("")
        self.message_ref = generate_message_ref()
        self._update_callout()
        self.emit("status", f"Saved note to {path}")
