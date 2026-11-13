# -*- coding: UTF-8 -*-
"""Shared helpers for the repository test suite.

The tests run against the source tree, never against a running NVDA, so the
add-on modules (which import ``wx``, ``addonHandler``, ``config`` ...) cannot be
imported directly.  Everything the tests need is either pure standard-library
code or a single function/constant extracted from a file with ``ast``.
"""

import ast
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SKIP_DIRS = {
    ".git",
    ".gitnexus",
    ".claude",
    "__pycache__",
    "build",
    "dist",
    "tests",
    "pywinsdk",
}


def source_path(relative):
    return ROOT / relative


def read_text(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


def python_files():
    """Every Python source file the add-on ships, as absolute paths."""
    found = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for filename in sorted(filenames):
            if filename.endswith(".py"):
                found.append(Path(dirpath) / filename)
    return found


def load_parts(relative, functions=(), constants=(), extra_globals=None):
    """Execute selected module-level functions and constants of a file.

    Only the requested nodes are compiled, so a module that imports ``wx`` or
    NVDA internals can still be unit-tested one function at a time.
    """
    path = ROOT / relative
    tree = ast.parse(path.read_text(encoding="utf-8"))
    wanted_functions = set(functions)
    wanted_constants = set(constants)
    body = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in wanted_functions:
            body.append(node)
        elif isinstance(node, ast.Assign):
            names = {t.id for t in node.targets if isinstance(t, ast.Name)}
            if names & wanted_constants:
                body.append(node)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id in wanted_constants:
                body.append(node)

    missing = (wanted_functions | wanted_constants) - {
        getattr(node, "name", None)
        or next(
            (t.id for t in getattr(node, "targets", []) if isinstance(t, ast.Name)),
            getattr(getattr(node, "target", None), "id", None),
        )
        for node in body
    }
    if missing:
        raise AssertionError(
            "%s: could not find %s" % (relative, ", ".join(sorted(missing)))
        )

    module = ast.Module(body=body, type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {
        "__file__": str(path),
        "__name__": "_extracted_%s" % path.stem,
        "__builtins__": __builtins__,
    }
    if extra_globals:
        namespace.update(extra_globals)
    exec(compile(module, str(path), "exec"), namespace)
    return namespace


def parse_manifest(relative="manifest.ini"):
    """Return the top-level ``key = value`` pairs of an NVDA manifest."""
    text = read_text(relative)
    values = {}
    lines = text.splitlines()
    index = 0
    assignment = None
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if assignment is None:
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key, value = stripped.split("=", 1)
                assignment = (key.strip(), value.strip())
        if assignment is not None:
            key, value = assignment
            if value.startswith('"""'):
                chunk = value[3:]
                collected = []
                while True:
                    if '"""' in chunk:
                        collected.append(chunk.split('"""', 1)[0])
                        value = "\n".join(collected)
                        break
                    collected.append(chunk)
                    index += 1
                    if index >= len(lines):
                        raise AssertionError("unterminated triple quote in %s" % key)
                    chunk = lines[index]
                values[key] = value
                assignment = None
            else:
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                values[key] = value
                assignment = None
        index += 1
    return values


def load_build_vars():
    """Evaluate buildVars.py without importing NVDA (it is standalone)."""
    path = ROOT / "buildVars.py"
    namespace = {"__file__": str(path), "__name__": "buildVars"}
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), namespace)
    return namespace


def parse_po(relative_or_path):
    """Return ``[{"msgid": ..., "msgstr": ...}]`` in file order."""
    path = Path(relative_or_path)
    if not path.is_absolute():
        path = ROOT / path
    entries = []
    current = None
    field = None

    def flush():
        nonlocal current, field
        if current is not None:
            entries.append(current)
            current = None
            field = None

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            flush()
            continue
        if line.startswith("#"):
            continue
        if line.startswith("msgctxt "):
            flush()
            current = {"msgid": "", "msgstr": ""}
            field = None
        elif line.startswith("msgid "):
            if current is None:
                current = {"msgid": "", "msgstr": ""}
            current["msgid"] = ast.literal_eval(line[len("msgid "):])
            field = "msgid"
        elif line.startswith("msgstr "):
            if current is None:
                current = {"msgid": "", "msgstr": ""}
            current["msgstr"] = ast.literal_eval(line[len("msgstr "):])
            field = "msgstr"
        elif line.startswith('"'):
            if current is None:
                continue
            fragment = ast.literal_eval(line)
            if field in ("msgid", "msgstr"):
                current[field] = current[field] + fragment
    flush()
    return entries


def read_mo(relative_or_path):
    """Read a compiled .mo file into ``{msgid: msgstr}``."""
    import struct

    path = Path(relative_or_path)
    if not path.is_absolute():
        path = ROOT / path
    data = path.read_bytes()
    magic, _revision, count, orig_off, trans_off, _hash_size, _hash_off = struct.unpack(
        "<7I", data[:28]
    )
    if magic != 0x950412DE:
        raise AssertionError("%s is not a little-endian .mo file" % path)
    result = {}
    for index in range(count):
        o_len, o_off = struct.unpack("<2I", data[orig_off + index * 8: orig_off + index * 8 + 8])
        t_len, t_off = struct.unpack("<2I", data[trans_off + index * 8: trans_off + index * 8 + 8])
        key = data[o_off: o_off + o_len].decode("utf-8")
        value = data[t_off: t_off + t_len].decode("utf-8")
        result[key] = value
    return result


def source_strings():
    """Every literal passed to ``_()`` anywhere in the shipped sources."""
    strings = set()
    for path in python_files():
        if path.name == "buildVars.py":
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "_"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                strings.add(node.args[0].value)
    strings.discard("")
    return strings


def locale_dirs():
    base = ROOT / "locale"
    if not base.is_dir():
        return []
    return sorted(p for p in base.iterdir() if (p / "LC_MESSAGES" / "nvda.po").is_file())
