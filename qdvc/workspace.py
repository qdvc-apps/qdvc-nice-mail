"""Workspace model — files are the database (spec §1, §6).

Layout of a workspace folder:

    <workspace>/
        favourite_emoji.csv        columns: id
        phrases.csv                columns: id,text
        mailsigs/
            signoff.txt            everything before the m-dash
            disclaimer.txt         the disclaimer body
            profiles/
                <name>.txt         one profile per file
"""
from __future__ import annotations

import csv
import os

from .emoji import DEFAULT_FAVOURITE_CHAR, EmojiCatalogue
from .models import Phrase, Profile
from .naming import emoji_id


def _atomic_write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    os.replace(tmp, path)


class Workspace:
    """Viewer/editor over the plaintext files plus an in-memory index."""

    def __init__(self, path: str, catalogue: EmojiCatalogue | None = None) -> None:
        self.path = os.path.abspath(path)
        self.catalogue = catalogue or EmojiCatalogue()
        self.favourite_ids: list[str] = []
        self.favourite_labels: dict[str, str] = {}
        self.favourite_chars: dict[str, str] = {}  # id -> glyph, for custom emoji
        self.phrases: list[Phrase] = []
        self.profiles: list[Profile] = []
        self.scan()

    # ---- paths -----------------------------------------------------------
    @property
    def favourites_csv(self) -> str:
        return os.path.join(self.path, "favourite_emoji.csv")

    @property
    def phrases_csv(self) -> str:
        return os.path.join(self.path, "phrases.csv")

    @property
    def mailsigs_dir(self) -> str:
        return os.path.join(self.path, "mailsigs")

    @property
    def profiles_dir(self) -> str:
        return os.path.join(self.mailsigs_dir, "profiles")

    @property
    def signoff_txt(self) -> str:
        return os.path.join(self.mailsigs_dir, "signoff.txt")

    @property
    def disclaimer_txt(self) -> str:
        return os.path.join(self.mailsigs_dir, "disclaimer.txt")

    # ---- scaffolding -----------------------------------------------------
    def ensure_scaffold(self) -> None:
        """Create the expected files/folders with sensible defaults if absent."""
        os.makedirs(self.profiles_dir, exist_ok=True)

        if not os.path.exists(self.favourites_csv):
            # Seed the one required default favourite (😊).
            fav = next(
                (e for e in self.catalogue.all() if e.char == DEFAULT_FAVOURITE_CHAR),
                None,
            )
            fid = fav.id if fav else emoji_id("smiling face with smiling eyes")
            self._write_favourites([fid])

        if not os.path.exists(self.phrases_csv):
            self._write_phrases([
                Phrase(id="thanks", text="Thanks very much for your help."),
                Phrase(id="follow_up", text="Just following up on my previous email."),
            ])

        if not os.path.exists(self.signoff_txt):
            _atomic_write(self.signoff_txt, "Kind regards,\n\nJohn Smith\n")
        if not os.path.exists(self.disclaimer_txt):
            _atomic_write(self.disclaimer_txt, "a disclaimer text goes here\n")
        default_profile = os.path.join(self.profiles_dir, "default.txt")
        if not os.listdir(self.profiles_dir):
            _atomic_write(
                default_profile,
                "John Smith\n"
                "Specialist and Superhero\n"
                "Data by day, defeating villains by night\n",
            )

    # ---- load ------------------------------------------------------------
    def scan(self) -> None:
        self.favourite_ids = self._read_favourites()
        self.phrases = self._read_phrases()
        self.profiles = self._read_profiles()

    def _read_favourites(self) -> list[str]:
        ids: list[str] = []
        self.favourite_labels = {}
        self.favourite_chars = {}
        if not os.path.exists(self.favourites_csv):
            return ids
        with open(self.favourites_csv, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                fid = (row.get("id") or "").strip()
                if fid and fid not in ids:
                    ids.append(fid)
                    label = (row.get("label") or "").strip()
                    if label:
                        self.favourite_labels[fid] = label
                    # A glyph is stored only for custom (pasted) emoji that
                    # are not in the Unicode-name-derived catalogue.
                    char = (row.get("char") or "").strip()
                    if char:
                        self.favourite_chars[fid] = char
        return ids

    def _read_phrases(self) -> list[Phrase]:
        out: list[Phrase] = []
        if not os.path.exists(self.phrases_csv):
            return out
        with open(self.phrases_csv, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                pid = (row.get("id") or "").strip()
                text = (row.get("text") or "").strip()
                if pid:
                    out.append(Phrase(id=pid, text=text))
        return out

    def _read_profiles(self) -> list[Profile]:
        out: list[Profile] = []
        if not os.path.isdir(self.profiles_dir):
            return out
        for fn in sorted(os.listdir(self.profiles_dir)):
            if not fn.endswith(".txt"):
                continue
            full = os.path.join(self.profiles_dir, fn)
            try:
                with open(full, encoding="utf-8") as fh:
                    lines = [ln.rstrip("\n") for ln in fh.read().splitlines()]
            except OSError:
                continue
            # trim trailing blank lines
            while lines and not lines[-1].strip():
                lines.pop()
            out.append(Profile(name=os.path.splitext(fn)[0], lines=lines))
        return out

    def read_text_file(self, path: str) -> str:
        try:
            with open(path, encoding="utf-8") as fh:
                return fh.read()
        except OSError:
            return ""

    @property
    def signoff(self) -> str:
        return self.read_text_file(self.signoff_txt)

    @property
    def disclaimer(self) -> str:
        return self.read_text_file(self.disclaimer_txt)

    # ---- favourites mutation --------------------------------------------
    def _write_favourites(self, ids: list[str]) -> None:
        import io
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id", "label", "char"])
        for fid in ids:
            writer.writerow([
                fid,
                self.favourite_labels.get(fid, ""),
                self.favourite_chars.get(fid, ""),
            ])
        _atomic_write(self.favourites_csv, buf.getvalue())

    def add_favourite(self, emoji_uid: str) -> bool:
        if emoji_uid in self.favourite_ids:
            return False
        self.favourite_ids.append(emoji_uid)
        self._write_favourites(self.favourite_ids)
        return True

    def add_custom_favourite(self, char: str) -> str | None:
        """Favourite an arbitrary pasted glyph not in the catalogue.

        Returns the assigned id, or None if the glyph is blank or already a
        favourite. The glyph is persisted in the `char` column so it survives
        reload even though it has no Unicode-name-derived catalogue entry.
        """
        char = (char or "").strip()
        if not char:
            return None
        em = self.catalogue.make_custom(char)
        if em.id in self.favourite_ids:
            return None
        self.favourite_ids.append(em.id)
        self.favourite_chars[em.id] = char
        self._write_favourites(self.favourite_ids)
        return em.id

    def remove_favourite(self, emoji_uid: str) -> bool:
        if emoji_uid not in self.favourite_ids:
            return False
        self.favourite_ids.remove(emoji_uid)
        self.favourite_labels.pop(emoji_uid, None)
        self.favourite_chars.pop(emoji_uid, None)
        self._write_favourites(self.favourite_ids)
        return True

    def set_favourite_label(self, emoji_uid: str, label: str) -> None:
        """Set (or clear) the user label for a favourited emoji."""
        if emoji_uid not in self.favourite_ids:
            return
        label = (label or "").strip()
        if label:
            self.favourite_labels[emoji_uid] = label
        else:
            self.favourite_labels.pop(emoji_uid, None)
        self._write_favourites(self.favourite_ids)

    def favourite_label(self, emoji_uid: str) -> str:
        return self.favourite_labels.get(emoji_uid, "")

    def move_favourite(self, emoji_uid: str, delta: int) -> bool:
        """Move a favourite up (-1) or down (+1) in the list. Returns moved."""
        if emoji_uid not in self.favourite_ids:
            return False
        i = self.favourite_ids.index(emoji_uid)
        j = i + delta
        if j < 0 or j >= len(self.favourite_ids):
            return False
        self.favourite_ids[i], self.favourite_ids[j] = (
            self.favourite_ids[j], self.favourite_ids[i]
        )
        self._write_favourites(self.favourite_ids)
        return True

    def resolve_emoji(self, fid: str):
        """Return the Emoji for a favourite id, catalogue or custom."""
        em = self.catalogue.get(fid)
        if em is not None:
            return em
        char = self.favourite_chars.get(fid)
        if char:
            return self.catalogue.make_custom(char)
        return None

    def custom_favourites(self) -> list:
        """Custom (pasted) favourite emoji, in favourites order."""
        out = []
        for fid in self.favourite_ids:
            if self.catalogue.get(fid) is None:
                em = self.resolve_emoji(fid)
                if em is not None:
                    out.append(em)
        return out

    def favourite_emoji(self):
        out = []
        for fid in self.favourite_ids:
            em = self.resolve_emoji(fid)
            if em is not None:
                out.append(em)
        return out

    # ---- phrases mutation ------------------------------------------------
    def _write_phrases(self, phrases: list[Phrase]) -> None:
        import io
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id", "text"])
        for p in phrases:
            writer.writerow([p.id, p.text])
        _atomic_write(self.phrases_csv, buf.getvalue())
        self.phrases = list(phrases)

    def _unique_phrase_id(self, base: str) -> str:
        from .naming import emoji_id as slug  # same slug rule
        base = slug(base) or "phrase"
        existing = {p.id for p in self.phrases}
        if base not in existing:
            return base
        n = 2
        while f"{base}_{n}" in existing:
            n += 1
        return f"{base}_{n}"

    def add_phrase(self, text: str) -> Phrase:
        pid = self._unique_phrase_id(text[:32])
        p = Phrase(id=pid, text=text.strip())
        self._write_phrases(self.phrases + [p])
        return p

    def edit_phrase(self, pid: str, text: str) -> None:
        for p in self.phrases:
            if p.id == pid:
                p.text = text.strip()
                break
        self._write_phrases(self.phrases)

    def delete_phrase(self, pid: str) -> None:
        self._write_phrases([p for p in self.phrases if p.id != pid])

    def move_phrase(self, pid: str, delta: int) -> bool:
        """Move a phrase up (-1) or down (+1) in the list. Returns moved."""
        ids = [p.id for p in self.phrases]
        if pid not in ids:
            return False
        i = ids.index(pid)
        j = i + delta
        if j < 0 or j >= len(self.phrases):
            return False
        reordered = list(self.phrases)
        reordered[i], reordered[j] = reordered[j], reordered[i]
        self._write_phrases(reordered)
        return True

    # ---- profiles --------------------------------------------------------
    def get_profile(self, name: str | None) -> Profile | None:
        if name is None:
            return self.profiles[0] if self.profiles else None
        for p in self.profiles:
            if p.name == name:
                return p
        return self.profiles[0] if self.profiles else None

    # ---- validation ------------------------------------------------------
    def validate(self) -> dict[str, list[str]]:
        problems: dict[str, list[str]] = {"orphan_favourites": [], "missing_files": []}
        for fid in self.favourite_ids:
            # A favourite is an orphan only if it is neither in the catalogue
            # nor a custom glyph with a stored character.
            if self.catalogue.get(fid) is None and not self.favourite_chars.get(fid):
                problems["orphan_favourites"].append(fid)
        for label, path in (
            ("signoff.txt", self.signoff_txt),
            ("disclaimer.txt", self.disclaimer_txt),
        ):
            if not os.path.exists(path):
                problems["missing_files"].append(label)
        return problems
