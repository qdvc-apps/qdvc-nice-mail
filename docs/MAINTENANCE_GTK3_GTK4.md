# GTK 3 ↔ GTK 4 — element by element

QDVC Nice Mail has two front-ends on one pure core (spec §1, §9): GTK 3 in
`qdvc/gtk3/` (classic MATE look, the default) and GTK 4 / libadwaita in
`qdvc/gtk4/` (GNOME HIG). This file maps every user-facing element of one to
the other, so a change can be made in both (the parity rule, spec §14). What
is shared lives in the pure layer: the model (`workspace.py`), the signature
and note builders (`mailsig.py`, `note.py`), and in `ui_prefs.py` the
shortcuts table, page list, dropdown labels and list/search rules.

## Application and window

| Element | GTK 3 | GTK 4 |
| --- | --- | --- |
| Application | `Gtk.Application` (`gtk3_app.py`) | `Adw.Application` (`gtk4_app.py`) |
| Id / program name | `qdvc.NiceMail` / `qdvc-nicemail` | same |
| Icon | `qdvc.NiceMail`, else `internet-mail` | `qdvc.NiceMail`, else `internet-mail`, `mail-send`, … |
| Window | `Gtk.ApplicationWindow`, centred | `Adw.ApplicationWindow`, min 360 × 294 |
| Size saved | `window` on delete-event | `window` + `window_maximized` on close-request |
| Layout | menubar, tab bar, per-tab toolbar, content, statusbar | header bar, `Adw.ViewStack`, `Adw.ViewSwitcherBar` when narrow |
| Pages | `Gtk.Notebook` (tab bar only) + two `Gtk.Stack`s | `Adw.ViewStack` + `Adw.ViewSwitcher` (title widget) |
| Commands | menu items + toolbar buttons with callbacks | `win.*` `Gio.SimpleAction`s (`gtk4_actions.py`) |
| Sensitivity | `_update_actions_sensitivity` | `gtk4_actions.update()` |
| Status messages | `Gtk.Statusbar` | `Adw.Toast`s |
| No workspace | empty lists, a status message | an `Adw.StatusPage` per page with Open Workspace… |
| Open workspace | `Gtk.FileChooserDialog.run()` | `Gtk.FileDialog.select_folder()` (async) |
| New-workspace check | `Gtk.MessageDialog` | `Adw.AlertDialog` |
| Recent workspaces | — (config only) | primary menu › Open Recent |
| Reveal workspace | File › Reveal Workspace in File Manager | primary menu › Show in Files (`Gtk.FileLauncher`) |
| Preferences | `Gtk.Dialog` (Edit › Preferences) | `Adw.PreferencesDialog`, live-apply |
| About | `Gtk.AboutDialog` (Help › About) | `Adw.AboutDialog` (primary menu) |
| Shortcuts reference | — | `Gtk.ShortcutsWindow` from `SHORTCUTS` (Ctrl+?) |
| Quit over D-Bus | `app.quit` action | `app.quit` action |

## Menus and commands

| GTK 3 menu item / button | GTK 4 action | GTK 4 surface |
| --- | --- | --- |
| File › Open Workspace… (Ctrl+O) | `win.open-workspace` | primary menu; empty-state buttons |
| File › Reveal Workspace in File Manager | `win.show-in-files` | primary menu |
| File › Quit (Ctrl+Q) | `app.quit` | Ctrl+Q |
| Edit › Copy (Ctrl+C) | `win.copy` | Copy header button; Ctrl+C (bubble phase) |
| Edit › Preferences (Ctrl+,) | `win.preferences` | primary menu |
| View › Emoji … Note to Self (Alt+1…4) | `win.show-page::<id>` | view switcher; Alt+1…4 |
| View › Refresh (Ctrl+R) | `win.refresh` | primary menu › Refresh from Disk |
| F5 (new message ref) | `win.new-ref` | refresh buttons on Signature and Note |
| Ctrl+F (focus search) | `win.find` | Ctrl+F |
| Help › About | `win.about` | primary menu |
| — | `win.shortcuts` | primary menu; Ctrl+? |
| — | `window.close` | Ctrl+W |

## Emoji

| Element | GTK 3 | GTK 4 |
| --- | --- | --- |
| List | `Gtk.TreeView` over `Gtk.ListStore(str × 4)` | `Gtk.ColumnView` (`.data-table`) over `Gio.ListStore` of `EmojiItem` |
| Columns | Emoji, Name, User label — resizable | same, resizable |
| Block | toolbar `Gtk.ComboBoxText` | linked toggle buttons, stateful `win.emoji-block` |
| Search | second toolbar row, `Gtk.SearchEntry` | search strip, `Gtk.SearchEntry`; type-to-search |
| Search rule | `ui_prefs.emoji_listing` | `Gtk.CustomFilter` → `ui_prefs.emoji_matches` |
| Copy | Ctrl+C, Copy button, double-click | Ctrl+C, Copy button, Enter / double-click, Enter in search |
| Add/remove favourite | right-click menu | star button (action bar), right-click menu |
| User label | right-click › Set User Label… (`Gtk.Dialog`) | label button, right-click (`Adw.AlertDialog` + entry) |
| Move up / down | toolbar buttons, right-click | action bar buttons, right-click |
| Add custom emoji | toolbar Add Custom | header ＋ button |
| Skin tone | Preferences combo | Preferences combo row (with a sample hand) |
| Empty favourites / no match | empty list | status pages ("No Favourites Yet", "No Results") |

