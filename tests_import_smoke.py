"""Display-free import smoke test (spec §13).

Installs a permissive fake ``gi`` so every module under qdvc/gtk3/ and
qdvc/gtk4/ can be imported without a GTK runtime, exercising class bodies,
__gsignals__ and top-level code. Enum-derived constants must go through
guarded helpers.

Because the stub accepts any attribute, it also statically validates every
``Gtk.<Enum>.<MEMBER>`` (and, for GTK 4, ``Adw.``/``Pango.``/``Gio.``) access
against curated maps of real members, per toolkit; and checks that the GTK 4
window's ``win.*`` actions and the shared SHORTCUTS table agree.
"""
import ast
import glob
import importlib
import os
import re
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))


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

    class _Repository:
        @staticmethod
        def get_default():
            return _Repository()

        def enumerate_versions(self, _namespace):
            return []

    gi.Repository = _Repository

    repo = types.ModuleType("gi.repository")

    class _ModuleAny(types.ModuleType):
        def __getattr__(self, name):
            # The _Anything class works as a base class (Gtk.Box) and, via its
            # metaclass, resolves chained access like GObject.SignalFlags.RUN_FIRST.
            return _Anything

    for mod_name in ("Gtk", "Gdk", "Gio", "GLib", "GObject", "Pango", "Adw", "Graphene"):
        m = _ModuleAny("gi.repository." + mod_name)
        setattr(repo, mod_name, m)
        sys.modules["gi.repository." + mod_name] = m

    gi.repository = repo
    sys.modules["gi"] = gi
    sys.modules["gi.repository"] = repo


# Curated: the enums each front-end uses, with their valid members on the
# oldest supported toolkit (GTK 3.24; GTK 4.14 + libadwaita 1.5).
VALID_GTK3 = {
    "Gtk.AccelFlags": {"VISIBLE", "LOCKED", "MASK"},
    "Gtk.ButtonsType": {"NONE", "OK", "CLOSE", "CANCEL", "YES_NO", "OK_CANCEL"},
    "Gtk.FileChooserAction": {"OPEN", "SAVE", "SELECT_FOLDER", "CREATE_FOLDER"},
    "Gtk.IconSize": {
        "INVALID", "MENU", "SMALL_TOOLBAR", "LARGE_TOOLBAR", "BUTTON", "DND", "DIALOG",
    },
    "Gtk.MessageType": {"INFO", "WARNING", "QUESTION", "ERROR", "OTHER"},
    "Gtk.Orientation": {"HORIZONTAL", "VERTICAL"},
    "Gtk.PolicyType": {"ALWAYS", "AUTOMATIC", "NEVER", "EXTERNAL"},
    "Gtk.ResponseType": {
        "NONE", "REJECT", "ACCEPT", "DELETE_EVENT", "OK", "CANCEL",
        "CLOSE", "YES", "NO", "APPLY", "HELP",
    },
    "Gtk.SelectionMode": {"NONE", "SINGLE", "BROWSE", "MULTIPLE"},
    "Gtk.ShadowType": {"NONE", "IN", "OUT", "ETCHED_IN", "ETCHED_OUT"},
    "Gtk.ToolbarStyle": {"ICONS", "TEXT", "BOTH", "BOTH_HORIZ"},
    "Gtk.WindowPosition": {
        "NONE", "CENTER", "MOUSE", "CENTER_ALWAYS", "CENTER_ON_PARENT",
    },
    "Gtk.WrapMode": {"NONE", "CHAR", "WORD", "WORD_CHAR"},
}

VALID_GTK4 = {
    "Gtk.AccessibleProperty": {
        "AUTOCOMPLETE", "DESCRIPTION", "HAS_POPUP", "KEY_SHORTCUTS", "LABEL", "LEVEL",
        "MODAL", "MULTI_LINE", "MULTI_SELECTABLE", "ORIENTATION", "PLACEHOLDER",
        "READ_ONLY", "REQUIRED", "ROLE_DESCRIPTION", "SORT", "VALUE_MAX", "VALUE_MIN",
        "VALUE_NOW", "VALUE_TEXT",
    },
    "Gtk.Align": {"FILL", "START", "END", "CENTER", "BASELINE", "BASELINE_FILL",
                  "BASELINE_CENTER"},
    "Gtk.FilterChange": {"DIFFERENT", "LESS_STRICT", "MORE_STRICT"},
    "Gtk.InputPurpose": {"FREE_FORM", "ALPHA", "DIGITS", "NUMBER", "PHONE", "URL", "EMAIL",
                         "NAME", "PASSWORD", "PIN", "TERMINAL"},
    "Gtk.ListScrollFlags": {"NONE", "FOCUS", "SELECT"},
    "Gtk.Orientation": {"HORIZONTAL", "VERTICAL"},
    "Gtk.PolicyType": {"ALWAYS", "AUTOMATIC", "NEVER", "EXTERNAL"},
    "Gtk.PropagationPhase": {"NONE", "CAPTURE", "BUBBLE", "TARGET"},
    "Gtk.WrapMode": {"NONE", "CHAR", "WORD", "WORD_CHAR"},
    "Adw.ResponseAppearance": {"DEFAULT", "SUGGESTED", "DESTRUCTIVE"},
    "Adw.ToolbarStyle": {"FLAT", "RAISED", "RAISED_BORDER"},
    "Adw.ViewSwitcherPolicy": {"NARROW", "WIDE"},
    "Pango.EllipsizeMode": {"NONE", "START", "MIDDLE", "END"},
    "Pango.FontMask": {"FAMILY", "STYLE", "VARIANT", "WEIGHT", "STRETCH", "SIZE", "GRAVITY",
                       "VARIATIONS"},
    "Pango.Style": {"NORMAL", "OBLIQUE", "ITALIC"},
    "Pango.WrapMode": {"WORD", "CHAR", "WORD_CHAR"},
    "Gio.ApplicationFlags": {"FLAGS_NONE", "DEFAULT_FLAGS", "IS_SERVICE", "IS_LAUNCHER",
                             "HANDLES_OPEN", "HANDLES_COMMAND_LINE", "SEND_ENVIRONMENT",
                             "NON_UNIQUE", "CAN_OVERRIDE_APP_ID", "ALLOW_REPLACEMENT",
                             "REPLACE"},
}

