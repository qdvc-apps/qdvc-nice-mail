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


def main() -> int:
    _install_fake_gi()
    modules = [
        "qdvc",
        "qdvc.config",
        "qdvc.naming",
        "qdvc.emoji",
        "qdvc.models",
        "qdvc.mailsig",
        "qdvc.workspace",
        "qdvc.platform_utils",
        "qdvc.ui_prefs",
        "qdvc.gtk3.gtk3_app",
        "qdvc.gtk3.gtk3_main_window",
        "qdvc.gtk3.gtk3_emoji_tab",
        "qdvc.gtk3.gtk3_phrases_tab",
        "qdvc.gtk3.gtk3_signature_tab",
        "qdvc.gtk3.gtk3_preferences",
        "qdvc.gtk3.gtk3_shortcuts",
    ]
    failures = []
    for name in modules:
        try:
            importlib.import_module(name)
        except Exception as exc:  # noqa: BLE001
            failures.append((name, repr(exc)))

    if failures:
        for name, err in failures:
            print(f"FAIL {name}: {err}")
        return 1
    print(f"import smoke test OK ({len(modules)} modules)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
