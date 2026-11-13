# -*- coding: UTF-8 -*-
"""manifest.ini is the source of truth; buildVars.py must never disagree."""

import unittest

import support


class TestVersionSync(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = support.parse_manifest()
        cls.build_vars = support.load_build_vars()["addon_info"]

    def test_version_matches_build_vars(self):
        self.assertEqual(self.manifest["version"], self.build_vars["addon_version"])

    def test_version_looks_like_x_y(self):
        self.assertRegex(self.manifest["version"], r"^\d+(\.\d+)+$")

    def test_name_matches_build_vars(self):
        self.assertEqual(self.manifest["name"], self.build_vars["addon_name"])

    def test_summary_matches_build_vars(self):
        self.assertEqual(
            self.manifest["summary"], self.build_vars["addon_summary"].strip()
        )

    def test_description_matches_build_vars(self):
        self.assertEqual(
            self.manifest["description"].strip(),
            self.build_vars["addon_description"].strip(),
        )

    def test_url_matches_build_vars(self):
        self.assertEqual(self.manifest["url"], self.build_vars["addon_url"])

    def test_source_url_points_at_the_manifest_repository(self):
        self.assertEqual(self.build_vars["addon_sourceURL"], self.manifest["url"])

    def test_author_matches_build_vars(self):
        self.assertEqual(self.manifest["author"], self.build_vars["addon_author"])

    def test_nvda_versions_match_build_vars(self):
        self.assertEqual(
            self.manifest["minimumNVDAVersion"],
            self.build_vars["addon_minimumNVDAVersion"],
        )
        self.assertEqual(
            self.manifest["lastTestedNVDAVersion"],
            self.build_vars["addon_lastTestedNVDAVersion"],
        )

    def test_version_script_agrees(self):
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, str(support.ROOT / "scripts" / "addon_version.py"), "check"],
            cwd=str(support.ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            "scripts/addon_version.py check failed:\n%s\n%s"
            % (result.stdout, result.stderr),
        )


if __name__ == "__main__":
    unittest.main()
