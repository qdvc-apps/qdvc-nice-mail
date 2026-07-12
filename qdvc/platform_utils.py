"""Launch system applications (pure)."""
from __future__ import annotations

import os
import subprocess
import sys


def open_with_default_app(path: str) -> None:
    try:
        if sys.platform.startswith("darwin"):
            subprocess.Popen(["open", path])
        elif os.name == "nt":  # pragma: no cover
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


def open_with_text_editor(path: str) -> None:
    try:
        if sys.platform.startswith("darwin"):
            subprocess.Popen(["open", "-t", path])
        elif os.name == "nt":  # pragma: no cover
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


def reveal_in_file_manager(path: str, template: str | None = None) -> None:
    directory = path if os.path.isdir(path) else os.path.dirname(path)
    try:
        if template:
            cmd = template.format(dir=directory, file=path)
            subprocess.Popen(cmd, shell=True)
        elif sys.platform.startswith("darwin"):
            subprocess.Popen(["open", directory])
        elif os.name == "nt":  # pragma: no cover
            os.startfile(directory)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", directory])
    except Exception:
        pass
