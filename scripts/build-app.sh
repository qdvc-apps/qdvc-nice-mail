#!/usr/bin/env bash
# Check, test, stage and install QDVC Nice Mail for the current user (no root).
#
#   scripts/build-app.sh               # check dependencies, run the tests, stage build/
#   scripts/build-app.sh --install     # ...and install to ~/.local (restarts a running copy)
#   scripts/build-app.sh --uninstall   # remove the installed copy, launcher and icons
#   scripts/build-app.sh --no-tests    # skip the tests (combine with --install)
#   scripts/build-app.sh --run         # after building/installing, start the app
#
# Installs:
#   ~/.local/share/qdvc-nicemail/app/                   the program (qdvc_nicemail.py, qdvc/, data/)
#   ~/.local/bin/qdvc-nicemail                          launcher script
#   ~/.local/share/applications/qdvc.NiceMail.desktop   menu entry (Activities, Dock, MATE menu)
#   ~/.local/share/icons/hicolor/.../qdvc.NiceMail*.svg app icons
# The launcher starts the front-end chosen in Preferences (GTK 3 unless you
# pick GTK 4); either works with the same files. Set PREFIX to install
# elsewhere (default: ~/.local).
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
APP_ID="qdvc.NiceMail"
NAME="qdvc-nicemail"
PREFIX="${PREFIX:-$HOME/.local}"
SHARE="$PREFIX/share"
APP_DIR="$SHARE/$NAME/app"
BIN_DIR="$PREFIX/bin"
DESKTOP="$SHARE/applications/$APP_ID.desktop"
ICONS="$SHARE/icons/hicolor"
STAGE="$ROOT/build/$NAME"
# A launcher from the earlier manual setup (README), named after the program.
LEGACY_DESKTOP="$SHARE/applications/$NAME.desktop"

install=0 uninstall=0 tests=1 run=0
for arg in "$@"; do
    case "$arg" in
        --install) install=1 ;;
        --uninstall) uninstall=1 ;;
        --no-tests|--no-test) tests=0 ;;
        --run) run=1 ;;
        -h|--help) sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "Unknown option: $arg (see --help)" >&2; exit 2 ;;
    esac
done

say() { printf '==> %s\n' "$*"; }

# Is a copy running? Ask it to quit through its D-Bus actions (app.quit, in
# both front-ends); it saves its window size first.
running() {
    command -v gdbus >/dev/null 2>&1 || return 1
    gdbus call --session --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus \
        --method org.freedesktop.DBus.NameHasOwner "$APP_ID" 2>/dev/null | grep -q true
}
quit_running() {
    gdbus call --session --dest "$APP_ID" --object-path "/${APP_ID//./\/}" \
        --method org.gtk.Actions.Activate quit [] {} >/dev/null 2>&1 || true
    for _ in $(seq 1 30); do running || return 0; sleep 0.1; done
    echo "warning: the running copy did not quit; restart it to use the new version" >&2
}

refresh_caches() {
    command -v update-desktop-database >/dev/null 2>&1 \
        && update-desktop-database -q "$SHARE/applications" 2>/dev/null || true
    touch "$ICONS" "$SHARE/applications" 2>/dev/null || true
    if [[ -f "$ICONS/index.theme" ]]; then
        command -v gtk4-update-icon-cache >/dev/null 2>&1 \
            && gtk4-update-icon-cache -q -t -f "$ICONS" 2>/dev/null \
            || { command -v gtk-update-icon-cache >/dev/null 2>&1 \
                 && gtk-update-icon-cache -q -t -f "$ICONS" 2>/dev/null; } || true
    fi
}

legacy_note() {
    if [[ -f "$LEGACY_DESKTOP" ]]; then
        echo "note: an older launcher, $LEGACY_DESKTOP, is still installed and may show" >&2
        echo "      a second QDVC Nice Mail entry; remove it with: rm '$LEGACY_DESKTOP'" >&2
    fi
}

if [[ $uninstall -eq 1 ]]; then
    running && { say "Quitting the running copy"; quit_running; }
    rm -rf "$SHARE/$NAME" "$BIN_DIR/$NAME" "$DESKTOP" \
        "$ICONS/scalable/apps/$APP_ID.svg" "$ICONS/symbolic/apps/$APP_ID-symbolic.svg"
    refresh_caches
    say "Uninstalled (your workspaces and ~/.config/$NAME are untouched)"
    legacy_note
    exit 0
fi

# --- dependencies ---------------------------------------------------------
# Each front-end is probed in its own Python process: GTK 3 and GTK 4 cannot
# both be loaded into one.
say "Checking dependencies"
if ! python3 - <<'PY'
import sys
problems = []
if sys.version_info < (3, 10):
    problems.append(f"Python 3.10 or later (this is {sys.version.split()[0]})")
try:
    import gi  # noqa: F401
except ImportError:
    problems.append("PyGObject (python3-gi)")
try:
    import yaml  # noqa: F401
except ImportError:
    problems.append("PyYAML (python3-yaml)")
if problems:
    print("Missing: " + "; ".join(problems), file=sys.stderr)
    sys.exit(1)
PY
then
    cat >&2 <<'HELP'
Install the dependencies, then run this script again:
  Debian/Ubuntu: sudo apt install python3-gi python3-yaml gir1.2-gtk-4.0 gir1.2-adw-1 gir1.2-gtk-3.0
  Fedora:        sudo dnf install python3-gobject python3-pyyaml gtk4 libadwaita gtk3
  Arch:          sudo pacman -S python-gobject python-yaml gtk4 libadwaita gtk3
