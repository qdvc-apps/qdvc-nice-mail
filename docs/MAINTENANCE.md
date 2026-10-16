# MAINTENANCE

This app follows the [QDVC Python GTK app
specification](https://github.com/qdvc-apps/qdvc-python-gtk-app-specification/).
That document is the source of truth for the shared architecture (pure core vs.
toolkit views, files-as-database, config location, atomic writes, application
identity, the shortcut model, and so on) and is **not** repeated here. This
file records only what is specific to QDVC Nice Mail, and any deviations from
the spec. The element-by-element map between the two front-ends is in
[MAINTENANCE_GTK3_GTK4.md](MAINTENANCE_GTK3_GTK4.md).

Both front-ends are complete and at parity: GTK 3 (`qdvc/gtk3/`, the default,
classic MATE look) and GTK 4 / libadwaita (`qdvc/gtk4/`, GNOME HIG), on one
pure core. The parity rule (spec §14) applies to every change.

## Deviations from the spec

- **Tab bar above a per-tab toolbar (GTK 3).** The spec's classic layout is
  menubar → single toolbar → content. This app instead shows a tab bar between
  the menubar and the toolbar, with a *different toolbar per tab*. See "GTK 3
  UI layout" below for how this is built. (GTK 4 follows spec §9 exactly: a
  view switcher, header-bar buttons, no toolbar.)
- **A bundled app icon (§7.3).** The default icon is the app's own
  `qdvc.NiceMail` (`data/icons/`, drawn by `tools/make_icon.py`), as in the
  family's GNOME apps, so the app is recognisable in the Dock, Activities and
  the MATE menu. It is never *required*: `scripts/build-app.sh` installs it
  into the user's hicolor theme, a checkout adds `data/icons` to the icon
  theme's search path, and if neither is found both front-ends fall back to
  the stock themed `internet-mail` (`FALLBACK_ICON_NAME` in `gtk3_app.py`,
  `FALLBACK_ICON_NAMES` in `gtk4_app.py`). There is no custom-icon preference:
  GTK 4 windows only take themed icon names, so it could not reach the window.
- **Launcher name (§7.4).** The launcher is
  `~/.local/share/applications/qdvc.NiceMail.desktop` (from
  `data/qdvc.NiceMail.desktop.in`, installed by `scripts/build-app.sh`), named
  after the application id rather than `qdvc-nicemail.desktop`: GNOME Shell on
  Wayland matches a window to its launcher by the application id.
  `StartupWMClass=qdvc-nicemail` still matches the program name for X11. The
  build script warns about a leftover `qdvc-nicemail.desktop` from the earlier
  manual setup, which would show a second menu entry.
- **libadwaita 1.5 dialog forms (§9).** The GTK 4 front-end uses
  `Adw.PreferencesDialog`, `Adw.AlertDialog` and `Adw.AboutDialog` instead of
  the `Adw.PreferencesWindow` / `Adw.MessageDialog` / `Adw.AboutWindow` the
  spec names: the window forms are deprecated from libadwaita 1.6, and the
  dialog forms adapt to narrow windows. libadwaita 1.5 (GNOME 46) is therefore
  the minimum for GTK 4; the dispatcher falls back to GTK 3 on anything older.
- **Ctrl+C in GTK 4 is not an application accelerator (§10).** GTK 4 runs
  application accelerators before the focused widget, so a global Ctrl+C would
  stop the search boxes and the note body from copying their own selection.
  Ctrl+C (`win.copy`) is instead a shortcut on a bubble-phase controller on the
  window, which sees the key only when the focused widget did not use it. The
  `SHORTCUTS` table marks it `bubble=True`.
- **GTK 3 accelerators are attached by hand (§10).** The GTK 3 menubar wires
  its accelerators in `gtk3_main_window` (`_menu_item(..., accel=...)` and
  `_wire_accelerators`) rather than looping over `ui_prefs.SHORTCUTS`; the
  table documents them (`gtk3_shortcuts.shortcut_rows()`), and
  `tests_model.py` checks the table has no clashing keys. When adding a GTK 3
  shortcut, change both.

