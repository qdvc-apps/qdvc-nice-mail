"""Pure-model tests — no display required (spec §13)."""
import os
import tempfile
import unittest

from qdvc.emoji import DEFAULT_FAVOURITE_CHAR, EmojiCatalogue, accepts_skin_tone
from qdvc.mailsig import assemble_signature
from qdvc.naming import MSGREF_ALPHABET, MSGREF_LENGTH, emoji_id, generate_message_ref
from qdvc.note import build_note_eml, default_note_filename, note_body
from qdvc import ui_prefs
from qdvc.workspace import Workspace, looks_like_workspace


class NamingTests(unittest.TestCase):
    def test_snake_case_id(self):
        self.assertEqual(emoji_id("GRINNING FACE"), "grinning_face")
        self.assertEqual(emoji_id("FACE WITH TEARS OF JOY"), "face_with_tears_of_joy")
        self.assertEqual(emoji_id("A+B  C"), "a_b_c")

    def test_message_ref(self):
        ref = generate_message_ref()
        self.assertEqual(len(ref), MSGREF_LENGTH)
        self.assertTrue(all(c in MSGREF_ALPHABET for c in ref))


class EmojiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = EmojiCatalogue()

    def test_ids_unique(self):
        ids = [e.id for e in self.cat.all()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_default_favourite_present(self):
        self.assertTrue(any(e.char == DEFAULT_FAVOURITE_CHAR for e in self.cat.all()))

    def test_skin_tone(self):
        wave = next(e for e in self.cat.all() if e.char == "\U0001F44B")
        self.assertTrue(accepts_skin_tone(wave.char))
        self.assertNotEqual(wave.display("dark"), wave.char)

    def test_search(self):
        self.assertTrue(self.cat.search("grinning"))
        self.assertEqual(self.cat.search(""), self.cat.all())


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.ws = Workspace(self.dir)
        self.ws.ensure_scaffold()
        self.ws.scan()

    def test_scaffold_files(self):
        self.assertTrue(os.path.exists(self.ws.favourites_csv))
        self.assertTrue(os.path.exists(self.ws.phrases_csv))
        self.assertTrue(os.path.exists(self.ws.signoff_txt))
        self.assertTrue(os.path.exists(self.ws.disclaimer_txt))
        self.assertTrue(self.ws.profiles)

    def test_favourites_roundtrip(self):
        wave = next(e for e in self.ws.catalogue.all() if e.char == "\U0001F44B")
        self.assertTrue(self.ws.add_favourite(wave.id))
        self.assertFalse(self.ws.add_favourite(wave.id))  # dedup
        reloaded = Workspace(self.dir)
        self.assertIn(wave.id, reloaded.favourite_ids)
        self.ws.remove_favourite(wave.id)
        self.assertNotIn(wave.id, Workspace(self.dir).favourite_ids)

    def test_phrase_crud(self):
        p = self.ws.add_phrase("Please find the attached file.")
        self.assertIn(p, self.ws.phrases)
        self.ws.edit_phrase(p.id, "Please see the attached file.")
        self.assertEqual(next(x for x in self.ws.phrases if x.id == p.id).text,
                         "Please see the attached file.")
        self.ws.delete_phrase(p.id)
        self.assertNotIn(p.id, [x.id for x in self.ws.phrases])

    def test_signature_format(self):
        prof = self.ws.get_profile(None)
        sig = assemble_signature(self.ws.signoff, prof, self.ws.disclaimer, True, "YyM4mRnjHQ")
        self.assertIn("Kind regards,", sig)
        self.assertIn("\u2014", sig)
        self.assertIn("Disclaimer:", sig)
        self.assertTrue(sig.rstrip().endswith("Message ref. YyM4mRnjHQ"))
        # Two blank lines precede the m-dash line.
        self.assertIn("\n\n\n\u2014\n", sig)

    def test_favourite_labels_and_reorder(self):
        cat = self.ws.catalogue
        wave = next(e for e in cat.all() if e.char == "\U0001F44B")
        thumbs = next(e for e in cat.all() if e.char == "\U0001F44D")
        self.ws.add_favourite(wave.id)
        self.ws.add_favourite(thumbs.id)
        self.ws.set_favourite_label(wave.id, "friendly wave")
        self.assertEqual(self.ws.favourite_label(wave.id), "friendly wave")
        # Reorder: move thumbs up past wave.
        before = list(self.ws.favourite_ids)
        self.assertTrue(self.ws.move_favourite(thumbs.id, -1))
        self.assertNotEqual(before, self.ws.favourite_ids)
        # Label persists across reload.
        reloaded = Workspace(self.dir)
        self.assertEqual(reloaded.favourite_label(wave.id), "friendly wave")

    def test_phrase_reorder(self):
        ids_before = [p.id for p in self.ws.phrases]
        last = ids_before[-1]
        self.assertTrue(self.ws.move_phrase(last, -1))
        self.assertEqual(self.ws.phrases[-2].id, last)

    def test_custom_favourite(self):
        mending = "\u2764\ufe0f\u200d\U0001fa79"  # ❤️‍🩹
        new_id = self.ws.add_custom_favourite(mending)
        self.assertIsNotNone(new_id)
        self.assertIn(new_id, self.ws.favourite_ids)
        # Adding the same glyph again is a no-op.
        self.assertIsNone(self.ws.add_custom_favourite(mending))
        # Resolvable as a custom emoji, and skin tone never applies.
        em = self.ws.resolve_emoji(new_id)
        self.assertTrue(em.custom)
        self.assertEqual(em.char, mending)
        self.assertEqual(em.display("dark"), mending)
        # Appears among custom favourites and is not an orphan.
        self.assertIn(new_id, [e.id for e in self.ws.custom_favourites()])
        self.assertEqual(self.ws.validate()["orphan_favourites"], [])
        # Glyph + label persist across reload.
        self.ws.set_favourite_label(new_id, "mending")
        reloaded = Workspace(self.dir)
        self.assertEqual(reloaded.favourite_chars.get(new_id), mending)
        self.assertEqual(reloaded.favourite_label(new_id), "mending")
        self.assertTrue(reloaded.resolve_emoji(new_id).custom)

    def test_old_two_column_favourites_still_load(self):
        # A favourites file predating the `char` column must still read.
        import os
        with open(self.ws.favourites_csv, "w", encoding="utf-8", newline="") as fh:
            fh.write("id,label\nsmiling_face_with_smiling_eyes,hi\n")
        reloaded = Workspace(self.dir)
        self.assertEqual(reloaded.favourite_ids, ["smiling_face_with_smiling_eyes"])
        self.assertEqual(reloaded.favourite_label("smiling_face_with_smiling_eyes"), "hi")

    def test_signature_without_disclaimer(self):
        prof = self.ws.get_profile(None)
        sig = assemble_signature(self.ws.signoff, prof, self.ws.disclaimer, False, "ABC1234567")
        self.assertNotIn("Disclaimer:", sig)

    def test_signature_ref_only(self):
        prof = self.ws.get_profile(None)
        sig = assemble_signature(
            self.ws.signoff, prof, self.ws.disclaimer, True, "ABC1234567", ref_only=True
        )
        # Only the m-dash, a blank line, and the message ref line.
        self.assertEqual(sig, "\u2014\n\nMessage ref. ABC1234567\n")
        self.assertNotIn("Kind regards", sig)
        self.assertNotIn("Disclaimer:", sig)


class NoteEmailTests(unittest.TestCase):
    def test_note_body_trailer(self):
        body = note_body("Buy milk", "BeFGzLRHNX")
        # user text, two blank lines, m-dash, blank line, ref line.
        self.assertEqual(body, "Buy milk\n\n\n\u2014\n\nMessage ref. BeFGzLRHNX\n")

    def test_eml_headers_and_self_addressing(self):
        from datetime import datetime, timezone, timedelta
        when = datetime(2026, 7, 13, 14, 30, tzinfo=timezone(timedelta(hours=1)))
        raw = build_note_eml("me@example.com", "Reminder", "Text", "ABC1234567", when=when)
        self.assertIsInstance(raw, bytes)
        text = raw.decode("utf-8")
        self.assertIn("From: me@example.com", text)
        self.assertIn("To: me@example.com", text)
        self.assertIn("Subject: Reminder", text)
        self.assertIn("Date: Mon, 13 Jul 2026 14:30:00 +0100", text)
        self.assertIn("Message ref. ABC1234567", text)

    def test_default_filename(self):
        from datetime import datetime, timezone
        when = datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc)
        self.assertEqual(
            default_note_filename("ABC1234567", when=when),
            "2026-01-05-message-ref-ABC1234567.eml",
        )


