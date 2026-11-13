# -*- coding: UTF-8 -*-
"""Translation coverage: no source string may be missing from a locale."""

import unittest

import support


class TestTranslations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.strings = support.source_strings()
        cls.locales = support.locale_dirs()

    def test_there_is_at_least_one_locale(self):
        self.assertTrue(self.locales, "no locale directory was found")

    def test_every_source_string_exists_in_every_po(self):
        self.assertTrue(self.strings, "no translatable strings were found")
        missing = []
        for locale in self.locales:
            entries = support.parse_po(locale / "LC_MESSAGES" / "nvda.po")
            known = {entry["msgid"] for entry in entries if entry["msgid"]}
            for text in sorted(self.strings - known):
                missing.append("%s: %r" % (locale.name, text[:80]))
        self.assertEqual(
            missing,
            [],
            "source strings missing from a .po file (add them, translated or not):\n"
            + "\n".join(missing),
        )

    def test_arabic_is_fully_translated(self):
        arabic = support.ROOT / "locale" / "ar" / "LC_MESSAGES" / "nvda.po"
        if not arabic.is_file():
            self.skipTest("Arabic locale is not present")
        empty = [
            entry["msgid"]
            for entry in support.parse_po(arabic)
            if entry["msgid"] and not entry["msgstr"].strip()
        ]
        self.assertEqual(
            empty, [], "untranslated Arabic strings:\n" + "\n".join(empty[:10])
        )

    def test_compiled_mo_matches_the_po_file(self):
        for locale in self.locales:
            po = locale / "LC_MESSAGES" / "nvda.po"
            mo = locale / "LC_MESSAGES" / "nvda.mo"
            with self.subTest(locale=locale.name):
                self.assertTrue(mo.is_file(), "%s has no nvda.mo" % locale.name)
                translated = {
                    entry["msgid"]: entry["msgstr"]
                    for entry in support.parse_po(po)
                    if entry["msgid"] and entry["msgstr"].strip()
                }
                compiled = support.read_mo(mo)
                for msgid, msgstr in translated.items():
                    self.assertEqual(
                        compiled.get(msgid),
                        msgstr,
                        "%s: nvda.mo is out of date for %r" % (locale.name, msgid[:60]),
                    )

    def test_mo_never_contains_an_empty_translation(self):
        for locale in self.locales:
            compiled = support.read_mo(locale / "LC_MESSAGES" / "nvda.mo")
            empty = [key for key, value in compiled.items() if key and not value.strip()]
            with self.subTest(locale=locale.name):
                self.assertEqual(
                    empty,
                    [],
                    "%s: an empty msgstr makes gettext return an empty string\n%s"
                    % (locale.name, empty[:5]),
                )

    def test_mo_header_declares_utf8(self):
        for locale in self.locales:
            compiled = support.read_mo(locale / "LC_MESSAGES" / "nvda.mo")
            header = compiled.get("", "")
            with self.subTest(locale=locale.name):
                self.assertIn("charset=utf-8", header.lower())


if __name__ == "__main__":
    unittest.main()
