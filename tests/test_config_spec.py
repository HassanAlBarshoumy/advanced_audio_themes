# -*- coding: UTF-8 -*-
"""The configuration spec in handler.py is the single source of truth."""

import re
import unittest

import support

HANDLER = "globalPlugins/audiothemes/handler.py"
SETTINGS = "globalPlugins/audiothemes/settings.py"

SPEC_VALUE_RE = re.compile(
    r"^(boolean|integer|float|string|list)\(\s*default=.*\)\s*$", re.DOTALL
)
# ``config.conf["audiothemes"]["some_key"]`` written out literally: every such
# key must exist in the spec or NVDA raises KeyError at runtime.
LITERAL_KEY_RE = re.compile(r"\[\"audiothemes\"\]\[\"([A-Za-z0-9_]+)\"\]")


class TestConfigSpec(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = support.load_parts(
            HANDLER, constants=("audiothemes_config_defaults",)
        )["audiothemes_config_defaults"]

    def test_spec_is_a_dict_of_configobj_strings(self):
        self.assertIsInstance(self.spec, dict)
        for key, value in self.spec.items():
            with self.subTest(key=key):
                self.assertIsInstance(value, str)
                self.assertRegex(value, SPEC_VALUE_RE)

    def test_spec_has_no_duplicate_or_empty_keys(self):
        keys = list(self.spec)
        self.assertEqual(len(keys), len(set(keys)))
        self.assertNotIn("", keys)

    def test_core_keys_are_present(self):
        for key in (
            "enable_audio_themes",
            "active_theme",
            "use_in_say_all",
            "speak_roles",
            "blacklisted_roles",
            "check_for_updates_auto",
            "store_url",
        ):
            with self.subTest(key=key):
                self.assertIn(key, self.spec)

    def test_store_url_default_is_https(self):
        self.assertIn("default='https://", self.spec["store_url"])

    def test_literal_config_access_uses_spec_keys(self):
        offenders = []
        for relative in (HANDLER, SETTINGS):
            text = support.read_text(relative)
            for match in LITERAL_KEY_RE.finditer(text):
                key = match.group(1)
                if key not in self.spec:
                    line = text.count("\n", 0, match.start()) + 1
                    offenders.append("%s:%d -> %s" % (relative, line, key))
        self.assertEqual(
            offenders,
            [],
            "config keys read from NVDA without a spec entry:\n" + "\n".join(offenders),
        )


if __name__ == "__main__":
    unittest.main()
