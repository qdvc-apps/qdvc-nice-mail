"""Mail-signature assembly (pure)."""
from __future__ import annotations

from .models import Profile

MDASH = "\u2014"  # —


def assemble_signature(
    signoff: str,
    profile: Profile | None,
    disclaimer: str,
    include_disclaimer: bool,
    message_ref: str,
    ref_only: bool = False,
) -> str:
    """Assemble the plaintext mail signature.

    Layout:
        <signoff>


        —

        <profile block>

        [Disclaimer: <disclaimer>]

        Message ref. <ref>

    In `ref_only` mode the signature is just the m-dash, a blank line, and the
    message ref line — nothing else:

        —

        Message ref. <ref>
    """
    if ref_only:
        return f"{MDASH}\n\nMessage ref. {message_ref}\n"

    parts: list[str] = []

    signoff = (signoff or "").rstrip("\n")
    if signoff:
        parts.append(signoff)

    # An extra blank line precedes the m-dash (blocks are otherwise separated
    # by a single blank line). Prepending a newline to the m-dash part yields
    # two blank lines between the signoff and the m-dash.
    parts.append("\n" + MDASH)

    if profile is not None and profile.block.strip():
        parts.append(profile.block.rstrip("\n"))

    if include_disclaimer:
        d = (disclaimer or "").strip()
        if d:
            parts.append(f"Disclaimer: {d}")

    parts.append(f"Message ref. {message_ref}")

    # Blank line between every block.
    return "\n\n".join(parts) + "\n"
