"""Keep the add-on version consistent across the repository.

``manifest.ini`` is the source of truth - it is the file NVDA itself reads -
and ``buildVars.py`` is kept in sync so the two can never disagree.

Usage:
    python scripts/addon_version.py show
    python scripts/addon_version.py check
    python scripts/addon_version.py set 9.44
    python scripts/addon_version.py bump major|minor|patch
    python scripts/addon_version.py set-last-tested 2026.3

Every value is rewritten in place, byte for byte, so line endings and the rest
of the file (including the triple quoted description) are never touched.
"""

import os
import re
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_PATH = os.path.join(ROOT_DIR, "manifest.ini")
BUILD_VARS_PATH = os.path.join(ROOT_DIR, "buildVars.py")

MANIFEST_VERSION_RE = re.compile(rb"(?m)^(version\s*=\s*)([^\r\n]*?)(\r?\n)")
MANIFEST_LAST_TESTED_RE = re.compile(rb"(?m)^(lastTestedNVDAVersion\s*=\s*)([^\r\n]*?)(\r?\n)")
BUILD_VARS_VERSION_RE = re.compile(rb'("addon_version"\s*:\s*")([^"]*)(")')
VERSION_RE = re.compile(r"^\d+(?:\.\d+)*$")

USAGE = "usage: addon_version.py {show|check|set <version>|bump major|minor|patch|set-last-tested <version>}"


class VersionError(Exception):
	"""Raised for an invalid version or a file that cannot be updated."""


def read_bytes(path):
	with open(path, "rb") as handle:
		return handle.read()


def write_bytes(path, data):
	with open(path, "wb") as handle:
		handle.write(data)


def read_value(path, pattern, label):
	match = pattern.search(read_bytes(path))
	if match is None:
		raise VersionError("%s: could not find %s" % (path, label))
	return match.group(2).decode("utf-8").strip()


def replace_value(path, pattern, new_value, label):
	data = read_bytes(path)
	replacement = new_value.encode("utf-8")
	updated, count = pattern.subn(lambda match: match.group(1) + replacement + match.group(3), data, count=1)
	if count != 1:
		raise VersionError("%s: could not find %s" % (path, label))
	write_bytes(path, updated)


def check_version_format(version, what):
	if not VERSION_RE.match(version):
		raise VersionError("%s must be a dotted number such as 9.44, got %r" % (what, version))


def manifest_version():
	return read_value(MANIFEST_PATH, MANIFEST_VERSION_RE, "the version line")


def build_vars_version():
	return read_value(BUILD_VARS_PATH, BUILD_VARS_VERSION_RE, "the addon_version entry")


def command_show():
	print(manifest_version())
	return 0


def command_check():
	manifest = manifest_version()
	declared = build_vars_version()
	check_version_format(manifest, "manifest.ini version")
	if declared != manifest:
		raise VersionError(
			"version mismatch: manifest.ini has %s but buildVars.py has %s "
			"(fix it with: python scripts/addon_version.py set %s)" % (manifest, declared, manifest)
		)
	print("versions agree: %s" % manifest)
	return 0


def set_version(new_version):
	check_version_format(new_version, "version")
	replace_value(MANIFEST_PATH, MANIFEST_VERSION_RE, new_version, "the version line")
	replace_value(BUILD_VARS_PATH, BUILD_VARS_VERSION_RE, new_version, "the addon_version entry")
	print("version set to %s" % new_version)
	return 0


def command_bump(part):
	parts = [int(number) for number in manifest_version().split(".")]
	while len(parts) < 3:
		parts.append(0)
	index = {"major": 0, "minor": 1, "patch": 2}[part]
	parts[index] += 1
	for position in range(index + 1, len(parts)):
		parts[position] = 0
	while len(parts) > 2 and parts[-1] == 0:
		parts.pop()
	return set_version(".".join(str(number) for number in parts))


def command_set_last_tested(new_version):
	check_version_format(new_version, "NVDA version")
	replace_value(MANIFEST_PATH, MANIFEST_LAST_TESTED_RE, new_version, "the lastTestedNVDAVersion line")
	print("lastTestedNVDAVersion set to %s" % new_version)
	return 0


def main(argv):
	if not argv:
		print(USAGE)
		return 2
	command, arguments = argv[0], argv[1:]
	if command == "show":
		expected = 0
	elif command == "check":
		expected = 0
	elif command == "set":
		expected = 1
	elif command == "bump":
		expected = 1
	elif command == "set-last-tested":
		expected = 1
	else:
		print("error: unknown command %r" % command, file=sys.stderr)
		print(USAGE, file=sys.stderr)
		return 2

	if len(arguments) != expected:
		print("error: %s takes %d argument(s)" % (command, expected), file=sys.stderr)
		print(USAGE, file=sys.stderr)
		return 2

	try:
		if command == "show":
			return command_show()
		if command == "check":
			return command_check()
		if command == "set":
			return set_version(arguments[0])
		if command == "bump":
			if arguments[0] not in ("major", "minor", "patch"):
				raise VersionError("bump takes one of: major, minor, patch")
			return command_bump(arguments[0])
		return command_set_last_tested(arguments[0])
	except VersionError as error:
		print("error: %s" % error, file=sys.stderr)
		return 1


if __name__ == "__main__":
	sys.exit(main(sys.argv[1:]))
