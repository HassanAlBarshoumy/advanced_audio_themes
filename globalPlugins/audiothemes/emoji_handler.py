import json
import re
import config
import speech
from functools import lru_cache
from .handler import SpecialProps
from . import emoji_cldr_data

_DEFAULT_EMOJI_CONFIG = {
    "emoji_enabled": True,
    "emoji_sound": True,
    "emoji_prefix": True,
    "emoji_prefix_text": "emoji",
    "emoji_suffix_text": "emoji",
    "emoji_volume": 20,
    "emoji_position": "before",
    "emoji_sound_position": "before",
    "emoji_repeat": "per_emoji",
    "emoji_sound_repeat": "per_emoji",
    "emoji_prefix_repeat": "per_emoji",
    "emoji_delay_before": 0,
    "emoji_delay_after": 0,
    "emoji_suppress_role_sound": False,
    "emoji_blacklist": "",
    "emoji_sound_cat_smileys": True,
    "emoji_sound_cat_people": True,
    "emoji_sound_cat_animals": True,
    "emoji_sound_cat_food": True,
    "emoji_sound_cat_travel": True,
    "emoji_sound_cat_activities": True,
    "emoji_sound_cat_objects": True,
    "emoji_sound_cat_symbols": True,
    "emoji_sound_cat_flags": True,
    "emoji_cat_smileys": True,
    "emoji_cat_people": True,
    "emoji_cat_animals": True,
    "emoji_cat_food": True,
    "emoji_cat_travel": True,
    "emoji_cat_activities": True,
    "emoji_cat_objects": True,
    "emoji_cat_symbols": True,
    "emoji_cat_flags": True,
    "emoji_prefix_text_per_category": "{}",
    "emoji_suffix_text_per_category": "{}",
    "emoji_volume_per_category": "{}",
    "emoji_sound_position_per_category": "{}",
    "emoji_custom_descriptions": "{}",
}

_cached_emoji_config = dict(_DEFAULT_EMOJI_CONFIG)
_cached_json_configs = {}

def refreshCachedConfig():
    global _cached_emoji_config, _cached_json_configs
    _cached_emoji_config = dict(_DEFAULT_EMOJI_CONFIG)
    ac = config.conf["audiothemes"]
    for key in _cached_emoji_config:
        _cached_emoji_config[key] = ac.get(key, _cached_emoji_config[key])
    try:
        _cached_emoji_config["emoji_delay_before"] = int(_cached_emoji_config["emoji_delay_before"])
    except (ValueError, TypeError):
        _cached_emoji_config["emoji_delay_before"] = 0
    try:
        _cached_emoji_config["emoji_delay_after"] = int(_cached_emoji_config["emoji_delay_after"])
    except (ValueError, TypeError):
        _cached_emoji_config["emoji_delay_after"] = 0
    _cached_json_configs = {}
    for key in ("emoji_prefix_text_per_category", "emoji_suffix_text_per_category",
                "emoji_volume_per_category", "emoji_sound_position_per_category",
                "emoji_custom_descriptions"):
        raw = _cached_emoji_config.get(key, "{}")
        try:
            _cached_json_configs[key] = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            _cached_json_configs[key] = {}

EMOJI_CATEGORY_SMILEYS = 0
EMOJI_CATEGORY_PEOPLE = 1
EMOJI_CATEGORY_ANIMALS = 2
EMOJI_CATEGORY_FOOD = 3
EMOJI_CATEGORY_TRAVEL = 4
EMOJI_CATEGORY_ACTIVITIES = 5
EMOJI_CATEGORY_OBJECTS = 6
EMOJI_CATEGORY_SYMBOLS = 7
EMOJI_CATEGORY_FLAGS = 8

CATEGORY_NAMES = {
    EMOJI_CATEGORY_SMILEYS: "smileys",
    EMOJI_CATEGORY_PEOPLE: "people",
    EMOJI_CATEGORY_ANIMALS: "animals",
    EMOJI_CATEGORY_FOOD: "food",
    EMOJI_CATEGORY_TRAVEL: "travel",
    EMOJI_CATEGORY_ACTIVITIES: "activities",
    EMOJI_CATEGORY_OBJECTS: "objects",
    EMOJI_CATEGORY_SYMBOLS: "symbols",
    EMOJI_CATEGORY_FLAGS: "flags",
}

_ZWJ = u"\u200D"
_VS = u"\uFE0F"
_KEYCAP = u"\u20E3"

