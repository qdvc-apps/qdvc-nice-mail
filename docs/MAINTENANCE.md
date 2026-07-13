# MAINTENANCE

This app follows the [QDVC Python GTK app
specification](https://github.com/qdvc-apps/qdvc-python-gtk-app-specification).
That document is the source of truth for the shared architecture (pure core vs.
toolkit views, files-as-database, config location, atomic writes, application
identity, the shortcut model, and so on) and is **not** repeated here. This
file records only what is specific to QDVC Nice Mail, and any deviations from
the spec.

## Deviations from the spec

- **No GTK 4 front-end (yet).** `qdvc/gtk4/` is absent, so the dispatcher's
  `--gtk4` path prints a note and falls back to GTK 3 (`qdvc_nicemail.py`), the
  Preferences backend selector is present but disabled, and
  `docs/MAINTENANCE_GTK3_GTK4.md` is omitted (permitted by spec §12 until a
  GTK 4 front-end exists). When GTK 4 is added, restore the parity rule (§14).
- **Tab bar above a per-tab toolbar.** The spec's classic layout is
  menubar → single toolbar → content. This app instead shows a tab bar between
  the menubar and the toolbar, with a *different toolbar per tab*. See "UI
  layout" below for how this is built.
- **`Gtk.ImageMenuItem` menubar.** The spec discourages the deprecated
  `Gtk.ImageMenuItem` in favour of a custom `Box(Image + Label)` in a plain
  `Gtk.MenuItem`. That custom child broke left padding, native accelerator
  display, and mnemonic alignment, so this app deliberately uses
  `Gtk.ImageMenuItem` (with `set_always_show_image(True)`) plus mnemonic labels
  instead. The project owner has accepted this deviation and will amend the
  spec to prioritise a correct menubar over GTK 4 forward-compatibility in a
  GTK 3-only app.

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
qdvc/
    naming.py                 emoji_id (snake_case), message-ref generator
    emoji.py                  EmojiCatalogue (from unicodedata), skin tones
    models.py                 Phrase, Profile dataclasses
    mailsig.py                assemble_signature()
    workspace.py              Workspace: scan/scaffold, CSV + txt I/O, CRUD
    ui_prefs.py               SHORTCUTS table, dropdown label tables
    gtk3/
        gtk3_emoji_tab.py     emoji TreeView; copy, favourites, labels, reorder
        gtk3_phrases_tab.py   phrases list + add/edit/delete/reorder
        gtk3_signature_tab.py signature preview + copy
```

## Data formats (this app)

- `favourite_emoji.csv` — header `id,label,char`; one favourite per row, in
  display order. `label` is an optional user label. `char` holds the literal
  glyph and is populated only for custom (pasted) favourites — catalogue emoji
  leave it blank and resolve their glyph from the catalogue. Files written by
  older versions with an `id` or `id,label` header still load (the reader
  tolerates missing `label`/`char` columns).
- `phrases.csv` — header `id,text`; rows are stored in display order.
- `mailsigs/signoff.txt` — free text placed before the m-dash.
- `mailsigs/disclaimer.txt` — disclaimer body (prefixed `Disclaimer: ` on
  output, only when the toolbar toggle is on).
- `mailsigs/profiles/<name>.txt` — one profile; filename stem is the dropdown
  label; file contents are the block after the m-dash.

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
*All Emoji* block (`custom_favourites()`), where the view annotates the name.
List order in `favourite_emoji.csv` and
`phrases.csv` is significant and preserved on every write, which is what backs
the move-up/move-down feature.

## Signature assembly

`assemble_signature()` (pure, in `qdvc/mailsig.py`) joins blocks with a single
blank line, except that an **extra** blank line precedes the m-dash (two blank
lines between the signoff and the m-dash). The message ref uses the reduced,
unambiguous alphabet in `qdvc/naming.py`. In `ref_only` mode the function
returns just the m-dash, a blank line, and the `Message ref.` line — nothing
else. The Ref Only and Disclaimer toggles (both on the Signature toolbar) and
the Profile choice persist via config keys `ref_only`, `include_disclaimer`,
and `profile`; the signature preview font is config key `signature_font`
(empty = built-in monospace), and the emoji skin tone is config key
`skin_tone` (both set in Preferences).

## UI layout (the tab-bar-above-toolbar deviation)

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
and `Gtk.MenuItem.new_with_mnemonic` otherwise. Labels carry underscore
mnemonics, and top-level menus use them too (`_File` → Alt+F, etc.). Icon names
go through `_resolve_icon`, which walks a per-name fallback chain and returns
the first name present in the theme, or `None` — e.g. `help-about` falls back
through `help-browser` / `help-contents` to the near-universal
`dialog-information`.
`PreferencesDialog` stores its parent as `main_window` (not `window`, which
collides with a read-only `Gtk.Window` GObject field).
Toolbar combo boxes (emoji Block, Signature Profile) are given a fixed width so
focus/prelight states cannot relayout neighbouring items.

Action sensitivity is centralised in `_update_actions_sensitivity`.

## Common maintenance tasks — where to touch

- New emoji-tab control: add the widget in `_build_emoji_toolbar` and a setter
  on `EmojiTab`.
- New signature field: extend `assemble_signature` (pure) and, if driven by
  the toolbar, a control in `_build_signature_toolbar` + setter on
  `SignatureTab`.
- New shortcut: add to `ui_prefs.SHORTCUTS` and wire the accelerator in the
  main window's AccelGroup.
- New tab-adaptive command: add a dispatcher on `MainWindow` (like
  `copy_current_tab`) that branches on `_current_tab_index`.

## Testing

`tests_model.py` exercises the pure layer against a temp workspace (including
favourite labels, reordering, and signature format). `tests_import_smoke.py`
installs a permissive fake `gi` and imports every view module. Pre-ship:
`py_compile` all modules, then both test scripts.
