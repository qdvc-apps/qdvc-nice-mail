#!/usr/bin/env python3
"""QDVC Nice Mail — thin entry point / backend dispatcher (spec §3).

Backend selection order: --gtk3/--gtk4 flag -> config ui_backend -> gtk3.
GTK 4 is not implemented at this stage; a request for it prints a note and
falls back to GTK 3.
"""
from __future__ import annotations

import sys


def _select_backend(argv: list[str]) -> tuple[str, list[str]]:
    backend = None
    rest: list[str] = []
    for arg in argv[1:]:
        if arg == "--gtk3":
            backend = "gtk3"
        elif arg == "--gtk4":
            backend = "gtk4"
        else:
            rest.append(arg)

    if backend is None:
        try:
            from qdvc.config import Config
            backend = Config().ui_backend
        except Exception:
            backend = "gtk3"

    return backend, rest


def main() -> int:
    backend, rest = _select_backend(sys.argv)

    if backend == "gtk4":
        sys.stderr.write(
            "qdvc-nicemail: GTK 4 backend is not implemented yet; "
            "falling back to GTK 3.\n"
        )
        backend = "gtk3"

    # Preserve argv[0] (GApplication expects a program name there).
    backend_argv = [sys.argv[0], *rest]

    from qdvc.gtk3.gtk3_app import main as gtk3_main
    return gtk3_main(backend_argv)


if __name__ == "__main__":
    raise SystemExit(main())
