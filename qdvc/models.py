"""Domain records (pure)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Phrase:
    id: str
    text: str


@dataclass
class Profile:
    """A mail-signature profile loaded from mailsigs/profiles/<name>.txt."""
    name: str          # filename stem, used as the dropdown label
    lines: list[str]   # the block that appears after the m-dash

    @property
    def block(self) -> str:
        return "\n".join(self.lines)