_ENUM_ACCESS = re.compile(r"\b((?:Gtk|Adw|Pango|Gio)\.[A-Z][A-Za-z]+)\.([A-Z][A-Z_]+)\b")


def _check_enum_members() -> list[str]:
    """Every curated ``Ns.Enum.MEMBER`` used in a view module must be real.

    The fake ``gi`` returns a truthy value for *any* attribute, so a typo or
    nonexistent member (e.g. ``Gtk.MessageType.SUCCESS``, which GTK 3 lacks)
    imports cleanly and only fails at runtime; this closes that blind spot.
    An enum missing from the map for its toolkit is reported too, so the map
    grows with the code.
    """
    problems: list[str] = []
    for toolkit, valid in (("gtk3", VALID_GTK3), ("gtk4", VALID_GTK4)):
        for path in sorted(glob.glob(os.path.join(HERE, "qdvc", toolkit, "*.py"))):
            with open(path, encoding="utf-8") as fh:
                src = fh.read()
            name = os.path.basename(path)
            for enum, member in _ENUM_ACCESS.findall(src):
                if enum not in valid:
                    if enum.startswith("Gtk.") or toolkit == "gtk4":
                        problems.append(f"{name}: {enum} is not in the curated "
                                        f"{toolkit.upper()} enum map; add its members")
                elif member not in valid[enum]:
                    problems.append(f"{name}: {enum}.{member} is not a valid "
                                    f"{toolkit.upper()} member")
    return sorted(set(problems))


def _check_gtk4_actions() -> list[str]:
    """Every ``win.*`` action named by the GTK 4 code or SHORTCUTS is installed
    by gtk4_actions.install(), and vice versa nothing installed is unused."""
    from qdvc.ui_prefs import shortcuts_for

    with open(os.path.join(HERE, "qdvc", "gtk4", "gtk4_actions.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    install = next(n for n in tree.body
                   if isinstance(n, ast.FunctionDef) and n.name == "install")
    installed = {"emoji-block"}
    for node in ast.walk(install):
        if isinstance(node, ast.Dict):
            for key in node.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    installed.add(key.value)
    used: set[str] = set()
    for path in glob.glob(os.path.join(HERE, "qdvc", "gtk4", "*.py")):
        with open(path, encoding="utf-8") as fh:
            used |= set(re.findall(r'"win\.([a-z-]+)', fh.read()))
    for s in shortcuts_for("gtk4"):
        if s.action and s.action.startswith("win."):
            used.add(s.action[4:].split("::")[0])
    problems = [f"win.{a} is used but not installed" for a in sorted(used - installed)]
    problems += [f"win.{a} is installed but never used" for a in sorted(installed - used)]
    return problems


def main() -> int:
    _install_fake_gi()
    modules = ["qdvc_nicemail"]
    for package in ("qdvc", "qdvc/gtk3", "qdvc/gtk4"):
        for path in sorted(glob.glob(os.path.join(HERE, package, "*.py"))):
            stem = os.path.splitext(os.path.basename(path))[0]
            dotted = package.replace("/", ".")
            modules.append(dotted if stem == "__init__" else f"{dotted}.{stem}")
    failures = []
    for name in modules:
        try:
            importlib.import_module(name)
        except Exception as exc:  # noqa: BLE001
            failures.append((name, repr(exc)))

    problems = _check_enum_members() + _check_gtk4_actions()

    if failures or problems:
        for name, err in failures:
            print(f"FAIL {name}: {err}")
        for problem in problems:
            print(f"FAIL {problem}")
        return 1
    print(f"import smoke test OK ({len(modules)} modules; enum members and "
          f"GTK 4 actions validated)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