## Runtime note specific to this app

The emoji list is built at runtime from the standard-library `unicodedata`
(see `qdvc/emoji.py`), so no third-party emoji package is required (satisfying
the spec's "third-party libs SHOULD be optional"). This scans single code
points, so multi-code-point / ZWJ sequences (e.g. ❤️‍🩹, which has no single
Unicode name) are **not** in the generated catalogue. Users can still add any
such glyph via "custom favourites" (see below); a fuller fix would be to parse
Unicode's `emoji-test.txt`.

## Directory & file layout

Only the app-specific modules are listed; the roles of the standard scaffold
files are defined by the spec.

```
qdvc_nicemail.py              dispatcher: --gtk3/--gtk4 -> ui_backend -> gtk3, with
                              fallbacks both ways (typelibs probed, never loaded)
qdvc/
    __init__.py               APP_ID, APP_NAME, APP_SUMMARY, PRGNAME
    naming.py                 emoji_id (snake_case), message-ref generator
    emoji.py                  EmojiCatalogue (from unicodedata), skin tones
    models.py                 Phrase, Profile dataclasses
    mailsig.py                assemble_signature()
    note.py                   build_note_eml(), note_body(), default_note_filename()
    workspace.py              Workspace: scan/scaffold, CSV + txt I/O, CRUD;
                              looks_like_workspace()
    ui_prefs.py               SHORTCUTS table; PAGES; dropdown labels; the list
                              rules both UIs share (emoji_block_items,
                              emoji_matches, phrase_listing, ...); font_css()
    gtk3/
        gtk3_emoji_tab.py     emoji TreeView; copy, favourites, labels, reorder
        gtk3_phrases_tab.py   phrases list (alphabetical + search) + add/edit/delete
        gtk3_signature_tab.py signature preview + copy
        gtk3_note_tab.py      note-to-self: from/to, subject, body, Send -> .eml
    gtk4/
        gtk4_app.py           Adw.Application: icon, CSS, accelerators, app.quit
        gtk4_window.py        header bar + ViewStack/ViewSwitcher, workspace, toasts
        gtk4_actions.py       every win.* action; update() = sensitivity; primary menu
        gtk4_emoji_page.py    ColumnView over a filtered ListStore; star, label,
                              move, custom emoji, context menu
        gtk4_phrases_page.py  ListView; search; new/edit/delete; context menu
        gtk4_signature_page.py  Profile / Disclaimer / Reference Only rows + preview
        gtk4_note_page.py     entry rows, body, callout; Send -> Gtk.FileDialog
        gtk4_dialogs.py       alert, confirm, prompt_text (Adw.AlertDialog)
        gtk4_preferences.py   Adw.PreferencesDialog (live-apply, backend selector)
        gtk4_shortcuts.py     Keyboard Shortcuts window from SHORTCUTS
        gtk4_widgets.py       status pages, icon buttons, FontStyler, clipboard
        style.css             the few custom styles (glyph size, callout)
data/
    qdvc.NiceMail.desktop.in  launcher template (@EXEC@ filled in by the script)
    icons/hicolor/            the app icon and its symbolic variant (generated)
scripts/build-app.sh          check deps, test, stage build/, install to ~/.local
tools/make_icon.py            draws data/icons/ (edit its constants, rerun)
```

## Data formats (this app)

- `favourite_emoji.csv` — header `id,label,char`; one favourite per row, in
  display order. `label` is an optional user label. `char` holds the literal
  glyph and is populated only for custom (pasted) favourites — catalogue emoji
  leave it blank and resolve their glyph from the catalogue. Files written by
  older versions with an `id` or `id,label` header still load (the reader
  tolerates missing `label`/`char` columns).
- `phrases.csv` — header `id,text`. Rows are stored in insertion/file order,
  but the Phrases tab displays them sorted alphabetically by text.
- `mailsigs/signoff.txt` — free text placed before the m-dash.
- `mailsigs/disclaimer.txt` — disclaimer body (prefixed `Disclaimer: ` on
  output, only when the Disclaimer toggle is on).
- `mailsigs/profiles/<name>.txt` — one profile; filename stem is the dropdown
  label; file contents are the block after the m-dash.

Choosing a folder in Open Workspace… that has none of `favourite_emoji.csv`,
`phrases.csv` or `mailsigs/` (`looks_like_workspace()`) asks before
scaffolding them, in both front-ends. GTK 4 also asks for such a folder passed
on the command line (`open_path`); GTK 3 scaffolds it directly, as before.
Reopening the last workspace never asks.

## Model / load pipeline

`Workspace(path)` runs `scan()` to build `favourite_ids` (plus the
`favourite_labels` and `favourite_chars` maps), `phrases`, and `profiles`.
`ensure_scaffold()` creates any missing files with defaults, including the
required single default favourite 😊. Emoji ids are the stable snake_case of
the Unicode name; favourites and their labels reference emoji by id so the CSV
stays human-readable and diff-able. Custom favourites are pasted glyphs with no
catalogue entry: `add_custom_favourite(char)` assigns a `custom_<codepoints>`
id (`naming.custom_emoji_id`) and stores the glyph in `favourite_chars`;
`resolve_emoji(id)` returns the catalogue `Emoji` or reconstructs a custom one
via `EmojiCatalogue.make_custom` (best-effort name from the component code
points, and skin tone never applied). Custom favourites also appear in the
*All Emoji* block (`custom_favourites()`), where the views annotate the name
(`ui_prefs.emoji_display_name`). List order in `favourite_emoji.csv` is
significant and preserved on every write, which is what backs the emoji
move-up/move-down feature. Phrases are not manually reorderable — both UIs sort
them alphabetically and filter them by a search box — though
`Workspace.move_phrase` remains in the pure layer, unused by the UI.

Which emoji or phrases a page lists for a block and a search query is decided
once, in `ui_prefs` (`emoji_block_items` + `emoji_matches`, `phrase_listing`
+ `phrase_matches`): GTK 3 calls `emoji_listing` / `phrase_listing` to fill
its `Gtk.ListStore`; GTK 4 fills a `Gio.ListStore` with the block and filters
it with a `Gtk.CustomFilter` that calls the same predicate.

## Signature assembly

`assemble_signature()` (pure, in `qdvc/mailsig.py`) joins blocks with a single
blank line, except that an **extra** blank line precedes the m-dash (two blank
lines between the signoff and the m-dash). The message ref uses the reduced,
unambiguous alphabet in `qdvc/naming.py`. In `ref_only` mode the function
returns just the m-dash, a blank line, and the `Message ref.` line — nothing
else. The Ref Only and Disclaimer toggles and the Profile choice persist via
config keys `ref_only`, `include_disclaimer`, and `profile`; the signature
preview font is config key `signature_font` (empty = built-in monospace; a
Pango font description, written alike by GTK 3's `FontButton` and GTK 4's
`FontDialogButton`), and the emoji skin tone is config key `skin_tone` (both
set in Preferences). All keys are shared, so switching front-ends keeps them.

## Note to Self (EML)

`qdvc/note.py` (pure) builds a self-addressed RFC 5322 message via the stdlib
`email` package: `build_note_eml()` sets From and To to the same address, adds
Subject and a Date header (defaults to now; injectable for tests), and sets the
body to `note_body()` — the user's text, two blank lines, an m-dash, a blank
line, and the `Message ref.` line (the same trailer as the Signature tab's
Ref Only mode). `default_note_filename()` yields
`yyyy-mm-dd-message-ref-<ref>.eml`. The From/To address persists via config key
`note_email`; the tab's message ref is independent of the Signature tab's.
`gtk3_note_tab.py` holds the three fields (address, subject, body) — all sharing
the Signature preview font via `set_font()` — and a `Gtk.InfoBar` callout
containing a 24px `emblem-default` icon and a markup label ("This note to self
will be assigned <b>Message ref. …</b>"). GTK 3 has no "success" message type
(only info/warning/question/error), so the bar uses `MessageType.INFO` and is
painted green by `_apply_success_style`, which adds a CSS class plus a
`Gtk.CssProvider` keyed on the theme's exported `@success_color` (with a fixed
green fallback). GTK 4 draws the same callout as a box styled from
`@success_bg_color` / `@success_color` (`style.css`, `.callout`). Send runs
`build_note_eml()` and offers a Save dialog; on a successful save it clears the
subject and body and generates a fresh message ref (as if New Ref were
pressed). New Ref and Refresh both call `refresh_message_ref()`. The Send
button uses the `document-save` icon per the feature request. The page works
without a workspace.

## GTK 3 UI layout (the tab-bar-above-toolbar deviation)

The main window stacks, top to bottom: menubar, a `Gtk.Notebook` used **only
for its tab bar** (its pages are empty), a `Gtk.Stack` of per-tab toolbars, the
content `Gtk.Stack`, and a statusbar. Switching notebook pages swaps both the
toolbar stack and the content stack (`_on_switch_page`), so each tab shows its
own toolbar between the tab bar and the content. The emoji "toolbar" is a
vertical `Gtk.Box` of two `Gtk.Toolbar` rows (controls, then the search box on
its own row); the stack accepts any widget, not just a `Gtk.Toolbar`. The
toolbar stack sets `vhomogeneous(False)` so the single-row Phrases/Signature
toolbars keep their natural height instead of matching the two-row emoji one.

Two menu commands are tab-adaptive: `copy_current_tab` (Edit → Copy, Ctrl+C)
and `refresh_current_tab` (View → Refresh, Ctrl+R) dispatch on the active page
(Refresh rescans the workspace and, on the Signature tab, also generates a new
message ref). The Signature toolbar's Ref Only toggle uses
`_on_ref_only_toggled`; `_apply_ref_only_state` re-renders and disables the
Disclaimer toggle while Ref Only is on. Window-level accelerators (in
`_wire_accelerators`) add F5 (new message ref) and Ctrl+F (focus the emoji
search box when the emoji tab is active).

Menu items are built by `_menu_item(label, icon, accel)`: it uses
`Gtk.ImageMenuItem.new_with_mnemonic` when an icon resolves (so GTK handles
icon/checkmark reservation, left alignment, and native accelerator rendering)
and `Gtk.MenuItem.new_with_mnemonic` otherwise, as spec §8 requires. Labels
carry underscore mnemonics, and top-level menus use them too (`_File` → Alt+F,
etc.). Icon names go through `_resolve_icon`, which walks a per-name fallback
chain and returns the first name present in the theme, or `None` — e.g.
`help-about` falls back through `help-browser` / `help-contents` to the
near-universal `dialog-information`.
`PreferencesDialog` stores its parent as `main_window` (not `window`, which
collides with a read-only `Gtk.Window` GObject field).
Toolbar combo boxes (emoji Block, Signature Profile) are given a fixed width so
focus/prelight states cannot relayout neighbouring items.

Action sensitivity is centralised in `_update_actions_sensitivity`. The
application also has an `app.quit` action (not shown in the UI), so
`scripts/build-app.sh` can close a running copy over D-Bus before reinstalling.

## GTK 4 UI layout

One `Adw.HeaderBar`: the visible page's own buttons at the start (Copy and
Add Custom Emoji; Copy and New Phrase; Copy; Send…), an `Adw.ViewSwitcher` as
the title, and the primary menu at the end (Open Workspace…, Open Recent, Show
in Files, Refresh from Disk; Preferences, Keyboard Shortcuts, About). Below
620 sp the switcher moves to an `Adw.ViewSwitcherBar` at the bottom and the
title shows the page name (an `Adw.Breakpoint`). Statusbar messages become
toasts.

