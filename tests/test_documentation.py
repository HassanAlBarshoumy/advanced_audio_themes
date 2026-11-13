# -*- coding: UTF-8 -*-
"""Every documentation folder must ship the file NVDA opens for Help."""

import re
import unittest

import support


class TestDocumentation(unittest.TestCase):
    def test_manifest_doc_file_is_html(self):
        manifest = support.parse_manifest()
        self.assertEqual(manifest["docFileName"], "readme.html")

    def test_every_doc_folder_has_the_manual_in_both_formats(self):
        doc = support.ROOT / "doc"
        self.assertTrue(doc.is_dir(), "doc/ is missing")
        missing = []
        for folder in sorted(p for p in doc.iterdir() if p.is_dir()):
            for name in ("readme.md", "readme.html"):
                if not (folder / name).is_file():
                    missing.append("%s/%s" % (folder.name, name))
        self.assertEqual(
            missing, [], "documentation folders missing a manual:\n" + "\n".join(missing)
        )

    def test_english_manual_is_the_fallback(self):
        english = support.read_text("doc/en/readme.html")
        self.assertIn("<h1>Advanced Audio Themes</h1>", english)
        self.assertIn('lang="en"', english)

    def test_german_manual_is_german_and_well_formed(self):
        german = support.read_text("doc/de/readme.html")
        self.assertIn('lang="de"', german)
        self.assertIn("<h1>Erweiterte Audio-Themes", german)
        self.assertIn("Funktionen", german)
        # No markdown leftovers: the browser would show them literally.
        self.assertNotIn("**", german)
        self.assertNotIn("| ---", german)

    def test_manual_tags_are_balanced(self):
        german = support.read_text("doc/de/readme.html")
        for tag in ("ul", "ol", "li", "p", "table", "th", "td", "strong"):
            with self.subTest(tag=tag):
                self.assertEqual(
                    len(re.findall(r"<%s\b" % tag, german)),
                    len(re.findall(r"</%s>" % tag, german)),
                )

    def test_help_script_opens_the_shipped_file_name(self):
        text = support.read_text("globalPlugins/audiothemes/__init__.py")
        self.assertIn('os.path.join(addonDir, "doc", lang, "readme.html")', text)


if __name__ == "__main__":
    unittest.main()
