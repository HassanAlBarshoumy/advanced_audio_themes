"""Build the NVDA add-on package (.nvda-addon).

The add-on name and version are read from ``manifest.ini`` - the same file NVDA
itself reads - so the built file name can never disagree with the manifest.

When the script runs inside GitHub Actions it also publishes ``name``,
``version``, ``filename`` and ``path`` as step outputs through ``$GITHUB_OUTPUT``.

Standing user rule: this add-on is NEVER built locally - every build happens
on GitHub Actions. The script enforces that: it refuses to run outside a
workflow job and exits with code 2.

Usage (GitHub Actions only):
    python build_addon.py
"""

import os
import re
import sys
import zipfile

sys.dont_write_bytecode = True

ADDON_DIR = os.path.dirname(os.path.abspath(__file__))
MANIFEST_PATH = os.path.join(ADDON_DIR, "manifest.ini")

# Every workflow job on GitHub Actions sets GITHUB_ACTIONS=true. Any other
# environment means someone is running the packager on their own machine,
# which the standing user rule forbids.
GITHUB_ACTIONS_ENV = "GITHUB_ACTIONS"

LOCAL_BUILD_REFUSAL = (
	"Refusing to build locally: this add-on is built on GitHub Actions only "
	"(standing user rule - no local builds, now or in the future).\n"
	"  Build    : gh workflow run build.yml\n"
	"  Download : gh run download <run-id> -n advanced_audio_themes-<version>\n"
	"  Release  : gh workflow run release.yml -f version=<x.y>"
)


class LocalBuildRefused(Exception):
	"""Raised when the packager is invoked outside GitHub Actions."""


def enforce_ci_only_build():
	"""Abort unless running inside a GitHub Actions workflow job.

	There is deliberately no local override: the user wants every build of
	this add-on produced on GitHub, never on this machine.
	"""
	if os.environ.get(GITHUB_ACTIONS_ENV) == "true":
		return
	raise LocalBuildRefused(LOCAL_BUILD_REFUSAL)

# Development-only files and folders: never shipped inside the package.
EXCLUDE_DIRS = {".git", ".github", "__pycache__", "scripts", "dist", "build"}
EXCLUDE_FILES = {
	".gitignore",
	".gitattributes",
	".gitmodules",
	"AGENTS.md",
	"build_addon.py",
	"buildVars.py",
	"SConstruct",
	"sconstruct",
	"manifest.ini.tpl",
	"prepareDefaultConfig.py",
}
EXCLUDE_SUFFIXES = (".nvda-addon", ".sha256", ".pyc", ".pyo", ".py~", ".log")

# Tracked paths that must never be packaged even when they exist on disk.
# The x86 copies of the Steam Audio engine are dead weight: NVDA has shipped
# 64-bit only since 2023.1, this add-on requires >= 2024.1, and the loader in
# unspoken/steam_audio.py always resolves lib/x64 first. Keeping the guard here
# means re-adding the binaries cannot silently put ~16 MB back into the package.
EXCLUDE_PATHS = ("globalPlugins/audiothemes/unspoken/lib/x86",)

REQUIRED_MANIFEST_KEYS = ("name", "summary", "version", "author")


class BuildError(Exception):
	"""Raised when the package cannot be produced for a clear reason."""


def parse_manifest(path=MANIFEST_PATH):
	"""Return the top-level ``key = value`` pairs of an NVDA manifest.ini.

	Multi line values (the triple quoted ``description``) are removed first so
	their contents can never be mistaken for a key.
	"""
	with open(path, "rb") as manifest_file:
		text = manifest_file.read().decode("utf-8-sig")
	text = re.sub(r'""".*?"""', '""', text, flags=re.S)
	values = {}
	for line in text.splitlines():
		match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$", line)
		if not match:
			continue
		value = match.group(2)
		if len(value) >= 2 and value[0] == value[-1] == '"':
			value = value[1:-1]
		values.setdefault(match.group(1), value)
	return values


def addon_name_and_version():
	"""Return ``(name, version)`` after validating the mandatory manifest keys."""
	values = parse_manifest()
	missing = [key for key in REQUIRED_MANIFEST_KEYS if not values.get(key)]
	if missing:
		raise BuildError("manifest.ini is missing required keys: %s" % ", ".join(missing))
	return values["name"], values["version"]


def should_exclude(relative_path):
	"""Tell whether a path inside the add-on directory must stay out of the package."""
	normalised_path = relative_path.replace("\\", "/")
	for excluded_path in EXCLUDE_PATHS:
		if normalised_path == excluded_path or normalised_path.startswith(excluded_path + "/"):
			return True
	parts = normalised_path.split("/")
	for part in parts:
		if part in EXCLUDE_DIRS:
			return True
	file_name = parts[-1]
	if file_name in EXCLUDE_FILES:
		return True
	return file_name.endswith(EXCLUDE_SUFFIXES)


def write_github_outputs(**outputs):
	"""Publish step outputs when running on GitHub Actions (no-op elsewhere)."""
	output_file = os.environ.get("GITHUB_OUTPUT")
	if not output_file:
		return
	with open(output_file, "a", encoding="utf-8") as handle:
		for key, value in outputs.items():
			handle.write("%s=%s\n" % (key, value))


def build():
	"""Create ``<name>-<version>.nvda-addon`` next to this script."""
	enforce_ci_only_build()
	name, version = addon_name_and_version()
	file_name = "%s-%s.nvda-addon" % (name, version)
	output_path = os.path.join(ADDON_DIR, file_name)

	entries = 0
	# LZMA shrinks the package by roughly a quarter compared with deflate: the
	# bulk of the add-on is WAV audio and the Steam Audio DLL, and NVDA installs
	# add-ons with Python's zipfile module, which reads LZMA natively.
	with zipfile.ZipFile(output_path, "w", zipfile.ZIP_LZMA) as package:
		for folder, sub_folders, files in os.walk(ADDON_DIR):
			# Prune instead of filtering afterwards: ".git" can hold thousands
			# of files and we must never even walk into it.
			sub_folders[:] = [name for name in sub_folders if name not in EXCLUDE_DIRS]
			for file_name_on_disk in files:
				full_path = os.path.join(folder, file_name_on_disk)
				relative_path = os.path.relpath(full_path, ADDON_DIR)
				if should_exclude(relative_path):
					continue
				package.write(full_path, relative_path.replace(os.sep, "/"))
				entries += 1

	with zipfile.ZipFile(output_path) as package:
		if "manifest.ini" not in package.namelist():
			os.remove(output_path)
			raise BuildError("the built package has no manifest.ini at its root")

	size_mb = os.path.getsize(output_path) / (1024 * 1024)
	print("Add-on  : %s %s" % (name, version))
	print("Entries : %d" % entries)
	print("Package : %s (%.1f MB)" % (output_path, size_mb))

	write_github_outputs(name=name, version=version, filename=file_name, path=output_path)
	return output_path


def main():
	try:
		build()
	except LocalBuildRefused as refusal:
		print(str(refusal), file=sys.stderr)
		return 2
	except BuildError as error:
		print("Build failed: %s" % error, file=sys.stderr)
		return 1
	return 0


if __name__ == "__main__":
	sys.exit(main())
