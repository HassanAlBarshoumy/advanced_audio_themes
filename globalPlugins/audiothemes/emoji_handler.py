import re
import config
import speech
from .handler import SpecialProps

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

_EMOJI_CATEGORY_RANGES = {
    EMOJI_CATEGORY_SMILEYS: re.compile(
        u"["
        u"\U0001F600-\U0001F64F"
        u"\u263A\u2639"
        u"\u2763-\u2764"
        u"\U0001F9D0-\U0001F9DF"
        u"]"
    ),
    EMOJI_CATEGORY_PEOPLE: re.compile(
        u"["
        u"\U0001F9B0-\U0001F9FF"
        u"\U0001F9D0-\U0001F9FF"
        u"\U0001F468-\U0001F487"
        u"\U0001F9CD-\U0001F9CF"
        u"\U0001F64B-\U0001F64F"
        u"\U0001F926"
        u"\U0001F937-\U0001F93A"
        u"\U0001F93C-\U0001F93E"
        u"\U0001F645-\U0001F647"
        u"\U0001F64B-\U0001F64F"
        u"\U0001F44A-\U0001F450"
        u"\U0001F440-\U0001F443"
        u"\U0001F444-\U0001F445"
        u"\U0001F446-\U0001F44F"
        u"\U0001F44A"
        u"]"
    ),
    EMOJI_CATEGORY_ANIMALS: re.compile(
        u"["
        u"\U0001F400-\U0001F43E"
        u"\U0001F980-\U0001F984"
        u"\U0001F985-\U0001F991"
        u"\U0001F992-\U0001F9A2"
        u"\U0001F9A5-\U0001F9AA"
        u"\U0001F9AE-\U0001F9B4"
        u"\U0001FAB0-\U0001FAB6"
        u"\U0001FAC0-\U0001FAC5"
        u"\U0001FABF"
        u"\U0001F490-\U0001F49F"
        u"\U00002600-\U00002604"
        u"\U00002614-\U00002615"
        u"\U0001F30E-\U0001F331"
        u"\U0001F332-\U0001F33F"
        u"\U0001F340-\U0001F345"
        u"\U0001F346-\U0001F34A"
        u"\U0001FAB0-\U0001FAB6"
        u"]"
    ),
    EMOJI_CATEGORY_FOOD: re.compile(
        u"["
        u"\U0001F32D-\U0001F32F"
        u"\U0001F330-\U0001F331"
        u"\U0001F336"
        u"\U0001F33D-\U0001F341"
        u"\U0001F343"
        u"\U0001F345-\U0001F353"
        u"\U0001F354-\U0001F35A"
        u"\U0001F35B-\U0001F363"
        u"\U0001F364-\U0001F36B"
        u"\U0001F36C-\U0001F37F"
        u"\U0001F9C0-\U0001F9C2"
        u"\U0001F9C3-\U0001F9CA"
        u"\U0001FAD0-\U0001FAD6"
        u"]"
    ),
    EMOJI_CATEGORY_TRAVEL: re.compile(
        u"["
        u"\U0001F680-\U0001F6C5"
        u"\U0001F6C6-\U0001F6CF"
        u"\U0001F6D0-\U0001F6D2"
        u"\U0001F6D5-\U0001F6D7"
        u"\U0001F6DD-\U0001F6DF"
        u"\U0001F6EB-\U0001F6EC"
        u"\U0001F6F3-\U0001F6F8"
        u"\U0001F6F9-\U0001F6FC"
        u"\U0001F30B-\U0001F30F"
        u"\U0001F310-\U0001F31F"
        u"\U00002668-\U0000266A"
        u"\U00002668-\U0000266A"
        u"\U000026F0-\U000026F5"
        u"\U000026F7-\U000026FA"
        u"\U000026FD"
        u"\U00002702"
        u"\U0001F6CE-\U0001F6CF"
        u"\U0001F6CC"
        u"\U0001F6CB"
        u"\U0001F6C0-\U0001F6C5"
        u"\U000026E9-\U000026EA"
        u"\U000026C4-\U000026C5"
        u"]"
    ),
    EMOJI_CATEGORY_ACTIVITIES: re.compile(
        u"["
        u"\U000026BD-\U000026BE"
        u"\U000026F1"
        u"\U000026F7-\U000026F9"
        u"\U000026FA"
        u"\U0001F3A0-\U0001F3B0"
        u"\U0001F3B1-\U0001F3C0"
        u"\U0001F3C2-\U0001F3F0"
        u"\U0001F3F4-\U0001F3FF"
        u"\U0001F6A3"
        u"\U0001F6B4-\U0001F6B6"
        u"\U0001F6F7"
        u"\U0001F938-\U0001F93E"
        u"\U0001F93C-\U0001F93E"
        u"\U0001F9D0-\U0001F9DF"
        u"\U0001F9E9-\U0001F9F1"
        u"\U0001F9F2-\U0001F9FB"
        u"\U0001FA70-\U0001FA73"
        u"\U0001FA80-\U0001FA82"
        u"\U0001FA90-\U0001FA95"
        u"\U000023F0"
        u"\U000023F3"
        u"\U000026E9-\U000026EA"
        u"\U000026F1"
        u"\U000026BD"
        u"]"
    ),
    EMOJI_CATEGORY_OBJECTS: re.compile(
        u"["
        u"\U0001F4A1-\U0001F4B0"
        u"\U0001F4B1-\U0001F4FC"
        u"\U0001F4FD-\U0001F4FF"
        u"\U0001F500-\U0001F53D"
        u"\U0001F550-\U0001F567"
        u"\U0001F5A5-\U0001F5FF"
        u"\U0001F6F8"
        u"\U0001F6F9-\U0001F6FC"
        u"\U0001F6E1-\U0001F6EB"
        u"\U0001F9E9-\U0001F9F1"
        u"\U0001F9F2-\U0001F9FB"
        u"\U0001FA70-\U0001FA74"
        u"\U0001FA78-\U0001FA7C"
        u"\U0001FA80-\U0001FA86"
        u"\U0001FA90-\U0001FAA8"
        u"\U0001FAB0-\U0001FAB6"
        u"\U0001FAC0-\U0001FAC5"
        u"\U0001FAD0-\U0001FAD6"
        u"\U0001FAE0-\U0001FAE8"
        u"\U0001FAF0-\U0001FAF8"
        u"\U0000231A-\U0000231B"
        u"\U000023E9-\U000023EC"
        u"\U000023F0"
        u"\U000023F3"
        u"\U0000260E"
        u"\U00002611"
        u"\U00002618"
        u"\U000026A1"
        u"]"
    ),
    EMOJI_CATEGORY_SYMBOLS: re.compile(
        u"["
        u"\U00002764"
        u"\U00002795-\U00002797"
        u"\U0000274C"
        u"\U0000274E"
        u"\U00002753-\U00002755"
        u"\U00002757"
        u"\U00002763-\U00002764"
        u"\U000027A1"
        u"\U000027B0"
        u"\U000027BF"
        u"\U00002B05-\U00002B07"
        u"\U00002B1B-\U00002B1C"
        u"\U00002B50"
        u"\U00002B55"
        u"\U00002600-\U00002604"
        u"\U0000260E"
        u"\U00002611"
        u"\U00002614-\U00002615"
        u"\U00002618"
        u"\U00002620"
        u"\U00002622-\U00002623"
        u"\U00002626"
        u"\U0000262A"
        u"\U0000262E-\U0000262F"
        u"\U00002638-\U0000263A"
        u"\U00002640-\U00002642"
        u"\U00002648-\U00002653"
        u"\U0000265F-\U00002660"
        u"\U00002663"
        u"\U00002665-\U00002666"
        u"\U00002668"
        u"\U0000267B"
        u"\U0000267E-\U0000267F"
        u"\U00002692-\U00002697"
        u"\U00002699"
        u"\U0000269B-\U0000269C"
        u"\U000026A0-\U000026A1"
        u"\U000026A7"
        u"\U000026AA-\U000026AB"
        u"\U000026B0-\U000026B1"
        u"\U000026C4-\U000026C5"
        u"\U000026C8"
        u"\U000026CE-\U000026CF"
        u"\U000026D1"
        u"\U000026D3-\U000026D4"
        u"\U000026E9-\U000026EA"
        u"\U000026F0-\U000026F5"
        u"\U000026F7-\U000026FA"
        u"\U000026FD"
        u"\U00002702"
        u"\U00002705"
        u"\U00002708-\U0000270D"
        u"\U0000270F"
        u"\U00002712"
        u"\U00002714"
        u"\U00002716"
        u"\U0000271D"
        u"\U00002721"
        u"\U00002728"
        u"\U00002733-\U00002734"
        u"\U00002744"
        u"\U00002747"
        u"\U000020E3"
        u"\U000000A9"
        u"\U000000AE"
        u"\U00002122"
        u"\U00002139"
        u"\U00002194-\U00002199"
        u"\U000021A9-\U000021AA"
        u"\U00002328"
        u"\U000023CF"
        u"\U000023E9-\U000023F3"
        u"\U000023F8-\U000023FA"
        u"\U000024C2"
        u"\U000025AA-\U000025AB"
        u"\U000025B6"
        u"\U000025C0"
        u"\U000025FB-\U000025FE"
        u"\U00002600-\U000027BF"
        u"\U00002934-\U00002935"
        u"\U00002B05-\U00002B55"
        u"\U00003030"
        u"\U0000303D"
        u"\U00003297"
        u"\U00003299"
        u"]"
    ),
    EMOJI_CATEGORY_FLAGS: re.compile(
        u"["
        u"\U0001F3F3-\U0001F3F4"
        u"\U0001F3C1"
        u"\U0001F6A9"
        u"\U0001F38C-\U0001F38D"
        u"\U0001F3FB-\U0001F3FF"
        u"]"
        u"|[\U0001F1E6-\U0001F1FF]{2}"
    ),
}

