"""The Signature page: choose how the signature is assembled and copy it.

    Gtk.Stack ── "no-workspace": Adw.StatusPage
              └ "content": ScrolledWindow > Adw.Clamp > Box
                    Adw.PreferencesGroup: Profile · Disclaimer · Reference Only ·
                                          Message Reference [⟳]
                    Adw.PreferencesGroup "Preview" [Copy]: the signature text

The text comes from ``mailsig.assemble_signature`` (pure, shared with GTK 3);
the Profile, Disclaimer and Reference Only choices persist in the config
(keys ``profile``, ``include_disclaimer``, ``ref_only``), as in GTK 3.
"""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ..mailsig import assemble_signature  # noqa: E402
from ..naming import generate_message_ref  # noqa: E402
from .gtk4_widgets import (CUSTOM_FONT_CLASS, copy_text, icon_button,  # noqa: E402
                           no_workspace_page, set_class)


class SignaturePage(Gtk.Stack):
    def __init__(self, window) -> None:  # noqa: ANN001
        super().__init__()
        self.window = window
        config = window.config
        self.profile_names: list[str] = []
        self.message_ref = generate_message_ref()
        self._updating = False

        options = Adw.PreferencesGroup()
        self.profile_row = Adw.ComboRow(title="Profile", model=Gtk.StringList.new([]))
        self.profile_row.connect("notify::selected", self._on_profile_changed)
        options.add(self.profile_row)
        self.disclaimer_row = Adw.SwitchRow(
            title="Disclaimer", subtitle="Add the text of mailsigs/disclaimer.txt",
            active=bool(config.get("include_disclaimer", True)))
        self.disclaimer_row.connect("notify::active", self._on_disclaimer_changed)
        options.add(self.disclaimer_row)
        self.ref_only_row = Adw.SwitchRow(
            title="Reference Only", subtitle="Only the m-dash and the message reference",
            active=bool(config.get("ref_only", False)))
        self.ref_only_row.connect("notify::active", self._on_ref_only_changed)
        options.add(self.ref_only_row)
        self.ref_row = Adw.ActionRow(title="Message Reference")
        self.ref_row.add_css_class("property")
        self.ref_row.add_suffix(icon_button("view-refresh-symbolic", "New Reference (F5)",
                                            "win.new-ref", flat=True))
        options.add(self.ref_row)

        preview = Adw.PreferencesGroup(title="Preview")
        copy = Gtk.Button(label="Copy", action_name="win.copy", valign=Gtk.Align.CENTER,
                          tooltip_text="Copy the Signature (Ctrl+C)")
        copy.add_css_class("flat")
        preview.set_header_suffix(copy)
        self.buffer = Gtk.TextBuffer()
        self.textview = Gtk.TextView(buffer=self.buffer, editable=False, cursor_visible=False,
                                     monospace=True, wrap_mode=Gtk.WrapMode.WORD_CHAR,
                                     top_margin=12, bottom_margin=12, left_margin=14,
                                     right_margin=14)
        self.textview.add_css_class("signature-preview")
        self.textview.update_property([Gtk.AccessibleProperty.LABEL], ["Signature preview"])
        card = Gtk.Frame(child=self.textview)
        card.add_css_class("view")
        preview.add(card)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24, margin_top=24,
                      margin_bottom=24, margin_start=12, margin_end=12)
        box.append(options)
        box.append(preview)
        clamp = Adw.Clamp(maximum_size=760, child=box)
        self.add_named(Gtk.ScrolledWindow(child=clamp, hscrollbar_policy=Gtk.PolicyType.NEVER),
                       "content")
        self.add_named(no_workspace_page("x-office-address-book-symbolic", "your signature"),
                       "no-workspace")
        self._sync_ref_only()

    def header_widgets(self) -> list[Gtk.Widget]:
        return [icon_button("edit-copy-symbolic", "Copy the Signature (Ctrl+C)", "win.copy")]

    # ------------------------------------------------------------------ state

    def reload(self) -> None:
        """Re-read the profiles (after opening or refreshing the workspace)."""
        ws = self.window.workspace
        self.set_visible_child_name("content" if ws else "no-workspace")
        if ws is None:
            return
        names = [p.name for p in ws.profiles]
        self._updating = True
        try:
            if names != self.profile_names:
                self.profile_names = names
                self.profile_row.set_model(Gtk.StringList.new(names))
            saved = self.window.config.get("profile")
            index = names.index(saved) if saved in names else 0
            if names:
                self.profile_row.set_selected(index)
            self.profile_row.set_subtitle("" if names else "Add one to mailsigs/profiles/")
        finally:
            self._updating = False
        self._sync_ref_only()
        self.render()

    def _profile_name(self) -> str | None:
        i = self.profile_row.get_selected()
        return self.profile_names[i] if 0 <= i < len(self.profile_names) else None

    def _on_profile_changed(self, *_args) -> None:
        if self._updating:
            return
        name = self._profile_name()
        if name is not None:
            self.window.config.set("profile", name)
        self.render()

    def _on_disclaimer_changed(self, row: Adw.SwitchRow, _pspec) -> None:  # noqa: ANN001
        self.window.config.set("include_disclaimer", row.get_active())
        self.render()

    def _on_ref_only_changed(self, row: Adw.SwitchRow, _pspec) -> None:  # noqa: ANN001
        self.window.config.set("ref_only", row.get_active())
        self._sync_ref_only()
        self.render()

    def _sync_ref_only(self) -> None:
        # The disclaimer and the profile do not apply to a reference-only signature.
        ref_only = self.ref_only_row.get_active()
        self.disclaimer_row.set_sensitive(not ref_only)
        self.profile_row.set_sensitive(not ref_only and bool(self.profile_names))

    def set_custom_font(self, custom: bool) -> None:
        set_class(self.textview, CUSTOM_FONT_CLASS, custom)
        self.textview.set_monospace(not custom)

    def refresh_message_ref(self) -> None:
        self.message_ref = generate_message_ref()
        self.render()
        self.window.toast(f"New message reference {self.message_ref}")

    # ------------------------------------------------------------------ text

    def render(self) -> None:
        self.ref_row.set_subtitle(self.message_ref)
        ws = self.window.workspace
        if ws is None:
            self.buffer.set_text("")
            return
        self.buffer.set_text(assemble_signature(
            signoff=ws.signoff,
            profile=ws.get_profile(self._profile_name()),
            disclaimer=ws.disclaimer,
            include_disclaimer=self.disclaimer_row.get_active(),
            message_ref=self.message_ref,
            ref_only=self.ref_only_row.get_active(),
        ))

    def current_text(self) -> str:
        start, end = self.buffer.get_bounds()
        return self.buffer.get_text(start, end, False)

    def copy_signature(self) -> None:
        if self.window.workspace is None:
            return
        copy_text(self, self.current_text())
        self.window.toast("Signature copied")
