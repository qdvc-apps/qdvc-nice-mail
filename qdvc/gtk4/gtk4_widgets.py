"""Small widget helpers shared by the GTK 4 pages."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk, Pango  # noqa: E402

from ..ui_prefs import font_css  # noqa: E402

#: Widgets carrying this class use the user's signature font (Preferences).
CUSTOM_FONT_CLASS = "qdvc-custom-font"


def load_css(provider: Gtk.CssProvider, css: str) -> None:
    if hasattr(provider, "load_from_string"):  # GTK 4.12+
        provider.load_from_string(css)
    else:  # pragma: no cover - older GTK 4
        provider.load_from_data(css, -1)


def status_page(icon_name: str, title: str, description: str,
                button_label: str | None = None, action_name: str | None = None,
                action_target: GLib.Variant | None = None) -> Adw.StatusPage:
    """An empty-state page, optionally with one pill button bound to an action."""
    page = Adw.StatusPage(icon_name=icon_name, title=title, description=description,
                          vexpand=True, hexpand=True)
    if button_label and action_name:
        button = Gtk.Button(label=button_label, action_name=action_name,
                            halign=Gtk.Align.CENTER)
        if action_target is not None:
            button.set_action_target_value(action_target)
        button.add_css_class("pill")
        button.add_css_class("suggested-action")
        page.set_child(button)
    return page


def no_workspace_page(icon_name: str, what: str) -> Adw.StatusPage:
    return status_page(
        icon_name, "No Workspace Open",
        f"Open a workspace folder to see {what}. Your favourites, phrases and signature "
        "pieces are kept there as plain text files.",
        "Open Workspace…", "win.open-workspace")


def icon_button(icon_name: str, tooltip: str, action_name: str, flat: bool = False,
                target: GLib.Variant | None = None) -> Gtk.Button:
    button = Gtk.Button(icon_name=icon_name, tooltip_text=tooltip, action_name=action_name,
                        valign=Gtk.Align.CENTER)
    if target is not None:
        button.set_action_target_value(target)
    if flat:
        button.add_css_class("flat")
    return button


def copy_text(widget: Gtk.Widget, text: str) -> None:
    # Gdk.Clipboard.set() is gdk_clipboard_set_value (the C set_text() is
    # not introspectable); PyGObject wraps the str in a GValue.
    widget.get_clipboard().set(text)


def set_class(widget: Gtk.Widget, css_class: str, on: bool) -> None:
    if on:
        widget.add_css_class(css_class)
    else:
        widget.remove_css_class(css_class)


class FontStyler:
    """Applies the user's signature font (a Pango font description string, as
    GTK 3's FontButton and GTK 4's FontDialogButton both write it) to every
    widget carrying :data:`CUSTOM_FONT_CLASS`, through one CSS provider."""

    def __init__(self, display) -> None:  # noqa: ANN001
        self.provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(
            display, self.provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1)
        self.font = ""

    def set_font(self, desc_string: str) -> None:
        self.font = desc_string or ""
        css = ""
        if self.font:
            desc = Pango.FontDescription.from_string(self.font)
            size = desc.get_size() / Pango.SCALE if desc.get_size() else None
            if size and desc.get_size_is_absolute():
                size = size * 0.75  # device pixels -> points
            fields = desc.get_set_fields()
            weight = int(desc.get_weight()) if fields & Pango.FontMask.WEIGHT else None
            italic = desc.get_style() in (Pango.Style.ITALIC, Pango.Style.OBLIQUE)
            css = font_css(f".{CUSTOM_FONT_CLASS} text", desc.get_family(), size, weight,
                           italic)
        load_css(self.provider, css)