FLAGS_REGIONAL_INDICATOR = re.compile(
    u"[\U0001F1E6-\U0001F1FF]{2}"
)


def _category_for_codepoint(ch):
    if FLAGS_REGIONAL_INDICATOR.match(ch):
        return EMOJI_CATEGORY_FLAGS
    cp = ord(ch[0])
    for cat, cr in _EMOJI_CATEGORY_RANGES.items():
        if cr.match(ch):
            return cat
    if 0x1F1E6 <= cp <= 0x1F1FF:
        return EMOJI_CATEGORY_FLAGS
    if 0x1F3FB <= cp <= 0x1F3FF:
        return EMOJI_CATEGORY_PEOPLE
    return EMOJI_CATEGORY_SMILEYS


def find_emojis(text):
    matches = []
    for m in _emoji_re.finditer(text):
        emoji = m.group(0)
        cat = _category_for_codepoint(emoji)
        matches.append((emoji, cat, m.start(), m.end()))
    return matches


def process_emoji_in_text(text):
    emojis = find_emojis(text)
    if not emojis:
        return None
    return emojis


def is_emoji_enabled():
    return config.conf["audiothemes"].get("emoji_enabled", True)


def is_emoji_sound_enabled():
    return config.conf["audiothemes"].get("emoji_sound", True)


