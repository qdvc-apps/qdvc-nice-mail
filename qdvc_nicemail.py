#!/usr/bin/env python3
"""QDVC Nice Mail — thin entry point / backend dispatcher (spec §3).

    python3 qdvc_nicemail.py [--gtk3 | --gtk4] [WORKSPACE-FOLDER]

Backend selection order: --gtk3/--gtk4 flag -> config ui_backend -> gtk3.
No GTK is imported until the backend is chosen, so only that front-end loads.

Fallbacks (each prints a note to stderr):
- GTK 4 chosen but GTK 4 / libadwaita >= 1.5 is not available -> GTK 3.
- GTK 3 chosen by the config or the default (not by --gtk3) but GTK 3 is not
  installed, while GTK 4 is -> GTK 4.
"""
from __future__ import annotations

import os
import sys

MIN_ADW = (1, 5)
PROG = "qdvc-nicemail"
# Set when re-executing for a fallback, so a fallback never loops.
_FALLBACK_ENV = "QDVC_NICEMAIL_FALLBACK"

INSTALL_HINT = (
    "Install one of the two front-ends' dependencies:\n"
    "  GTK 4 (GNOME): sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 python3-yaml\n"
    "  GTK 3 (MATE):  sudo apt install python3-gi gir1.2-gtk-3.0 python3-yaml\n"
    "  (Fedora: python3-gobject gtk4 libadwaita gtk3 python3-pyyaml)"
)


def _note(message: str) -> None:
    sys.stderr.write(f"{PROG}: {message}\n")


def _select_backend(argv: list[str]) -> tuple[str, bool, list[str]]:
    """(backend, chosen explicitly by a flag, the other arguments)."""
    backend = None
    rest: list[str] = []
    for arg in argv[1:]:
        if arg == "--gtk3":
            backend = "gtk3"
        elif arg == "--gtk4":
            backend = "gtk4"
        else:
            rest.append(arg)

    explicit = backend is not None
    if backend is None:
        try:
            from qdvc.config import Config
            backend = Config().ui_backend
        except Exception:
            backend = "gtk3"

    return backend, explicit, rest


def toolkit_available(backend: str) -> bool:
    """Whether a front-end's typelibs are installed, without loading them.

    Loading a namespace pins its version for the whole process (GTK 3 cannot
    be loaded after GTK 4), so this only enumerates what is installed.
    """
    try:
        import gi
    except ImportError:
        return False
    repo_cls = getattr(gi, "Repository", None)
    if repo_cls is None:  # very old PyGObject: let the import decide
        return True
    repo = repo_cls.get_default()
    if backend == "gtk4":
        return "4.0" in repo.enumerate_versions("Gtk") and "1" in repo.enumerate_versions("Adw")
    return "3.0" in repo.enumerate_versions("Gtk")


def _reexec(flag: str, rest: list[str]) -> int:
    """Start again with another front-end (GTK is already loaded here)."""
    os.environ[_FALLBACK_ENV] = "1"
    script = os.path.abspath(__file__)
    os.execv(sys.executable, [sys.executable, script, flag, *rest])
    return 1  # not reached


def _run_gtk4(argv: list[str], rest: list[str]) -> int | None:
    """Run the GTK 4 front-end, or return None if it cannot start here."""
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        from gi.repository import Adw
    except (ImportError, ValueError) as exc:
        _note(f"GTK 4 / libadwaita could not be loaded ({exc}).")
        return None
    found = (Adw.get_major_version(), Adw.get_minor_version())
    if found < MIN_ADW:
        _note("libadwaita %d.%d or later is needed for the GTK 4 front-end (found %d.%d)."
              % (*MIN_ADW, *found))
        if toolkit_available("gtk3") and not os.environ.get(_FALLBACK_ENV):
            _note("falling back to GTK 3.")
            return _reexec("--gtk3", rest)
        return 1
    from qdvc.gtk4.gtk4_app import main as gtk4_main
    return gtk4_main(argv)


def main() -> int:
    if sys.version_info < (3, 10):
        _note("Python 3.10 or later is needed.")
        return 1
    backend, explicit, rest = _select_backend(sys.argv)
    have4, have3 = toolkit_available("gtk4"), toolkit_available("gtk3")
    if not (have4 or have3):
        _note("neither GTK 4 + libadwaita nor GTK 3 is available to Python.\n"
              + INSTALL_HINT)
        return 1

    if backend == "gtk4" and not have4:
        _note("the GTK 4 front-end needs GTK 4 and libadwaita; falling back to GTK 3.")
        backend = "gtk3"
    elif backend == "gtk3" and not have3 and have4 and not explicit:
        _note("GTK 3 is not installed; using the GTK 4 front-end.")
        backend = "gtk4"

    # Preserve argv[0] (GApplication expects a program name there).
    backend_argv = [sys.argv[0], *rest]

    if backend == "gtk4":
        result = _run_gtk4(backend_argv, rest)
        if result is not None:
            return result
        # Gtk 4.0 may now be pinned in this process: start afresh on GTK 3.
        if have3 and not os.environ.get(_FALLBACK_ENV):
            _note("falling back to GTK 3.")
            return _reexec("--gtk3", rest)

    if not have3:
        _note("GTK 3 is not available.\n" + INSTALL_HINT)
        return 1
    from qdvc.gtk3.gtk3_app import main as gtk3_main
    return gtk3_main(backend_argv)


if __name__ == "__main__":
    raise SystemExit(main())