REGIONAL_INDICATOR_RANGE = (
    (0x1F1E6, 0x1F1FF),
)

_EMOJI_SEQUENCE_PATTERNS = [
    re.compile(
        u"("
        u"["
        u"\U0001F600-\U0001F64F"  
        u"\U0001F300-\U0001F5FF"  
        u"\U0001F680-\U0001F6FF"  
        u"\U0001F900-\U0001F9FF"  
        u"\U0001FA00-\U0001FA6F"  
        u"\U0001FA70-\U0001FAFF"  
        u"\U00002600-\U000026FF"  
        u"\U00002700-\U000027BF"  
        u"\U00002300-\U000023FF"  
        u"\U000024C2-\U000024C2"  
        u"\U000025AA-\U000025FF"  
        u"\U00002B05-\U00002B55"  
        u"\U00002934-\U00002935"  
        u"\u00A9\u00AE"  
        u"\u2122\u2139"  
        u"\u2194-\u2199"  
        u"\u21A9-\u21AA"  
        u"\u231A-\u231B"  
        u"\u2328\u23CF"  
        u"\u23E9-\u23F3"  
        u"\u23F8-\u23FA"  
        u"\u24C2\u25B6\u25C0"  
        u"\u25FB-\u25FE"  
        u"\u2600-\u2604"  
        u"\u260E\u2611"  
        u"\u2614-\u2615"  
        u"\u2618\u261D"  
        u"\u2620\u2622\u2623\u2626\u262A\u262E\u262F"  
        u"\u2638-\u263A"  
        u"\u2640\u2642"  
        u"\u2648-\u2653"  
        u"\u265F\u2660\u2663\u2665\u2666\u2668"  
        u"\u267B\u267E\u267F"  
        u"\u2692-\u2697"  
        u"\u2699\u269B\u269C"  
        u"\u26A0-\u26A1"  
        u"\u26A7\u26AA-\u26AB"  
        u"\u26B0-\u26B1"  
        u"\u26BD-\u26BE"  
        u"\u26C4-\u26C5"  
        u"\u26C8\u26CE\u26CF"  
        u"\u26D1\u26D3\u26D4"  
        u"\u26E9\u26EA"  
        u"\u26F0-\u26F5"  
        u"\u26F7-\u26FA"  
        u"\u26FD\u2702"  
        u"\u2705\u2708-\u270D"  
        u"\u270F\u2712"  
        u"\u2714\u2716"  
        u"\u271D\u2721"  
        u"\u2728\u2733-\u2734"  
        u"\u2744\u2747"  
        u"\u274C\u274E"  
        u"\u2753-\u2755"  
        u"\u2757\u2763-\u2764"  
        u"\u2795-\u2797"  
        u"\u27A1\u27B0\u27BF"  
        u"\u2934\u2935"  
        u"\u2B05-\u2B07"  
        u"\u2B1B-\u2B1C"  
        u"\u2B50\u2B55"  
        u"\u3030\u303D"  
        u"\u3297\u3299"  
        u"]"
        u"[\uFE0F\u200D]?"
        u"(?:[\U0001F3FB-\U0001F3FF])?"
        u"(?:\u200D["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F900-\U0001F9FF"
        u"\U0001FA00-\U0001FA6F"
        u"\U00002600-\U000026FF"
        u"\U00002700-\U000027BF"
        u"\u2764"
        u"\u2B1B"
        u"]?"
        u")?)+"
    ),
    re.compile(
        u"["
        u"\U0001F1E6-\U0001F1FF"
        u"]{2}"
    ),
    re.compile(
        u"["
        u"0-9#*"
        u"]\uFE0F\u20E3"
    ),
]

_emoji_re = re.compile("|".join(p.pattern for p in _EMOJI_SEQUENCE_PATTERNS))

FLAGS_REGIONAL_INDICATOR = re.compile(
    u"[\U0001F1E6-\U0001F1FF]{2}"
)


@lru_cache(maxsize=512)
def _get_emoji_category(emoji_str):
    """Get category for an emoji using CLDR data first, then fallback to range-based detection."""
    cat = emoji_cldr_data.get_emoji_category(emoji_str)
    if cat is not None:
        return cat
    return _fallback_category(emoji_str)