def is_emoji_prefix_enabled():
    return config.conf["audiothemes"].get("emoji_prefix", True)


def get_emoji_prefix_text():
    return config.conf["audiothemes"].get("emoji_prefix_text", "emoji")


def get_emoji_volume():
    return config.conf["audiothemes"].get("emoji_volume", 20)


def get_emoji_position():
    return config.conf["audiothemes"].get("emoji_position", "before")


def get_emoji_repeat():
    return config.conf["audiothemes"].get("emoji_repeat", "per_emoji")


def is_category_enabled(cat):
    key = {
        EMOJI_CATEGORY_SMILEYS: "emoji_cat_smileys",
        EMOJI_CATEGORY_PEOPLE: "emoji_cat_people",
        EMOJI_CATEGORY_ANIMALS: "emoji_cat_animals",
        EMOJI_CATEGORY_FOOD: "emoji_cat_food",
        EMOJI_CATEGORY_TRAVEL: "emoji_cat_travel",
        EMOJI_CATEGORY_ACTIVITIES: "emoji_cat_activities",
        EMOJI_CATEGORY_OBJECTS: "emoji_cat_objects",
        EMOJI_CATEGORY_SYMBOLS: "emoji_cat_symbols",
        EMOJI_CATEGORY_FLAGS: "emoji_cat_flags",
    }.get(cat)
    if key is None:
        return True
    return config.conf["audiothemes"].get(key, True)
