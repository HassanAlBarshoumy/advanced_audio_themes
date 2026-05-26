import os
import sys
import zipfile
import json

sys.dont_write_bytecode = True
import buildVars

info = buildVars.addon_info
addon_name = info["addon_name"]
addon_version = info["addon_version"]
output_name = f"{addon_name}-{addon_version}.nvda-addon"

EXCLUDE_DIRS = {"__pycache__", ".git", ".github"}
EXCLUDE_FILES = {".gitignore", "buildVars.py", "build_addon.py", "SConstruct",
                 "sconstruct", "manifest.ini.tpl", "*.pyc", "*.pyo"}
ADDON_DIR = os.path.dirname(os.path.abspath(__file__))


def should_exclude(rel_path):
    parts = rel_path.replace("\\", "/").split("/")
    for part in parts:
        if part in EXCLUDE_DIRS:
            return True
    fname = parts[-1] if parts else ""
    if fname in EXCLUDE_FILES:
        return True
    if fname.endswith((".pyc", ".pyo", ".py~")):
        return True
    return False


def build_addon():
    output_path = os.path.join(ADDON_DIR, output_name)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for root, dirs, files in os.walk(ADDON_DIR):
            for d in list(dirs):
                if d in EXCLUDE_DIRS:
                    dirs.remove(d)
            for fname in files:
                full_path = os.path.join(root, fname)
                rel_path = os.path.relpath(full_path, ADDON_DIR)
                if not should_exclude(rel_path):
                    zf.write(full_path, rel_path)
    print(f"Built: {output_path}")
    return output_path


if __name__ == "__main__":
    build_addon()
