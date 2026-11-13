# -*- coding: UTF-8 -*-
"""The CLDR emoji loader must parse the official file and never block."""

import re
import time
import unittest

import support

EMOJI = "globalPlugins/audiothemes/emoji_cldr_data.py"

SAMPLE = """\
# group: Smileys & Emotion
1F600 ; fully-qualified # 😀 E1.0 grinning face
1F601 ; fully-qualified # 😁 E0.6 beaming face with smiling eyes

# group: Flags
1F1E6 1F1E8 ; fully-qualified # 🇦🇨 E2.0 flag: Ascension Island
"""


class TestEmojiData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.namespace = support.load_parts(
            EMOJI,
            functions=("_hex_to_emoji", "_parse_emoji_test", "_build_category_map"),
            constants=(
                "CLDR_GROUP_TO_CATEGORY",
                "CACHE_MAX_AGE_DAYS",
                "CACHE_MAX_AGE_SECONDS",
            ),
            extra_globals={"re": re, "time": time},
        )

    def test_hex_to_emoji(self):
        convert = self.namespace["_hex_to_emoji"]
        self.assertEqual(convert("1F600"), "\U0001F600")
        self.assertEqual(convert("1F1E6 1F1E8"), "\U0001F1E6\U0001F1E8")
        self.assertIsNone(convert("zzz"))
        self.assertIsNone(convert(""))

    def test_parse_emoji_test_reads_groups_and_names(self):
        groups, names = self.namespace["_parse_emoji_test"](SAMPLE)
        self.assertEqual(groups["\U0001F600"], "Smileys & Emotion")
        self.assertEqual(names["\U0001F600"], "grinning face")
        self.assertEqual(groups["\U0001F1E6\U0001F1E8"], "Flags")
        self.assertIn("Ascension Island", names["\U0001F1E6\U0001F1E8"])
        self.assertEqual(len(groups), 3)

    def test_category_map_uses_the_cldr_groups(self):
        groups = {
            "\U0001F600": "Smileys & Emotion",
            "\U0001F1E6\U0001F1E8": "Flags",
            "x": "Unknown group",
        }
        categories = self.namespace["_build_category_map"](groups)
        self.assertEqual(categories["\U0001F600"], 0)
        self.assertEqual(categories["\U0001F1E6\U0001F1E8"], 8)
        self.assertEqual(categories["x"], 0)

    def test_cache_lifetime_is_sixty_days(self):
        self.assertEqual(self.namespace["CACHE_MAX_AGE_DAYS"], 60)
        self.assertEqual(self.namespace["CACHE_MAX_AGE_SECONDS"], 60 * 24 * 60 * 60)

    def test_load_never_waits_for_the_network(self):
        import ast

        tree = ast.parse(support.read_text(EMOJI))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in ("load", "ensure_loaded"):
                called = {
                    call.func.id
                    for call in ast.walk(node)
                    if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                }
                with self.subTest(function=node.name):
                    self.assertNotIn("_download_and_parse", called)
                    self.assertNotIn("urlopen", called)
        # The refresh runs in a daemon thread so NVDA can always quit.
        self.assertIn("daemon=True", support.read_text(EMOJI))


if __name__ == "__main__":
    unittest.main()