The Emoji and Phrases pages are an `Adw.ToolbarView` each: a search strip on
top (plus the Favourites | All Emoji toggle, a stateful `win.emoji-block`),
the list, and a `Gtk.ActionBar` with the selection-level actions (star, user
label, move up/down; edit, delete). Typing anywhere on the page searches
(`SearchEntry.set_key_capture_widget`); Enter in the search box copies the
selected (by default the first) match; Enter or a double-click on a row copies
it; right-click or long-press opens a context menu. Without a workspace, these
pages and Signature show a "No Workspace Open" status page; Note to Self works
regardless.

Every command is a `win.*` action (`gtk4_actions.install`), and `update()`
computes all sensitivity in one place, called on page changes, selection
changes and reloads.

## Common maintenance tasks — where to touch

- New command: GTK 3 — a menu item / toolbar button in `gtk3_main_window` and
  its rule in `_update_actions_sensitivity`; GTK 4 — an action in
  `gtk4_actions.install`, its rule in `gtk4_actions.update`, and a button or
  menu item naming it. A shortcut goes in `ui_prefs.SHORTCUTS` (which registers
  it in GTK 4 and lists it in its Keyboard Shortcuts window) and in the GTK 3
  menubar. `tests_import_smoke.py` fails if a `win.*` name is used but not
  installed, or installed but unused.
