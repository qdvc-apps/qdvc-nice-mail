# QDVC Nice Mail

Write emails faster by keeping your most-used building blocks one click away:
a searchable **emoji** picker with favourites and skin tones, a library of
reusable **phrases**, and an assembled plaintext mail **signature**.

Built as a Python 3 + GTK 3 desktop app following the
[QDVC Python GTK app specification](https://github.com/qdvc-apps/qdvc-python-gtk-app-specification).
A GTK 4 / libadwaita front-end is **not** provided at this stage; the backend
dispatcher accepts `--gtk4` but falls back to GTK 3 with a note.

## What it does

The window has three tabs. The **tab bar sits above the toolbar**, because
each tab carries its own toolbar of relevant actions (the menubar stays on
top).

1. **Emoji** — a table of emoji, one per row (symbol, name, and your optional
   user label). Select a row and press **Ctrl+C** to copy the emoji. The
   toolbar's first row offers a **block** dropdown (*Favourites* by default, or
   *All Emoji* — the full Unicode set), an **Add Custom** button, **Move
   Up/Down** buttons to reorder favourites, and a **Copy** button; a second row
   holds the **search** box, which matches the emoji name, description, or your
   user label (**Ctrl+F** jumps to it). The **skin tone** is set in *Edit →
   Preferences* and persists between sessions. **Right-click** any emoji to add
   it to (or remove it from)
   your favourites, set a **user label** on a favourite, or move it up/down. If
   an emoji isn't in the list (many multi-part emoji such as ❤️‍🩹 have no single
   Unicode name and so aren't generated), use **Add Custom** to paste it in;
   it's saved to your favourites and also shown in *All Emoji*, noted as a
   custom emoji.
2. **Phrases** — your common phrases, listed alphabetically, with toolbar
   buttons to **add**, **edit**, and **delete**, plus a **search** box on a
   second row (**Ctrl+F** jumps to it). Select one and Ctrl+C (or the Copy
   button) to copy it.
3. **Signature** — assembles a plaintext signature. Pick a **profile** in the
   toolbar, toggle the **disclaimer** on/off, and hit **New Ref** (or **F5**)
   for a fresh message reference. Copy the result with the Copy button. A
   **Ref Only** toggle strips everything but the m-dash and the message ref
   line; while it's on, the disclaimer toggle is disabled. The disclaimer,
   Ref Only, and profile choices persist between sessions.
4. **Note to Self** — write a quick note and save it as an `.eml` you can send
   to yourself. Fill in a **From / To** address (remembered between sessions), a
   **subject**, and a plaintext **body**; a callout shows the message ref that
   will be attached (**New Ref** regenerates it). **Send** (the disk icon) writes
   a self-addressed `.eml` — From and To are the same address, dated now — whose
   body is your text followed by the m-dash and message-ref trailer. You choose
   where to save it; the default filename is
   `yyyy-mm-dd-message-ref-<ref>.eml`. Its message ref is independent of the
   Signature tab's.

**Edit → Copy** (`Ctrl+C`) and **View → Refresh** (`Ctrl+R`) adapt to the active
tab: Copy copies the selected emoji/phrase, or the whole signature; Refresh
reloads the table from disk, and on the Signature tab also generates a new
message ref.

Table columns (in the Emoji and Phrases tabs) can be resized by dragging their
header edges.

## The workspace folder

All data lives in a plain-text **workspace folder** you open from
**File → Open Workspace…** (`Ctrl+O`). Missing files are created for you on
first open. Layout:

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

- Python **3.10+**
- **PyGObject** + **GTK 3** (`python3-gi`, `gir1.2-gtk-3.0`)
- **PyYAML** (for the preferences file)

On Debian/Ubuntu/MATE:

```sh
sudo apt install python3-gi gir1.2-gtk-3.0 python3-yaml
```

## Run

```sh
python3 qdvc_nicemail.py                 # GTK 3 (default)
python3 qdvc_nicemail.py sample-workspace # open a workspace on launch
python3 qdvc_nicemail.py --gtk4          # note + falls back to GTK 3
```

Preferences (**Edit → Preferences**, `Ctrl+,`) let you switch the toolbar
style between labels-beside-icons and labels-below-icons, choose the **emoji
skin tone**, pick a **signature preview font** (also used for the Note to Self
fields, with a Default button to restore the built-in monospace font), and
toggle reopening the last workspace.

Every menu is reachable by mnemonic — **Alt+F** File, **Alt+E** Edit, **Alt+V**
View, **Alt+H** Help — and menu items show their shortcuts inline.

## Desktop launcher

Copy `qdvc-nicemail.desktop` to `~/.local/share/applications/`, then edit the
absolute paths in `Exec` and `Path`:

```sh
cp qdvc-nicemail.desktop ~/.local/share/applications/
# edit Exec=/Path= to point at this folder
desktop-file-validate ~/.local/share/applications/qdvc-nicemail.desktop
update-desktop-database ~/.local/share/applications
```

`StartupWMClass=qdvc-nicemail` matches the app's `GLib.set_prgname` call so the
panel associates the running window with the launcher.

## Development checks (no display needed)

```sh
python3 -m py_compile qdvc/*.py qdvc/gtk3/*.py qdvc_nicemail.py
python3 tests_model.py          # pure-model tests
python3 tests_import_smoke.py   # fake-gi import of every view module
```
