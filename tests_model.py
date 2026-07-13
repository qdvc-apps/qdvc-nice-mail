"""Pure-model tests — no display required (spec §13)."""
import os
import tempfile
import unittest

from qdvc.emoji import DEFAULT_FAVOURITE_CHAR, EmojiCatalogue, accepts_skin_tone
from qdvc.mailsig import assemble_signature
from qdvc.naming import MSGREF_ALPHABET, MSGREF_LENGTH, emoji_id, generate_message_ref
from qdvc.workspace import Workspace


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


if __name__ == "__main__":
    unittest.main()