_EMOJI_RANGES = [
    (EMOJI_CATEGORY_SMILEYS, [(0x1F600, 0x1F64F), (0x2639, 0x263A), (0x2763, 0x2764)]),
    (EMOJI_CATEGORY_PEOPLE, [(0x1F468, 0x1F487), (0x1F44A, 0x1F450), (0x1F440, 0x1F445), (0x1F9B0, 0x1F9FF)]),
    (EMOJI_CATEGORY_ANIMALS, [(0x1F400, 0x1F43E), (0x1F980, 0x1F9AA), (0x1FAB0, 0x1FAC5)]),
    (EMOJI_CATEGORY_FOOD, [(0x1F32D, 0x1F37F), (0x1F9C0, 0x1F9CA), (0x1FAD0, 0x1FAD6)]),
    (EMOJI_CATEGORY_TRAVEL, [(0x1F680, 0x1F6C5), (0x1F30B, 0x1F31F), (0x26C4, 0x26C5), (0x26F0, 0x26F5)]),
    (EMOJI_CATEGORY_ACTIVITIES, [(0x1F3A0, 0x1F3F0), (0x26BD, 0x26BE), (0x1F9E9, 0x1F9FB)]),
    (EMOJI_CATEGORY_OBJECTS, [(0x1F4A1, 0x1F53D), (0x1F550, 0x1F567), (0x1F5A5, 0x1F5FF), (0x231A, 0x231B), (0x23E9, 0x23F3)]),
    (EMOJI_CATEGORY_SYMBOLS, [(0x2600, 0x27BF), (0x2934, 0x2935), (0x2B05, 0x2B55), (0x00A9, 0x00AE), (0x2122, 0x2139)]),
    (EMOJI_CATEGORY_FLAGS, [(0x1F3F3, 0x1F3F4), (0x1F1E6, 0x1F1FF)]),
]

_CATEGORY_CONFIG_KEYS = {
    EMOJI_CATEGORY_SMILEYS: "emoji_cat_smileys",
    EMOJI_CATEGORY_PEOPLE: "emoji_cat_people",
    EMOJI_CATEGORY_ANIMALS: "emoji_cat_animals",
    EMOJI_CATEGORY_FOOD: "emoji_cat_food",
    EMOJI_CATEGORY_TRAVEL: "emoji_cat_travel",
    EMOJI_CATEGORY_ACTIVITIES: "emoji_cat_activities",
    EMOJI_CATEGORY_OBJECTS: "emoji_cat_objects",
    EMOJI_CATEGORY_SYMBOLS: "emoji_cat_symbols",
    EMOJI_CATEGORY_FLAGS: "emoji_cat_flags",
}

def _fallback_category(emoji_str):
    """Fallback category detection for emoji not in CLDR data."""
    if FLAGS_REGIONAL_INDICATOR.match(emoji_str):
        return EMOJI_CATEGORY_FLAGS
    cp = ord(emoji_str[0])
    for cat, ranges in _EMOJI_RANGES:
        for lo, hi in ranges:
            if lo <= cp <= hi:
                return cat
    if 0x1F3FB <= cp <= 0x1F3FF:
        return EMOJI_CATEGORY_PEOPLE
    return EMOJI_CATEGORY_SMILEYS


_cldr_index = None

def _ensure_cldr_index():
    global _cldr_index
    if _cldr_index is not None:
        return
    all_cldr = emoji_cldr_data.get_all_emoji()
    if not all_cldr:
        return
    _cldr_index = {}
    for emo in all_cldr:
        _cldr_index.setdefault(emo[0], []).append(emo)
    for lst in _cldr_index.values():
        lst.sort(key=len, reverse=True)

_has_cldr_data = None
def find_emojis(text):
    global _has_cldr_data
    matches = []
    for m in _emoji_re.finditer(text):
        emoji = m.group(0)
        cat = _get_emoji_category(emoji)
        matches.append((emoji, cat, m.start(), m.end()))
    if _has_cldr_data is None:
        all_cldr = emoji_cldr_data.get_all_emoji()
        _has_cldr_data = bool(all_cldr)
    if not _has_cldr_data:
        return matches
    covered = bytearray(len(text))
    for _, _, start, end in matches:
        for i in range(start, end):
            covered[i] = 1
    _ensure_cldr_index()
    i = 0
    while i < len(text):
        if covered[i]:
            i += 1
            continue
        found = False
        candidates = _cldr_index.get(text[i])
        if candidates:
            for emoji in candidates:
                elen = len(emoji)
                if i + elen <= len(text) and text[i:i+elen] == emoji:
                    cat = _get_emoji_category(emoji)
                    matches.append((emoji, cat, i, i+elen))
                    for j in range(i, i+elen):
                        covered[j] = 1
                    i += elen
                    found = True
                    break
        if not found:
            i += 1
    matches.sort(key=lambda x: x[2])
    return matches


