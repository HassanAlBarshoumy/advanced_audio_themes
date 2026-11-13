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
# True once the on-disk cache has been looked at (found or not).  Kept so the
# file is read at most once per process instead of on every detection call.
_cache_checked = False
# Guards every mutation of the module state above, and the download trigger.
_load_lock = threading.RLock()
# A download is started in a daemon thread: the hot path must never block on
# unicode.org.  These two fields rate-limit it so a failed download is retried
# at most once every DOWNLOAD_RETRY_SECONDS.
_downloading = False
_last_attempt_time = 0.0
DOWNLOAD_RETRY_SECONDS = 6 * 60 * 60
CACHE_MAX_AGE_SECONDS = CACHE_MAX_AGE_DAYS * 24 * 60 * 60


def _get_cache_dir():
    return os.path.join(globalVars.appArgs.configPath, "audio-themes")


def _get_cache_path():
    return os.path.join(_get_cache_dir(), CACHE_FILENAME)


def _hex_to_emoji(hex_str):
    try:
        if not hex_str or not hex_str.strip():
            return None
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
    """Return ``(emoji_to_group, emoji_to_name, timestamp)`` from the cache.

    Any failure (missing, unreadable or malformed file) yields
    ``(None, None, None)`` so the caller falls back to a background download.
    """
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
        if not emoji_to_group:
            return None, None, None
        return emoji_to_group, emoji_to_name, data.get("timestamp")
    except Exception as e:
        logHandler.log.debug(f"Could not load emoji CLDR cache: {e}")
        return None, None, None


def _cache_is_stale(timestamp):
    try:
        age = time.time() - float(timestamp)
    except (TypeError, ValueError):
        return True
    return age > CACHE_MAX_AGE_SECONDS


def _save_to_cache(emoji_to_group, emoji_to_name):
    path = _get_cache_path()
    tmp_path = None
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
        # Write then rename: a crash mid-write must never leave a half-written
        # cache that would be re-read on the next start.
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp_path, path)
    except Exception as e:
        logHandler.log.debug(f"Could not save emoji CLDR cache: {e}")
        if tmp_path is not None:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                logHandler.log.debug("Could not remove the temporary emoji cache file", exc_info=True)


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


def _apply_data(emoji_to_group, emoji_to_name):
    global _emoji_to_group, _emoji_to_name, _emoji_to_category, _emoji_set, _loaded
    _emoji_to_group = emoji_to_group
    _emoji_to_name = emoji_to_name
    _emoji_to_category = _build_category_map(emoji_to_group)
    _emoji_set = set(emoji_to_group.keys())
    # Set last: readers treat a True ``_loaded`` as "all four are in place".
    _loaded = True


def _background_download():
    global _downloading, _last_attempt_time
    try:
        emoji_to_group, emoji_to_name = _download_and_parse()
        if emoji_to_group:
            _save_to_cache(emoji_to_group, emoji_to_name)
            with _load_lock:
                _apply_data(emoji_to_group, emoji_to_name)
            logHandler.log.info(f"Loaded {len(emoji_to_group)} emoji from CLDR data")
        else:
            # A stale cache stays in use: only the refresh failed.
            logHandler.log.warning("Could not refresh CLDR emoji data; keeping the cached copy")
    finally:
        with _load_lock:
            _downloading = False
            _last_attempt_time = time.monotonic()


def _maybe_start_download(force=False):
    global _downloading
    with _load_lock:
        if _downloading:
            return
        if not force and (time.monotonic() - _last_attempt_time) < DOWNLOAD_RETRY_SECONDS:
            return
        _downloading = True
    threading.Thread(
        target=_background_download,
        name="AudioThemesEmojiCldr",
        daemon=True,
    ).start()


def _read_cache_once():
    global _cache_checked
    with _load_lock:
        if _cache_checked:
            return None, None, False
        emoji_to_group, emoji_to_name, timestamp = _load_from_cache()
        _cache_checked = True
    if not emoji_to_group:
        return None, None, False
    return emoji_to_group, emoji_to_name, _cache_is_stale(timestamp)


def load(force_refresh=False):
    """Load emoji data without ever blocking on the network.

    The on-disk cache is read synchronously (it is a small local file); a
    missing or older-than-60-days cache only schedules a background download.
    ``force_refresh`` keeps the current data and schedules a refresh.
    """
    if _loaded and not force_refresh:
        return True
    emoji_to_group = None
    emoji_to_name = None
    stale = False
    if not force_refresh:
        emoji_to_group, emoji_to_name, stale = _read_cache_once()
    if emoji_to_group:
        with _load_lock:
            _apply_data(emoji_to_group, emoji_to_name)
        if stale:
            _maybe_start_download()
        return True
    _maybe_start_download(force=force_refresh)
    return _loaded


def ensure_loaded():
    """Fast, non-blocking check used on the speech hot path."""
    if _loaded:
        return True
    return load()









def get_emoji_category(emoji_char):
    if not ensure_loaded():
        return None
    return _emoji_to_category.get(emoji_char)




def get_all_emoji():
    if not ensure_loaded():
        return set()
    return _emoji_set


