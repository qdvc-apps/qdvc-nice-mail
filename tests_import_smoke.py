"""Display-free import smoke test (spec §13).

Installs a permissive fake ``gi`` so every module under qdvc/gtk3/ can be
imported without a GTK runtime, exercising class bodies, __gsignals__ and
top-level code. Enum-derived constants must go through guarded helpers.
"""
import importlib
import sys
import types


class _AnyMeta(type):
    """Metaclass so class-level attribute access resolves (SignalFlags.RUN_FIRST)."""

    def __getattr__(cls, name):
        return _Anything()

    def __getitem__(cls, k):
        return _Anything()


class _Anything(metaclass=_AnyMeta):
    """Catch-all usable as a base class, instance, callable, and attr chain."""

    def __init__(self, *a, **k):
        pass

    def __getattr__(self, name):
        return _Anything()

    def __call__(self, *a, **k):
        return _Anything()

    def __getitem__(self, k):
        return _Anything()

    def __init_subclass__(cls, **kwargs):
        pass


def _install_fake_gi():
    gi = types.ModuleType("gi")

    def require_version(_name, _ver):
        return None

    gi.require_version = require_version

    repo = types.ModuleType("gi.repository")

    class _ModuleAny(types.ModuleType):
        def __getattr__(self, name):
            # The _Anything class works as a base class (Gtk.Box) and, via its
            # metaclass, resolves chained access like GObject.SignalFlags.RUN_FIRST.
            return _Anything

    for mod_name in ("Gtk", "Gdk", "Gio", "GLib", "GObject", "Pango"):
        m = _ModuleAny("gi.repository." + mod_name)
        setattr(repo, mod_name, m)
        sys.modules["gi.repository." + mod_name] = m

    gi.repository = repo
    sys.modules["gi"] = gi
    sys.modules["gi.repository"] = repo


def _check_gtk_enum_members() -> list[str]:
    """Static check: every ``Gtk.<Enum>.<MEMBER>`` used in the views must be a
    real GTK 3 member.

    The fake ``gi`` stub returns a truthy value for *any* attribute, so a typo
    or nonexistent enum member (e.g. ``Gtk.MessageType.SUCCESS``, which does not
    exist in GTK 3) imports cleanly and only blows up at runtime. This pass
    parses the source for such accesses and validates them against a curated map
    of real GTK 3 enum members, closing that blind spot.
    """
    import glob
    import os
    import re

    # Curated: the GTK 3 enums the codebase uses, with their valid members.
    valid = {
        "AccelFlags": {"VISIBLE", "LOCKED", "MASK"},
        "ButtonsType": {"NONE", "OK", "CLOSE", "CANCEL", "YES_NO", "OK_CANCEL"},
        "FileChooserAction": {"OPEN", "SAVE", "SELECT_FOLDER", "CREATE_FOLDER"},
        "IconSize": {
            "INVALID", "MENU", "SMALL_TOOLBAR", "LARGE_TOOLBAR",
            "BUTTON", "DND", "DIALOG",
        },
        "MessageType": {"INFO", "WARNING", "QUESTION", "ERROR", "OTHER"},
        "Orientation": {"HORIZONTAL", "VERTICAL"},
        "PolicyType": {"ALWAYS", "AUTOMATIC", "NEVER", "EXTERNAL"},
        "ResponseType": {
            "NONE", "REJECT", "ACCEPT", "DELETE_EVENT", "OK", "CANCEL",
            "CLOSE", "YES", "NO", "APPLY", "HELP",
        },
        "SelectionMode": {"NONE", "SINGLE", "BROWSE", "MULTIPLE"},
        "ShadowType": {"NONE", "IN", "OUT", "ETCHED_IN", "ETCHED_OUT"},
        "ToolbarStyle": {"ICONS", "TEXT", "BOTH", "BOTH_HORIZ"},
        "WindowPosition": {
            "NONE", "CENTER", "MOUSE", "CENTER_ALWAYS", "CENTER_ON_PARENT",
        },
        "WrapMode": {"NONE", "CHAR", "WORD", "WORD_CHAR"},
    }
    pattern = re.compile(r"Gtk\.([A-Z][A-Za-z]+)\.([A-Z][A-Z_]+)\b")
    here = os.path.dirname(os.path.abspath(__file__))
    problems: list[str] = []
    for path in glob.glob(os.path.join(here, "qdvc", "gtk3", "*.py")):
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        for enum, member in pattern.findall(src):
            if enum in valid and member not in valid[enum]:
                problems.append(
                    f"{os.path.basename(path)}: Gtk.{enum}.{member} is not a "
                    f"valid GTK 3 member"
                )
    return problems


def main() -> int:
    _install_fake_gi()
    modules = [
        "qdvc",
        "qdvc.config",
        "qdvc.naming",
        "qdvc.emoji",
        "qdvc.models",
        "qdvc.mailsig",
        "qdvc.note",
        "qdvc.workspace",
        "qdvc.platform_utils",
        "qdvc.ui_prefs",
        "qdvc.gtk3.gtk3_app",
        "qdvc.gtk3.gtk3_main_window",
        "qdvc.gtk3.gtk3_emoji_tab",
        "qdvc.gtk3.gtk3_phrases_tab",
        "qdvc.gtk3.gtk3_signature_tab",
        "qdvc.gtk3.gtk3_note_tab",
        "qdvc.gtk3.gtk3_preferences",
        "qdvc.gtk3.gtk3_shortcuts",
    ]
    failures = []
    for name in modules:
        try:
            importlib.import_module(name)
        except Exception as exc:  # noqa: BLE001
            failures.append((name, repr(exc)))

    enum_problems = _check_gtk_enum_members()

    if failures or enum_problems:
        for name, err in failures:
            print(f"FAIL {name}: {err}")
        for problem in enum_problems:
            print(f"FAIL {problem}")
        return 1
    print(
        f"import smoke test OK ({len(modules)} modules; "
        f"enum members validated)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