## Phrases

| Element | GTK 3 | GTK 4 |
| --- | --- | --- |
| List | `Gtk.TreeView`, one column | `Gtk.ListView`, wrapped labels |
| Order / search | `ui_prefs.phrase_listing` | sorted store + `Gtk.CustomFilter` → `phrase_matches` |
| Add | toolbar Add (`Gtk.Dialog`) | header ＋ button (`Adw.AlertDialog` + entry) |
| Edit / Delete | toolbar buttons | action bar buttons, right-click |
| Delete confirmation | `Gtk.MessageDialog` OK/Cancel | destructive `Adw.AlertDialog` (Cancel is default) |

## Signature

| Element | GTK 3 | GTK 4 |
| --- | --- | --- |
| Profile | toolbar `Gtk.ComboBoxText` | `Adw.ComboRow` |
| Disclaimer | `Gtk.ToggleToolButton` | `Adw.SwitchRow` |
| Ref Only | `Gtk.ToggleToolButton`; disables Disclaimer | `Adw.SwitchRow`; disables Disclaimer and Profile |
| New Ref | toolbar button, F5 | button on the Message Reference row, F5 |
| Preview | monospace `Gtk.TextView` | monospace `Gtk.TextView` in a framed card |
| Copy | toolbar Copy, Ctrl+C | header Copy, group-header Copy, Ctrl+C |
| Custom font | `override_font(Pango.FontDescription)` | CSS class + one provider (`FontStyler`) |

## Note to Self

| Element | GTK 3 | GTK 4 |
| --- | --- | --- |
| From / To, Subject | `Gtk.Entry` in a `Gtk.Grid` | `Adw.EntryRow`s |
| Body | `Gtk.TextView` in a framed scroller | `Gtk.TextView` in a framed card |
| Callout | green `Gtk.InfoBar` (CSS on `@success_color`) | `.callout` box (CSS on `@success_bg_color`) |
| Send | toolbar Send (document-save), `Gtk.FileChooserDialog` | header Send… (document-save), `Gtk.FileDialog.save()` |
| Save folder | chooser default | remembers the last folder in the session |

## Preferences

| Setting (config key) | GTK 3 | GTK 4 |
| --- | --- | --- |
| Toolbar style (`toolbar_style`) | combo | — (no toolbar, spec §9) |
| Skin tone (`skin_tone`) | combo | `Adw.ComboRow` |
| Font (`signature_font`) | `Gtk.FontButton` + Default | `Gtk.FontDialogButton` + reset button |
| Interface (`ui_backend`) | combo, after restart | `Adw.ComboRow`, after restart |
| Reopen last workspace (`reopen_last`) | check button | `Adw.SwitchRow` |

## List models and data binding — cheat-sheet

| Concern | GTK 3 | GTK 4 |
| --- | --- | --- |
| Row data | `Gtk.ListStore` columns of str | `Gio.ListStore(item_type=…)` of `GObject.Object` subclasses (`EmojiItem`, `PhraseItem`) holding the model objects |
| Filling | `store.clear()` + `append([...])` | `store.splice(0, n, items)` (one change notification) |
| Filtering | rebuild the store from `emoji_listing` | `Gtk.FilterListModel` + `Gtk.CustomFilter`; `filter.changed(Gtk.FilterChange.DIFFERENT)` on each keystroke |
| Selection | `view.get_selection().get_selected()` | `Gtk.SingleSelection(autoselect=True)`; `get_selected_item()`, `get_selected()` |
| Cells | `Gtk.CellRendererText`, `text=column` | `Gtk.SignalListItemFactory`: `setup` builds a `Gtk.Label`, `bind` sets its text from `get_item()` |
| Activation | `row-activated` | `activate(position)` on the view |
| Context menu | `button-press-event` + `Gtk.Menu.popup_at_pointer` | `Gtk.GestureClick(button=3)` / `Gtk.GestureLongPress` per cell + one `Gtk.PopoverMenu` on the page, pointed at the click |
| Reselect after a change | iterate the store, `select_iter` | iterate the filter model, `set_selected(pos)`, `scroll_to(pos, …)` |
| Positions | tree paths of the store | positions in the *filtered* model (the selection's model) |

## GTK 4 pitfalls met here

- Application accelerators run before the focused widget: Ctrl+C is on a
  bubble-phase `Gtk.ShortcutController` instead (see MAINTENANCE.md).
- `Gdk.Clipboard.set_text()` is not introspectable; use `clipboard.set(text)`
  (`gdk_clipboard_set_value`).
- A popover must be parented to a widget that unparents its children on
  dispose (a `Gtk.Box` does); the pages parent their context menus to
  themselves.
- `Adw.AlertDialog`'s default response is its default widget, so an entry with
  `activates_default` answers it on Enter; keep that response enabled.
- GTK 3 and GTK 4 cannot be loaded into one process; the dispatcher and the
  build script probe typelibs with `gi.Repository.enumerate_versions` (no load)
  or in a separate process.