class SharedUiRulesTests(unittest.TestCase):
    """The toolkit-independent rules both front-ends call (ui_prefs)."""

    @classmethod
    def setUpClass(cls):
        cls.catalogue = EmojiCatalogue()

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.ws = Workspace(self.dir, catalogue=self.catalogue)
        self.ws.ensure_scaffold()
        self.ws.scan()

    def test_emoji_blocks(self):
        favs = ui_prefs.emoji_block_items(self.ws, "favourites")
        self.assertEqual([e.char for e in favs], [DEFAULT_FAVOURITE_CHAR])
        custom = self.ws.add_custom_favourite("❤️‍\U0001fa79")
        everything = ui_prefs.emoji_block_items(self.ws, "all")
        # Custom favourites come first in All Emoji, then the catalogue.
        self.assertEqual(everything[0].id, custom)
        self.assertEqual(len(everything), len(self.catalogue.all()) + 1)

    def test_emoji_search_matches_name_id_and_label(self):
        wave = next(e for e in self.catalogue.all() if e.char == "\U0001F44B")
        self.ws.add_favourite(wave.id)
        self.ws.set_favourite_label(wave.id, "Hello there")
        self.assertTrue(ui_prefs.emoji_matches(self.ws, wave, "WAVING"))
        self.assertTrue(ui_prefs.emoji_matches(self.ws, wave, "waving_hand"))
        self.assertTrue(ui_prefs.emoji_matches(self.ws, wave, "hello"))
        self.assertTrue(ui_prefs.emoji_matches(self.ws, wave, "  "))
        self.assertFalse(ui_prefs.emoji_matches(self.ws, wave, "pizza"))
        self.assertEqual([e.id for e in ui_prefs.emoji_listing(self.ws, "favourites", "hello")],
                         [wave.id])

    def test_custom_emoji_display_name(self):
        custom = self.ws.resolve_emoji(self.ws.add_custom_favourite("\U0001F600‍"))
        self.assertIn(ui_prefs.CUSTOM_EMOJI_NOTE, ui_prefs.emoji_display_name(custom))
        smile = self.catalogue.all()[0]
        self.assertEqual(ui_prefs.emoji_display_name(smile), smile.name)

    def test_phrase_listing_is_alphabetical_and_filtered(self):
        self.ws.add_phrase("apples are nice")
        texts = [p.text for p in ui_prefs.phrase_listing(self.ws)]
        self.assertEqual(texts, sorted(texts, key=str.lower))
        self.assertEqual([p.text for p in ui_prefs.phrase_listing(self.ws, "APPLE")],
                         ["apples are nice"])

    def test_shortcuts_table(self):
        for toolkit in ("gtk3", "gtk4"):
            accels = [a for s in ui_prefs.shortcuts_for(toolkit) for a in s.accels]
            self.assertEqual(len(accels), len(set(accels)), f"duplicate accel in {toolkit}")
        self.assertTrue(all(s.section in ui_prefs.SHORTCUT_SECTIONS for s in ui_prefs.SHORTCUTS))
        gtk3_titles = [t for t, _a in __import__(
            "qdvc.gtk3.gtk3_shortcuts", fromlist=["x"]).shortcut_rows()]
        self.assertNotIn("Keyboard shortcuts", gtk3_titles)  # GTK 4 only
        # Ctrl+C must not be an application accelerator in GTK 4 (it would
        # pre-empt copying text in a search box); it is a bubble shortcut.
        self.assertNotIn("win.copy", ui_prefs.accelerators("gtk4"))
        self.assertEqual(ui_prefs.accelerators("gtk4", bubble=True), {"win.copy": ["<Primary>c"]})
        pages = {s.action.split("::")[1] for s in ui_prefs.SHORTCUTS
                 if s.action and s.action.startswith("win.show-page::")}
        self.assertEqual(pages, set(ui_prefs.PAGE_IDS))

    def test_font_css(self):
        self.assertEqual(ui_prefs.font_css(".x", None, None), "")
        css = ui_prefs.font_css(".x text", 'My "Odd" Font, Mono', 10.5, 700, True)
        self.assertIn('font-family: "My \\"Odd\\" Font", "Mono";', css)
        self.assertIn("font-size: 10.5pt;", css)
        self.assertIn("font-weight: 700;", css)
        self.assertIn("font-style: italic;", css)
        self.assertNotIn("font-weight", ui_prefs.font_css(".x", "Sans", 11, 400))

    def test_skin_tone_sample(self):
        self.assertEqual(ui_prefs.skin_tone_sample("none"), "\U0001F44B")
        self.assertEqual(ui_prefs.skin_tone_sample("dark"), "\U0001F44B\U0001F3FF")

    def test_looks_like_workspace(self):
        empty = tempfile.mkdtemp()
        self.assertFalse(looks_like_workspace(empty))
        self.assertTrue(looks_like_workspace(self.dir))
        os.makedirs(os.path.join(empty, "mailsigs"))
        self.assertTrue(looks_like_workspace(empty))


class DispatcherTests(unittest.TestCase):
    """qdvc_nicemail.py chooses a backend before importing any GTK."""

    def setUp(self):
        self.old = os.environ.get("XDG_CONFIG_HOME")
        os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp()
        import qdvc_nicemail
        self.d = qdvc_nicemail

    def tearDown(self):
        if self.old is None:
            os.environ.pop("XDG_CONFIG_HOME", None)
        else:
            os.environ["XDG_CONFIG_HOME"] = self.old

    def test_flag_wins_and_is_consumed(self):
        self.assertEqual(self.d._select_backend(["x", "/ws", "--gtk4"]), ("gtk4", True, ["/ws"]))
        self.assertEqual(self.d._select_backend(["x", "--gtk3"]), ("gtk3", True, []))

    def test_config_then_default(self):
        self.assertEqual(self.d._select_backend(["x"]), ("gtk3", False, []))
        from qdvc.config import Config
        Config().set("ui_backend", "GTK4")
        self.assertEqual(self.d._select_backend(["x"]), ("gtk4", False, []))
        Config().set("ui_backend", "qt")  # unrecognised -> gtk3
        self.assertEqual(self.d._select_backend(["x"]), ("gtk3", False, []))


if __name__ == "__main__":
    unittest.main()
