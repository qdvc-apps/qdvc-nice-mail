"""GTK3 Signature tab (spec §8)."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GObject, Gtk, Pango  # noqa: E402

from ..mailsig import assemble_signature  # noqa: E402
from ..naming import generate_message_ref  # noqa: E402


class SignatureTab(Gtk.Box):
    __gsignals__ = {
        "status": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, window) -> None:  # noqa: ANN001
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window = window
        self.profile_name: str | None = window.config.get("profile")
        self.include_disclaimer = bool(window.config.get("include_disclaimer", True))
        self.ref_only = bool(window.config.get("ref_only", False))
        self.message_ref = generate_message_ref()

        self.buffer = Gtk.TextBuffer()
        self.textview = Gtk.TextView(buffer=self.buffer)
        self.textview.set_editable(False)
        self.textview.set_cursor_visible(False)
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.textview.set_monospace(True)
        self.textview.set_left_margin(10)
        self.textview.set_top_margin(10)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroller.add(self.textview)
        self.pack_start(scroller, True, True, 0)

        # Apply any persisted custom preview font.
        self.set_font(self.window.config.get("signature_font", "") or "")

    # ---- toolbar-driven state -------------------------------------------
    def set_profile(self, name: str | None) -> None:
        self.profile_name = name
        self.reload()

    def set_include_disclaimer(self, value: bool) -> None:
        self.include_disclaimer = value
        self.reload()

    def set_ref_only(self, value: bool) -> None:
        self.ref_only = value
        self.reload()

    def set_font(self, font_desc: str) -> None:
        """Override the preview font. Empty string restores the default."""
        if font_desc:
            self.textview.override_font(Pango.FontDescription(font_desc))
            self.textview.set_monospace(False)
        else:
            self.textview.override_font(None)
            self.textview.set_monospace(True)

    def refresh_message_ref(self) -> None:
        self.message_ref = generate_message_ref()
        self.reload()
        self.emit("status", f"New message ref: {self.message_ref}")

    # ---- render ----------------------------------------------------------
    def reload(self) -> None:
        ws = self.window.workspace
        if ws is None:
            self.buffer.set_text("Open a workspace to build a signature.")
            self.emit("status", "No workspace open.")
            return
        profile = ws.get_profile(self.profile_name)
        text = assemble_signature(
            signoff=ws.signoff,
            profile=profile,
            disclaimer=ws.disclaimer,
            include_disclaimer=self.include_disclaimer,
            message_ref=self.message_ref,
            ref_only=self.ref_only,
        )
        self.buffer.set_text(text)
        self.emit("status", "Signature ready (ref only)." if self.ref_only else "Signature ready.")

    def current_text(self) -> str:
        start, end = self.buffer.get_bounds()
        return self.buffer.get_text(start, end, False)

    def copy_signature(self) -> None:
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(self.current_text(), -1)
        clipboard.store()
        self.emit("status", "Signature copied to clipboard.")