def process_emoji_in_text(text):
    emojis = find_emojis(text)
    if not emojis:
        return None
    return emojis


def is_emoji_enabled():
    return _cached_emoji_config["emoji_enabled"]


def is_emoji_sound_enabled():
    return _cached_emoji_config["emoji_sound"]


def is_emoji_prefix_enabled():
    return _cached_emoji_config["emoji_prefix"]


def get_emoji_prefix_text():
    return _cached_emoji_config["emoji_prefix_text"]


def get_emoji_suffix_text():
    return _cached_emoji_config["emoji_suffix_text"]


def get_emoji_volume():
    return _cached_emoji_config["emoji_volume"]


def get_emoji_position():
    return _cached_emoji_config["emoji_position"]


def get_emoji_sound_position():
    return _cached_emoji_config["emoji_sound_position"]


def get_emoji_repeat():
    return _cached_emoji_config["emoji_repeat"]


CATEGORY_TO_PROP = {
    EMOJI_CATEGORY_SMILEYS: SpecialProps.emoji_smileys,
    EMOJI_CATEGORY_PEOPLE: SpecialProps.emoji_people,
    EMOJI_CATEGORY_ANIMALS: SpecialProps.emoji_animals,
    EMOJI_CATEGORY_FOOD: SpecialProps.emoji_food,
    EMOJI_CATEGORY_TRAVEL: SpecialProps.emoji_travel,
    EMOJI_CATEGORY_ACTIVITIES: SpecialProps.emoji_activities,
    EMOJI_CATEGORY_OBJECTS: SpecialProps.emoji_objects,
    EMOJI_CATEGORY_SYMBOLS: SpecialProps.emoji_symbols,
    EMOJI_CATEGORY_FLAGS: SpecialProps.emoji_flags,
}


def get_special_prop_for_category(cat):
    return CATEGORY_TO_PROP.get(cat, SpecialProps.emoji)


def get_emoji_sound_repeat():
    return _cached_emoji_config["emoji_sound_repeat"]


def get_emoji_prefix_repeat():
    return _cached_emoji_config["emoji_prefix_repeat"]


def is_emoji_sound_category_enabled(cat):
    key = "emoji_sound_cat_" + CATEGORY_NAMES.get(cat, "smileys")
    return _cached_emoji_config.get(key, True)


def _get_json_config(key, default="{}"):
    result = _cached_json_configs.get(key)
    if result is not None:
        return result
    val = _cached_emoji_config.get(key, default)
    try:
        return json.loads(val) if isinstance(val, str) else val
    except (json.JSONDecodeError, TypeError):
        return {}


def get_emoji_prefix_text_for_category(cat):
    per_cat = _get_json_config("emoji_prefix_text_per_category")
    return per_cat.get(CATEGORY_NAMES.get(cat, "")) or get_emoji_prefix_text()


def get_emoji_suffix_text_for_category(cat):
    per_cat = _get_json_config("emoji_suffix_text_per_category")
    return per_cat.get(CATEGORY_NAMES.get(cat, "")) or get_emoji_suffix_text()


def get_emoji_volume_for_category(cat):
    per_cat = _get_json_config("emoji_volume_per_category")
    val = per_cat.get(CATEGORY_NAMES.get(cat))
    return val if val is not None else get_emoji_volume()


def get_emoji_sound_position_for_category(cat):
    per_cat = _get_json_config("emoji_sound_position_per_category")
    val = per_cat.get(CATEGORY_NAMES.get(cat))
    return val if val is not None else get_emoji_sound_position()


def get_emoji_delay_before():
    return _cached_emoji_config["emoji_delay_before"]


def get_emoji_delay_after():
    return _cached_emoji_config["emoji_delay_after"]


def is_emoji_suppress_role_sound():
    return _cached_emoji_config["emoji_suppress_role_sound"]


def is_emoji_blacklisted(emoji_char):
    raw = _cached_emoji_config["emoji_blacklist"]
    return emoji_char in raw


def get_emoji_custom_description(emoji_char):
    descs = _get_json_config("emoji_custom_descriptions")
    return descs.get(emoji_char)


def is_category_enabled(cat):
    key = _CATEGORY_CONFIG_KEYS.get(cat)
    if key is None:
        return True
    return _cached_emoji_config.get(key, True)
