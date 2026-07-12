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

## Runtime note specific to this app

The emoji list is built at runtime from the standard-library `unicodedata`
(see `qdvc/emoji.py`), so no third-party emoji package is required (satisfying
the spec's "third-party libs SHOULD be optional").

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

- `favourite_emoji.csv` — header `id,label`; one favourite per row, in display
  order. `label` is an optional user label and may be empty. Files written by
  older versions with a bare `id` header still load (the reader tolerates a
  missing `label` column).
- `phrases.csv` — header `id,text`; rows are stored in display order.
- `mailsigs/signoff.txt` — free text placed before the m-dash.
- `mailsigs/disclaimer.txt` — disclaimer body (prefixed `Disclaimer: ` on
  output, only when the toolbar toggle is on).
- `mailsigs/profiles/<name>.txt` — one profile; filename stem is the dropdown
  label; file contents are the block after the m-dash.

## Model / load pipeline

`Workspace(path)` runs `scan()` to build `favourite_ids` (plus the
`favourite_labels` map), `phrases`, and `profiles`. `ensure_scaffold()` creates
any missing files with defaults, including the required single default
favourite 😊. Emoji ids are the stable snake_case of the Unicode name;
favourites and their labels reference emoji by id so the CSV stays
human-readable and diff-able. List order in `favourite_emoji.csv` and
`phrases.csv` is significant and preserved on every write, which is what backs
the move-up/move-down feature.

## Signature assembly

`assemble_signature()` (pure, in `qdvc/mailsig.py`) joins blocks with a single
blank line, except that an **extra** blank line precedes the m-dash (two blank
lines between the signoff and the m-dash). The message ref uses the reduced,
unambiguous alphabet in `qdvc/naming.py`.

## UI layout (the tab-bar-above-toolbar deviation)

The main window stacks, top to bottom: menubar, a `Gtk.Notebook` used **only
for its tab bar** (its pages are empty), a `Gtk.Stack` of per-tab toolbars, the
content `Gtk.Stack`, and a statusbar. Switching notebook pages swaps both the
toolbar stack and the content stack (`_on_switch_page`), so each tab shows its
own toolbar between the tab bar and the content.

Two menu commands are tab-adaptive and dispatch on the active page:
`copy_current_tab` (Edit → Copy, Ctrl+C) and `refresh_current_tab` (View →
Refresh, Ctrl+R); the latter rescans the workspace and, on the Signature tab,
also generates a new message ref.

Menu items are built by `_menu_item(label, icon, accel)`: a fixed-width icon
slot keeps every label aligned to the same x-offset (with or without an icon),
and when an `accel` pair is passed the accelerator is both attached to the item
and shown right-aligned via `Gtk.accelerator_get_label`. Icon names go through
`_resolve_icon`, which walks a per-name fallback chain and returns the first
name present in the theme, or `None` (leaving the slot blank rather than
rendering a broken image) — e.g. `help-about` falls back through
`help-browser` / `help-contents` to the near-universal `dialog-information`.
`PreferencesDialog` stores its parent as `main_window` (not `window`, which
collides with a read-only `Gtk.Window` GObject field).
Toolbar combo boxes are given a fixed width so focus/prelight states cannot
relayout neighbouring items.

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
