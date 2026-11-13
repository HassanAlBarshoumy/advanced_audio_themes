# -*- coding: UTF-8 -*-
"""Static health checks that every shipped file must keep passing."""

import ast
import unittest

import support


class TestSyntax(unittest.TestCase):
    def test_every_python_file_parses(self):
        failures = []
        for path in support.python_files():
            try:
                ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError as error:
                failures.append("%s: %s" % (path.relative_to(support.ROOT), error))
        self.assertEqual(failures, [], "files that do not parse:\n" + "\n".join(failures))

    def test_no_file_is_empty(self):
        empty = [
            str(path.relative_to(support.ROOT))
            for path in support.python_files()
            if not path.read_text(encoding="utf-8").strip()
        ]
        self.assertEqual(empty, [], "empty sources: %s" % empty)


class TestErrorHandling(unittest.TestCase):
    def _handlers(self):
        for path in support.python_files():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    yield path, node

    def test_no_silently_swallowed_exception(self):
        """``except ...: pass`` hides failures: log them instead."""
        offenders = []
        for path, node in self._handlers():
            if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                offenders.append(
                    "%s:%d" % (path.relative_to(support.ROOT), node.lineno)
                )
        self.assertEqual(
            offenders,
            [],
            "silent except/pass blocks (use log.debug(..., exc_info=True)):\n"
            + "\n".join(offenders),
        )

    def test_every_except_names_its_exception(self):
        """A bare ``except:`` also catches KeyboardInterrupt and SystemExit."""
        offenders = []
        for path, node in self._handlers():
            if node.type is None:
                offenders.append(
                    "%s:%d" % (path.relative_to(support.ROOT), node.lineno)
                )
        self.assertEqual(offenders, [], "bare except clauses:\n" + "\n".join(offenders))


class TestNoSecrets(unittest.TestCase):
    PATTERNS = (
        "ghp_",
        "github_pat_",
        "sk-",
        "BEGIN RSA PRIVATE KEY",
        "BEGIN OPENSSH PRIVATE KEY",
        "AIza",
    )

    def test_no_credentials_are_committed(self):
        offenders = []
        for path in support.python_files():
            text = path.read_text(encoding="utf-8")
            for pattern in self.PATTERNS:
                if pattern in text:
                    offenders.append(
                        "%s contains %r" % (path.relative_to(support.ROOT), pattern)
                    )
        self.assertEqual(offenders, [], "possible secrets:\n" + "\n".join(offenders))


if __name__ == "__main__":
    unittest.main()