- New emoji-page control: GTK 3 — `_build_emoji_toolbar` and a setter on
  `EmojiTab`; GTK 4 — `EmojiPage._build_search_strip` or `_build_action_bar`.
- New list rule (what is shown, how search matches): `ui_prefs`, so both UIs
  follow it, with a test in `tests_model.py`.
- New signature field: extend `assemble_signature` (pure) and add a control in
  `_build_signature_toolbar` (GTK 3) and a row in `SignaturePage` (GTK 4).
- New preference: a default in `config.DEFAULTS`, a control in both
  Preferences dialogs.
- The icon: edit the constants in `tools/make_icon.py` and run it; `--preview`
  writes `build/icon-preview.png` (needs `rsvg-convert`). Keep the symbolic
  icon's details on whole pixels, or they blur at 16 px.

## Building and installing

`scripts/build-app.sh` checks Python, PyGObject and PyYAML, reports which
front-ends can run (each probed in its own process: GTK 3 and GTK 4 cannot
share one), runs both test scripts, stages `build/qdvc-nicemail/` and, with
`--install`, copies it to `~/.local/share/qdvc-nicemail/app/` with a
`~/.local/bin/qdvc-nicemail` launcher, the `.desktop` file and the icons. A
running copy is asked to quit over D-Bus first (`app.quit`, in both
front-ends) and restarted afterwards. `--uninstall` removes all of it and
keeps the config. See `--help`.

## Testing

`tests_model.py` exercises the pure layer against a temp workspace (including
favourite labels, signature format, note-to-self EML output, the shared list
and search rules, the shortcuts table, `font_css`, `looks_like_workspace`) and
the dispatcher's backend selection.
`tests_import_smoke.py` installs a permissive fake `gi` and imports every
module, including the dispatcher and both front-ends. Because that stub returns
a truthy value for *any* attribute (so a nonexistent enum member like
`Gtk.MessageType.SUCCESS` would import fine and only fail at runtime), it also
statically validates every enum access against curated maps of real members —
GTK 3.24 for `qdvc/gtk3/`; GTK 4.14, libadwaita 1.5, Pango and Gio for
`qdvc/gtk4/` — and reports an enum missing from the map. When using a new enum,
add its valid members (on the oldest supported version) to the map. It also
checks that the GTK 4 `win.*` actions used and installed agree. Pre-ship:
`scripts/build-app.sh` (or `py_compile` all modules, then both test scripts).