(Either toolkit is enough: GTK 4 + libadwaita for GNOME, GTK 3 for MATE.)
HELP
    exit 1
fi

gtk4_status=$(python3 - <<'PY' 2>/dev/null || true
import gi
gi.require_version("Gtk", "4.0"); gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk
ok = (Adw.get_major_version(), Adw.get_minor_version()) >= (1, 5)
print(("ok " if ok else "old ") + "GTK %d.%d.%d, libadwaita %d.%d.%d" % (
    Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version(),
    Adw.get_major_version(), Adw.get_minor_version(), Adw.get_micro_version()))
PY
)
gtk3_status=$(python3 - <<'PY' 2>/dev/null || true
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
print("ok GTK %d.%d.%d" % (Gtk.get_major_version(), Gtk.get_minor_version(),
                           Gtk.get_micro_version()))
PY
)
have4=0 have3=0
case "$gtk4_status" in
    ok\ *) have4=1; echo "    GTK 4 front-end: ${gtk4_status#ok }" ;;
    old\ *) echo "    GTK 4 front-end: needs libadwaita 1.5 or later (found ${gtk4_status#old })" ;;
    *) echo "    GTK 4 front-end: not available (gir1.2-gtk-4.0, gir1.2-adw-1)" ;;
esac
case "$gtk3_status" in
    ok\ *) have3=1; echo "    GTK 3 front-end: ${gtk3_status#ok }" ;;
    *) echo "    GTK 3 front-end: not available (gir1.2-gtk-3.0)" ;;
esac
if [[ $have4 -eq 0 && $have3 -eq 0 ]]; then
    cat >&2 <<'HELP'
Neither front-end can run. Install GTK 4 and libadwaita (GNOME) or GTK 3 (MATE):
  Debian/Ubuntu: sudo apt install gir1.2-gtk-4.0 gir1.2-adw-1    (or gir1.2-gtk-3.0)
  Fedora:        sudo dnf install gtk4 libadwaita                (or gtk3)
HELP
    exit 1
fi

# --- tests and build ------------------------------------------------------
if [[ $tests -eq 1 ]]; then
    say "Running the tests"
    if ! { python3 tests_model.py && python3 tests_import_smoke.py; }; then
        echo "Tests failed; nothing was installed." >&2
        exit 1
    fi
fi

say "Staging $STAGE"
rm -rf "$STAGE"
mkdir -p "$STAGE/data"
cp qdvc_nicemail.py "$STAGE/"
cp -r qdvc "$STAGE/"
cp -r data/icons "$STAGE/data/"
find "$STAGE" -name '__pycache__' -prune -exec rm -rf {} +
python3 -m compileall -q "$STAGE" >/dev/null

if [[ $install -eq 1 ]]; then
    was_running=0
    if running; then
        say "Quitting the running copy"
        quit_running
        was_running=1
    fi
    say "Installing to $PREFIX"
    rm -rf "$APP_DIR"
    mkdir -p "$APP_DIR" "$BIN_DIR" "$SHARE/applications" \
        "$ICONS/scalable/apps" "$ICONS/symbolic/apps"
    cp -r "$STAGE/." "$APP_DIR/"
    cat > "$BIN_DIR/$NAME" <<LAUNCHER
#!/bin/sh
exec python3 "$APP_DIR/qdvc_nicemail.py" "\$@"
LAUNCHER
    chmod +x "$BIN_DIR/$NAME"
    exec_path="$BIN_DIR/$NAME"
    # The Desktop Entry spec quotes arguments that contain spaces.
    [[ "$exec_path" == *" "* ]] && exec_path="\"$exec_path\""
    sed "s|@EXEC@|$exec_path|g" "data/$APP_ID.desktop.in" > "$DESKTOP"
    cp "data/icons/hicolor/scalable/apps/$APP_ID.svg" "$ICONS/scalable/apps/"
    cp "data/icons/hicolor/symbolic/apps/$APP_ID-symbolic.svg" "$ICONS/symbolic/apps/"
    if command -v desktop-file-validate >/dev/null 2>&1; then
        desktop-file-validate "$DESKTOP" || echo "warning: desktop-file-validate complained" >&2
    fi
    refresh_caches
    backend=$(cd "$APP_DIR" && python3 -c \
        'from qdvc.config import Config; print(Config().ui_backend)' 2>/dev/null || echo gtk3)
    # As the dispatcher decides: the configured front-end, else the other one.
    if [[ $backend == gtk4 && $have4 -eq 1 ]] || [[ $have3 -eq 0 ]]; then
        shown="GTK 4 (GNOME)"
    else
        shown="GTK 3 (classic)"
    fi
    say "Installed: open QDVC Nice Mail from Activities or the menu, or run $NAME"
    echo "    It starts the $shown front-end; Preferences switches it."
    case ":$PATH:" in *":$BIN_DIR:"*) ;; *) echo "note: $BIN_DIR is not on your PATH" >&2 ;; esac
    legacy_note
    if [[ $was_running -eq 1 ]]; then run=1; fi
fi

if [[ $run -eq 1 ]]; then
    if [[ $install -eq 1 ]]; then cmd=("$BIN_DIR/$NAME"); else cmd=(python3 "$STAGE/qdvc_nicemail.py"); fi
    say "Starting QDVC Nice Mail"
    nohup "${cmd[@]}" >/dev/null 2>&1 &
fi
say "Done"
