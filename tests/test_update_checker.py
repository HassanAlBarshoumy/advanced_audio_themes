# -*- coding: UTF-8 -*-
"""Version comparison and download-integrity helpers of the update checker."""

import hashlib
import os
import tempfile
import unittest

import support

UPDATE_CHECKER = "globalPlugins/audiothemes/update_checker.py"


class TestUpdateChecker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.namespace = support.load_parts(
            UPDATE_CHECKER,
            functions=(
                "parse_version",
                "_parse_checksum",
                "_sha256_of_file",
                "_find_asset",
                "_find_checksum_asset",
                "_read_manifest_version",
            ),
            constants=(
                "_SHA256_RE",
                "CHECKSUM_SUFFIX",
                "MAX_DOWNLOAD_BYTES",
                "_MANIFEST_VERSION_RE",
            ),
            extra_globals={"hashlib": hashlib, "os": os, "re": __import__("re")},
        )

    def test_parse_version_is_numeric(self):
        parse = self.namespace["parse_version"]
        self.assertEqual(parse("9.50"), (9, 50))
        self.assertEqual(parse("v9.50"), (9, 50))
        self.assertEqual(parse("v9.50.2"), (9, 50, 2))
        self.assertGreater(parse("9.50"), parse("9.49"))
        self.assertGreater(parse("10.0"), parse("9.99"))
        self.assertEqual(parse("beta"), (0, 0, 0))
        self.assertEqual(parse(""), (0, 0, 0))

    def test_checksum_parsing_accepts_both_formats(self):
        parse = self.namespace["_parse_checksum"]
        digest = "a" * 64
        self.assertEqual(parse(digest), digest)
        self.assertEqual(parse("%s  advanced_audio_themes-9.50.nvda-addon" % digest), digest)
        self.assertEqual(parse("%s  file\n" % digest.upper()), digest)
        self.assertIsNone(parse("not a checksum"))
        self.assertIsNone(parse(""))
        self.assertIsNone(parse(None))
        self.assertIsNone(parse("abc"))

    def test_sha256_of_file_matches_hashlib(self):
        path = None
        try:
            fd, path = tempfile.mkstemp()
            payload = b"advanced audio themes"
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
            self.assertEqual(
                self.namespace["_sha256_of_file"](path),
                hashlib.sha256(payload).hexdigest(),
            )
        finally:
            if path and os.path.exists(path):
                os.unlink(path)

    def test_asset_lookup_prefers_the_package_over_its_checksum(self):
        release = {
            "assets": [
                {
                    "name": "advanced_audio_themes-9.50.nvda-addon.sha256",
                    "browser_download_url": "https://example.invalid/sum",
                },
                {
                    "name": "advanced_audio_themes-9.50.nvda-addon",
                    "browser_download_url": "https://example.invalid/pkg",
                },
            ]
        }
        self.assertEqual(self.namespace["_find_asset"](release), "https://example.invalid/pkg")
        self.assertEqual(
            self.namespace["_find_checksum_asset"](release),
            "https://example.invalid/sum",
        )

    def test_older_release_without_checksum_is_tolerated(self):
        release = {
            "assets": [
                {"name": "x.nvda-addon", "browser_download_url": "https://example.invalid/pkg"}
            ]
        }
        self.assertIsNone(self.namespace["_find_checksum_asset"](release))

    def test_empty_release_returns_nothing(self):
        self.assertIsNone(self.namespace["_find_asset"]({}))
        self.assertIsNone(self.namespace["_find_checksum_asset"]({}))

    def test_download_cap_is_64_megabytes(self):
        self.assertEqual(self.namespace["MAX_DOWNLOAD_BYTES"], 64 * 1024 * 1024)

    def test_installed_version_falls_back_to_manifest(self):
        manifest = support.parse_manifest()
        self.assertEqual(self.namespace["_read_manifest_version"](), manifest["version"])

    def test_checksum_suffix_cannot_match_the_package(self):
        suffix = self.namespace["CHECKSUM_SUFFIX"]
        self.assertTrue("x.nvda-addon.sha256".endswith(".nvda-addon" + suffix))
        self.assertFalse("x.nvda-addon".endswith(".nvda-addon" + suffix))


if __name__ == "__main__":
    unittest.main()
