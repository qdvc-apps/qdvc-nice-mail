"""Note-to-Self EML assembly (pure).

Builds an RFC 5322 message (.eml) that a user sends to themselves: the same
address appears as both From and To. The body is the user's plaintext followed
by two blank lines, an m-dash, a blank line, and the message-ref line — i.e.
the same trailer the Signature tab produces in "Ref Only" mode.
"""
from __future__ import annotations

from datetime import datetime
from email.message import EmailMessage
from email.utils import format_datetime

from .mailsig import MDASH


def note_body(text: str, message_ref: str) -> str:
    """Body text: <user text>, two blank lines, m-dash, blank line, ref line."""
    body = (text or "").rstrip("\n")
    trailer = f"{MDASH}\n\nMessage ref. {message_ref}\n"
    return f"{body}\n\n\n{trailer}"


def build_note_eml(
    address: str,
    subject: str,
    text: str,
    message_ref: str,
    when: datetime | None = None,
) -> bytes:
    """Assemble a self-addressed plaintext .eml as bytes.

    `address` is used for both From and To. `when` defaults to now (local time
    with the system tz offset); pass one for deterministic output in tests.
    """
    msg = EmailMessage()
    addr = (address or "").strip()
    msg["From"] = addr
    msg["To"] = addr
    msg["Subject"] = (subject or "").strip()
    if when is None:
        when = datetime.now().astimezone()
    msg["Date"] = format_datetime(when)
    msg.set_content(note_body(text, message_ref))
    return msg.as_bytes()


def default_note_filename(message_ref: str, when: datetime | None = None) -> str:
    """Filename: yyyy-mm-dd-message-ref-<ref>.eml (today's date)."""
    if when is None:
        when = datetime.now().astimezone()
    return f"{when:%Y-%m-%d}-message-ref-{message_ref}.eml"
