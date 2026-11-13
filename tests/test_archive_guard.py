# -*- coding: UTF-8 -*-
"""Archive names must never escape the folder they are extracted into."""

import unittest

import support

HANDLER = "globalPlugins/audiothemes/handler.py"


class TestArchiveNameGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.is_safe = staticmethod(
            support.load_parts(HANDLER, functions=("is_safe_archive_name",))[
                "is_safe_archive_name"
            ]
        )

    def test_accepts_plain_relative_names(self):
        for name in (
            "sound.wav",
            "theme/sounds/focus.wav",
            "theme\\sounds\\focus.wav",
            "a..b.wav",
            "dir.with.dots/file.wav",
            ".hidden",
            "ünïcode/ö.wav",
        ):
            with self.subTest(name=name):
                self.assertTrue(self.is_safe(name))

    def test_rejects_traversal_and_absolute_paths(self):
        for name in (
            "",
            "../outside.wav",
            "a/../../outside.wav",
            "..\\outside.wav",
            "a\\..\\..\\outside.wav",
            "/etc/passwd",
            "\\windows\\system32\\x.dll",
            "C:/Windows/x.dll",
            "c:\\Windows\\x.dll",
            "a\x00b.wav",
            "./../x.wav",
        ):
            with self.subTest(name=name):
                self.assertFalse(self.is_safe(name))

    def test_rejects_only_dot_dot_segments(self):
        # "..." is a legal file name, ".." alone is not.
        self.assertTrue(self.is_safe("..."))
        self.assertFalse(self.is_safe("a/.."))


if __name__ == "__main__":
    unittest.main()
