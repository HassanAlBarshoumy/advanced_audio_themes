# -*- coding: UTF-8 -*-
"""Bookmark scripts run in a restricted sandbox: prove it cannot be escaped."""

import ast
import re
import unittest

import support

QUICK_JUMP = "globalPlugins/audiothemes/browserNavEngine/quickJump.py"


class TestBookmarkScriptSandbox(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        namespace = support.load_parts(
            QUICK_JUMP,
            functions=("_validate_script_ast",),
            constants=(
                "_FORMAT_DUNDER_RE",
                "_DUNDER_SCRIPT_ERROR",
                "_IMPORT_SCRIPT_ERROR",
            ),
            extra_globals={"ast": ast, "re": re},
        )
        cls.validate = staticmethod(namespace["_validate_script_ast"])

    def assert_rejected(self, code):
        with self.assertRaises(SyntaxError):
            self.validate(ast.parse(code))

    def assert_accepted(self, code):
        self.validate(ast.parse(code))

    def test_normal_snippets_still_run(self):
        for code in (
            "x = 1",
            "print(p)",
            "if p.level == 1:\n    pump()",
            "text = '{0} and {1}'.format(a, b)",
            "items = [i for i in range(3)]",
            "value = getattr(p, 'textInfo', None)",
        ):
            with self.subTest(code=code):
                self.assert_accepted(code)

    def test_dunder_attribute_access_is_rejected(self):
        for code in (
            "().__class__",
            "object.__subclasses__()",
            "p.__dict__",
            "x = ''.__class__.__mro__",
        ):
            with self.subTest(code=code):
                self.assert_rejected(code)

    def test_dunder_names_are_rejected(self):
        for code in (
            "__import__('os')",
            "x = __builtins__",
            "y = __loader__",
        ):
            with self.subTest(code=code):
                self.assert_rejected(code)

    def test_safe_builtins_exclude_the_dangerous_ones(self):
        text = support.read_text(QUICK_JUMP)
        match = re.search(r'for s in "([^"]+)"', text)
        self.assertIsNotNone(match, "safe_builtins list not found in quickJump.py")
        allowed = set(match.group(1).split())
        for name in ("eval", "exec", "compile", "open", "__import__", "input"):
            with self.subTest(name=name):
                self.assertNotIn(name, allowed)

    def test_imports_are_rejected(self):
        for code in (
            "import os",
            "from os import system",
            "import os, sys",
        ):
            with self.subTest(code=code):
                self.assert_rejected(code)

    def test_format_string_cannot_reach_a_dunder(self):
        for code in (
            "'{0.__class__}'.format(1)",
            "text = '{0.__class__.__mro__}'.format(1)",
        ):
            with self.subTest(code=code):
                self.assert_rejected(code)

    def test_format_string_with_normal_fields_is_allowed(self):
        self.assert_accepted("'{0} {1}'.format(a, b)")


if __name__ == "__main__":
    unittest.main()
