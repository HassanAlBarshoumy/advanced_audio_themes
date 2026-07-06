# -*- coding: UTF-8 -*-
# CLDR-based emoji detection and categorization using the Unicode emoji-test.txt data.
# Downloads and caches the official Unicode emoji list with CLDR groups and names.

import json
import os
import threading
import time
import urllib.request

import globalVars
import logHandler

EMOJI_TEST_URL = "https://unicode.org/Public/emoji/16.0/emoji-test.txt"
EMOJI_TEST_URL_FALLBACK = "https://unicode.org/Public/emoji/latest/emoji-test.txt"
CACHE_FILENAME = "emoji_cldr_cache.json"
CACHE_MAX_AGE_DAYS = 60

CLDR_GROUP_TO_CATEGORY = {
    "Smileys & Emotion": 0,
    "People & Body": 1,
    "Animals & Nature": 2,
    "Food & Drink": 3,
    "Travel & Places": 4,
    "Activities": 5,
    "Objects": 6,
    "Symbols": 7,
    "Flags": 8,
    "Component": 1,
}

_emoji_to_group = {}
_emoji_to_name = {}
_emoji_to_category = {}
_emoji_set = set()
_loaded = False
_load_attempted = False
_load_lock = threading.Lock()


def _get_cache_dir():
    return os.path.join(globalVars.appArgs.configPath, "audio-themes")


def _get_cache_path():
    return os.path.join(_get_cache_dir(), CACHE_FILENAME)


def _hex_to_emoji(hex_str):
    try:
        return "".join(chr(int(p, 16)) for p in hex_str.strip().split())
    except (ValueError, OverflowError):
        return None


def _parse_emoji_test(data):
    emoji_to_group = {}
    emoji_to_name = {}
    current_group = None
    for line in data.splitlines():
        stripped = line.strip()
        if stripped.startswith("# group:"):
            current_group = stripped[8:].strip()
        elif not stripped.startswith("#") and ";" in stripped:
            parts = stripped.split(";", 1)
            if len(parts) < 2:
                continue
            hex_codes = parts[0].strip()
            rest = parts[1].strip()
            emoji_str = _hex_to_emoji(hex_codes)
            if emoji_str is None:
                continue
            name = ""
            if "#" in rest:
                after_hash = rest.split("#", 1)[1].strip()
                name_start = after_hash
                if name_start.startswith(emoji_str):
                    name_start = name_start[len(emoji_str):].strip()
                if name_start.startswith("E") and " " in name_start:
                    idx = name_start.find(" ")
                    if idx > 0:
                        name = name_start[idx + 1:]
                    else:
                        name = name_start
                else:
                    name = name_start
            emoji_to_group[emoji_str] = current_group
            emoji_to_name[emoji_str] = name
    return emoji_to_group, emoji_to_name


def _build_category_map(emoji_to_group):
    emoji_to_category = {}
    for emoji_str, group in emoji_to_group.items():
        emoji_to_category[emoji_str] = CLDR_GROUP_TO_CATEGORY.get(group, 0)
    return emoji_to_category


def _load_from_cache():
    path = _get_cache_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        emoji_to_group = {}
        emoji_to_name = {}
        for entry in data.get("emoji", []):
            hex_str = entry.get("h")
            group = entry.get("g")
            name = entry.get("n")
            emoji_str = _hex_to_emoji(hex_str)
            if emoji_str and group:
                emoji_to_group[emoji_str] = group
                emoji_to_name[emoji_str] = name or ""
        return emoji_to_group, emoji_to_name
    except Exception as e:
        logHandler.log.debug(f"Could not load emoji CLDR cache: {e}")
        return None, None


def _save_to_cache(emoji_to_group, emoji_to_name):
    path = _get_cache_path()
    try:
        d = os.path.dirname(path)
        if not os.path.exists(d):
            os.makedirs(d)
        entries = []
        for emoji_str, group in emoji_to_group.items():
            hex_str = " ".join(f"{ord(c):04X}" for c in emoji_str)
            entries.append({
                "h": hex_str,
                "g": group,
                "n": emoji_to_name.get(emoji_str, ""),
            })
        data = {
            "version": "16.0",
            "timestamp": time.time(),
            "emoji": entries,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        logHandler.log.debug(f"Could not save emoji CLDR cache: {e}")


def _download_and_parse():
    urls = [EMOJI_TEST_URL, EMOJI_TEST_URL_FALLBACK]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "NVDA-AdvancedAudioThemes/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read().decode("utf-8")
            emoji_to_group, emoji_to_name = _parse_emoji_test(data)
            if emoji_to_group:
                return emoji_to_group, emoji_to_name
        except Exception as e:
            logHandler.log.debug(f"Could not download emoji CLDR data from {url}: {e}")
    return None, None


def load(force_refresh=False):
    global _emoji_to_group, _emoji_to_name, _emoji_to_category, _emoji_set, _loaded, _load_attempted
    with _load_lock:
        if _loaded and not force_refresh:
            return True
        _load_attempted = True
        emoji_to_group = None
        emoji_to_name = None
        if not force_refresh:
            emoji_to_group, emoji_to_name = _load_from_cache()
        if emoji_to_group is None:
            emoji_to_group, emoji_to_name = _download_and_parse()
            if emoji_to_group:
                _save_to_cache(emoji_to_group, emoji_to_name)
        if emoji_to_group:
            _emoji_to_group = emoji_to_group
            _emoji_to_name = emoji_to_name
            _emoji_to_category = _build_category_map(emoji_to_group)
            _emoji_set = set(emoji_to_group.keys())
            _loaded = True
            logHandler.log.info(f"Loaded {len(emoji_to_group)} emoji from CLDR data")
            return True
        logHandler.log.warning("Could not load CLDR emoji data — using fallback")
        _loaded = False
        return False


def ensure_loaded():
    if not _load_attempted:
        return load()
    return _loaded


def is_loaded():
    return _loaded


def get_emoji_group(emoji_char):
    if not ensure_loaded():
        return None
    return _emoji_to_group.get(emoji_char)


def get_emoji_name(emoji_char):
    if not ensure_loaded():
        return None
    return _emoji_to_name.get(emoji_char)


def get_emoji_category(emoji_char):
    if not ensure_loaded():
        return None
    return _emoji_to_category.get(emoji_char)


def is_emoji(char):
    if not ensure_loaded():
        return False
    return char in _emoji_set


def get_all_emoji():
    if not ensure_loaded():
        return set()
    return _emoji_set


def get_all_mappings():
    if not ensure_loaded():
        return {}, {}, {}
    return _emoji_to_group, _emoji_to_name, _emoji_to_category
