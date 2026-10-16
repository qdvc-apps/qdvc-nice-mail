# QDVC Nice Mail

<img src="data/icons/hicolor/scalable/apps/qdvc.NiceMail.svg" alt="" width="96" align="right">

Write emails faster by keeping your most-used building blocks one click away:
a searchable **emoji** picker with favourites and skin tones, a library of
reusable **phrases**, an assembled plaintext mail **signature**, and a quick
**note to self** saved as an `.eml`.

Built in Python following the
[QDVC Python GTK app specification](https://github.com/qdvc-apps/qdvc-python-gtk-app-specification),
with two front-ends over the same files:

- **GTK 3** — the classic look (menubar, toolbars, statusbar), at home on MATE.
  The default.
- **GTK 4 / libadwaita** — a GNOME app following the GNOME HIG: a view
  switcher in the header bar, header-bar buttons, toasts, and a layout that
  adapts down to phone width; light and dark styles.

Switch between them in **Preferences** (it takes effect the next time the app
starts), or start one explicitly with `--gtk3` / `--gtk4`.

## What it does

The window has four pages: tabs under the menubar in GTK 3 (the **tab bar
sits above the toolbar**, because each tab carries its own toolbar of relevant
actions), a view switcher in GTK 4's header bar.

1. **Emoji** — a table of emoji, one per row (symbol, name, and your optional
   user label). Select a row and press **Ctrl+C** (or Enter, or double-click)
   to copy the emoji. Choose the **block** — *Favourites* by default, or
   *All Emoji* (the full Unicode set) — and **search** by name, description or
   your user label (**Ctrl+F** jumps to the search box; in GTK 4 you can just
   start typing, and Enter copies the selected match). **Add to (or remove
   from) your favourites** with a right-click, or GTK 4's star button; give a
   favourite a **user label**; **move** favourites up and down to order them.
   The **skin tone** is set in Preferences and persists between sessions. If
   an emoji isn't in the list (many multi-part emoji such as ❤️‍🩹 have no
   single Unicode name and so aren't generated), use **Add Custom** to paste
   it in; it's saved to your favourites and also shown in *All Emoji*, noted
   as a custom emoji.
2. **Phrases** — your common phrases, listed alphabetically, with a search
   box (**Ctrl+F**), and **add**, **edit** and **delete**. Select one and
   Ctrl+C (or the Copy button, Enter or a double-click) to copy it.
3. **Signature** — assembles a plaintext signature. Pick a **profile**, toggle
   the **disclaimer** on/off, and hit **New Ref** (or **F5**) for a fresh
   message reference. Copy the result with the Copy button or Ctrl+C. A
   **Ref Only** toggle strips everything but the m-dash and the message ref
   line; while it's on, the disclaimer toggle is disabled. The disclaimer,
   Ref Only, and profile choices persist between sessions.
4. **Note to Self** — write a quick note and save it as an `.eml` you can send
   to yourself. Fill in a **From / To** address (remembered between sessions), a
   **subject**, and a plaintext **body**; a green callout shows the message ref
   that will be attached (**New Ref**, F5, or Refresh regenerates it).
   **Send** (the disk icon) writes a self-addressed `.eml` — From and To are the
   same address, dated now — whose body is your text followed by the m-dash and
   message-ref trailer. You choose where to save it; the default filename is
   `yyyy-mm-dd-message-ref-<ref>.eml`. After saving, the subject and body are
   cleared and a fresh message ref is generated for the next note. Its message
   ref is independent of the Signature page's. This page works without a
   workspace.

**Copy** (`Ctrl+C`) and **Refresh** (`Ctrl+R`) adapt to the active page: Copy
copies the selected emoji/phrase, or the whole signature; Refresh reloads the
workspace from disk, and on the Signature and Note pages also generates a new
message ref. `Alt+1` … `Alt+4` switch pages.

In GTK 3, every menu is reachable by mnemonic — **Alt+F** File, **Alt+E**
Edit, **Alt+V** View, **Alt+H** Help — and menu items show their shortcuts
inline. In GTK 4, everything else is in the main menu (☰), and **Ctrl+?**
lists every shortcut.

## The workspace folder

All data lives in a plain-text **workspace folder** you open with
**Open Workspace…** (`Ctrl+O`). Missing files are created for you the first
time (the app asks first if the folder doesn't look like a workspace yet).
Layout:

```
<workspace>/
    favourite_emoji.csv        columns: id,label,char (favourites, labels, custom glyphs)
    phrases.csv                columns: id,text
    mailsigs/
        signoff.txt            everything before the m-dash
        disclaimer.txt         the disclaimer body
        profiles/
            <name>.txt         one profile per file (dropdown = filename)
```

Each emoji has a stable snake_case **id** derived from its Unicode name
(e.g. `waving_hand_sign`); favourites are stored by that id, alongside an
optional user label in the `label` column. Custom (pasted) favourites get a
`custom_<codepoints>` id and store their glyph in the `char` column so they
survive reload; catalogue emoji leave `char` blank. The default favourite is 😊.

A ready-made `sample-workspace/` is included to try immediately.

### Signature format

```
Kind regards,

John Smith


—

John Smith
Specialist and Superhero
Data by day, defeating villains by night

Disclaimer: a disclaimer text goes here

Message ref. YyM4mRnjHQ
```

Everything before the m-dash comes from `signoff.txt` (followed by an extra
blank line before the m-dash); the block after it is the selected profile; the
disclaimer is included only when the toggle is on; the 10-character message ref
is drawn from an unambiguous alphabet
(`346789ABCDEFGHJKLMNPQRTUVWXYabcdefghijkmnpqrtwxyz`).

## Requirements

- Python **3.10+** with **PyGObject** and **PyYAML**, and either toolkit:
  - **GTK 4 + libadwaita 1.5 or later** for the GNOME front-end (GNOME 46:
    Ubuntu 24.04, Debian 13, Fedora 40 or later); or
  - **GTK 3** for the classic front-end.

```sh
sudo apt install python3-gi python3-yaml gir1.2-gtk-4.0 gir1.2-adw-1   # Debian/Ubuntu, GTK 4
sudo apt install python3-gi python3-yaml gir1.2-gtk-3.0                # Debian/Ubuntu/MATE, GTK 3
sudo dnf install python3-gobject python3-pyyaml gtk4 libadwaita gtk3   # Fedora, both
```

There is nothing to compile. If the chosen front-end's toolkit is missing,
the app starts the other one (with a note on the terminal).

## Install and run

From the repository root:

```sh
scripts/build-app.sh --install   # check, test and install for your user
```

That installs the app under `~/.local` (no root needed): it appears in
Activities (GNOME) or the applications menu (MATE) and can be pinned to the
Dock, and `qdvc-nicemail` runs it from a terminal (if `~/.local/bin` is on your
`PATH`). After pulling or editing the code, run the same command again: it
takes a couple of seconds, and if the app is running it is closed and started
again.

```sh
scripts/build-app.sh             # check dependencies, run the tests, stage build/
scripts/build-app.sh --no-tests  # skip the tests
scripts/build-app.sh --run       # start the staged (or, with --install, installed) app
scripts/build-app.sh --uninstall # remove it again (your workspaces and settings stay)
```

What `--install` puts where:

| Path | What |
| --- | --- |
| `~/.local/share/qdvc-nicemail/app/` | the program |
| `~/.local/bin/qdvc-nicemail` | the launcher |
| `~/.local/share/applications/qdvc.NiceMail.desktop` | the menu entry (named after the application ID, so GNOME on Wayland matches the window to it) |
| `~/.local/share/icons/hicolor/{scalable,symbolic}/apps/qdvc.NiceMail*.svg` | the icons |

Run straight from a checkout instead:

```sh
python3 qdvc_nicemail.py                  # the front-end chosen in Preferences (GTK 3 by default)
python3 qdvc_nicemail.py sample-workspace # open a workspace on launch
python3 qdvc_nicemail.py --gtk4           # the GTK 4 / libadwaita front-end
python3 qdvc_nicemail.py --gtk3           # the GTK 3 front-end
```

## Desktop launcher by hand

If you'd rather not use the script, the launcher is
`data/qdvc.NiceMail.desktop.in` with `@EXEC@` replaced by a command that runs
the app, installed under its application ID:

```sh
sed "s|@EXEC@|python3 $PWD/qdvc_nicemail.py|" data/qdvc.NiceMail.desktop.in \
    > ~/.local/share/applications/qdvc.NiceMail.desktop
desktop-file-validate ~/.local/share/applications/qdvc.NiceMail.desktop
update-desktop-database ~/.local/share/applications
```

(For the icon, also copy `data/icons/hicolor` into `~/.local/share/icons/hicolor`.)
`StartupWMClass=qdvc-nicemail` matches the program name the app sets
(`GLib.set_prgname`), so on X11 the panel associates the running window with
the launcher. If you set up the older `qdvc-nicemail.desktop` launcher by hand
before, remove it to avoid a second menu entry.

## Preferences

**Edit → Preferences** in GTK 3, main menu › Preferences in GTK 4 (`Ctrl+,`):
the **emoji skin tone**, the **signature preview font** (also used for the
Note to Self fields; *Default* restores the built-in monospace font), reopening
the **last workspace** at launch, and the **interface** (GTK 3 or GTK 4). GTK 3
also chooses the toolbar style (labels beside or below icons). Settings live in
`~/.config/qdvc-nicemail/config.yml` and are shared by both front-ends.

## Development checks (no display needed)

```sh
python3 tests_model.py          # pure-model tests
python3 tests_import_smoke.py   # fake-gi import of every module, enum + action checks
python3 tools/make_icon.py      # redraw data/icons/ after editing the icon
```

Maintainers: see [docs/MAINTENANCE.md](docs/MAINTENANCE.md) and
[docs/MAINTENANCE_GTK3_GTK4.md](docs/MAINTENANCE_GTK3_GTK4.md).
