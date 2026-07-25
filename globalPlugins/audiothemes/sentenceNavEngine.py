# -*- coding: UTF-8 -*-
# SentenceNav engine — integrated into Audio Themes NG
# Original: SentenceNav addon by Tony Malykh
# Copyright (C) 2018-2019 Tony Malykh
# This file is covered by the GNU General Public License.
# Integrated and adapted by Hassan AlBarshoumy

import addonHandler
try:
    addonHandler.initTranslation()
except AttributeError:
    pass
import api
import bisect
import braille
import config
import controlTypes
import ctypes
import functools
import globalPluginHandler
import gui
from gui.settingsDialogs import SettingsPanel
import json
import NVDAHelper
from NVDAObjects.window import winword
import operator
import re
import review
import vision
from scriptHandler import script, willSayAllResume
import speech
import struct
import textInfos
import tones
import ui
import wx
from logHandler import log

_cached_doc_formatting = {}
_cached_sentencenav_config = {}
_sn_cached_chime_volume = 10
_sn_cached_paragraph_chime_volume = 10

def _refresh_doc_formatting():
    global _cached_doc_formatting, _sn_cached_chime_volume, _sn_cached_paragraph_chime_volume
    global _cached_sentencenav_config
    try:
        _cached_doc_formatting = config.conf["documentFormatting"]
    except Exception:
        _cached_doc_formatting = {}
    try:
        _sn_cached_chime_volume = config.conf["sentencenav"]["noNextSentenceChimeVolume"]
    except Exception:
        _sn_cached_chime_volume = 10
    try:
        _sn_cached_paragraph_chime_volume = config.conf["sentencenav"]["paragraphChimeVolume"]
    except Exception:
        _sn_cached_paragraph_chime_volume = 10
    try:
        sn = config.conf["sentencenav"]
        _cached_sentencenav_config = {k: sn[k] for k in sn}
    except Exception:
        _cached_sentencenav_config = {}

# --- Compatibility shims for NVDA 2024+ / 2026+ ---
try:
    REASON_CARET = controlTypes.REASON_CARET
except AttributeError:
    REASON_CARET = controlTypes.OutputReason.CARET

try:
    ROLE_COMBOBOX = controlTypes.ROLE_COMBOBOX
    ROLE_LISTITEM = controlTypes.ROLE_LISTITEM
    ROLE_BUTTON = controlTypes.ROLE_BUTTON
except AttributeError:
    ROLE_COMBOBOX = controlTypes.Role.COMBOBOX
    ROLE_LISTITEM = controlTypes.Role.LISTITEM
    ROLE_BUTTON = controlTypes.Role.BUTTON

try:
    from sayAllHandler import CURSOR_CARET
except Exception:
    from speech import sayAll
    CURSOR_CARET = sayAll.CURSOR.CARET


# ──────────────────────────────────────────────
#  Configuration
# ──────────────────────────────────────────────

def initSentenceNavConfiguration():
    exceptionalAbbreviations = """
{
    "en": "Mr Ms Mrs Dr St e.g",
    "ru": "Тов тов",
    "ar": "Mr Ms Mrs Dr St e.g"
}
""".replace("\n", " ")
    capitalLetters = """
{
    "en": "A-Z",
    "ru": "А-Я",
    "ar": "A-Z"
}
""".replace("\n", " ")
    lowerCaseLetters = """
{
    "en": "a-z",
    "ru": "а-я",
    "ar": "a-z"
}
""".replace("\n", " ")
    confspec = {
        "paragraphChimeVolume": "integer( default=0, min=0, max=100)",
        "noNextSentenceChimeVolume": "integer( default=0, min=0, max=100)",
        "noNextSentenceMessage": "boolean( default=False)",
        "speakFormatted": "boolean( default=True)",
        "textCrackleVolume": "integer( default=0, min=0, max=100)",
        "noNextTextChimeVolume": "integer( default=0, min=0, max=100)",
        "noNextTextMessage": "boolean( default=False)",
        "reconstructMode": "string( default='sameIndent')",
        "breakOnWikiReferences": "boolean( default=True)",
        "sentenceBreakers": "string( default='.!?')",
        "fullWidthSentenceBreakers": "string( default='。！？')",
        "skippable": "string( default='\"\\u201d\\u00bb)')",
        "exceptionalAbbreviations": "string( default='%s')" % exceptionalAbbreviations,
        "capitalLetters": "string( default='%s')" % capitalLetters,
        "lowerCaseLetters": "string( default='%s')" % lowerCaseLetters,
        "phraseBreakers": "string( default='.!?,;:-\\u2013()')",
        "fullWidthPhraseBreakers": "string( default='\\u3002\\uff01\\uff1f\\uff0c\\uff1b\\uff1a\\uff08\\uff09')",
        "applicationsBlacklist": "string( default='audacity,excel')",
        "enableInWord": "boolean( default=False)",
        "breakAtElementBoundaries": "boolean( default=True)",
    }
    config.conf.spec["sentencenav"] = confspec


def getSNConfig(key, lang=None):
    try:
        value = _cached_sentencenav_config[key]
    except KeyError:
        value = config.conf["sentencenav"][key]
    if lang is None:
        return value
    try:
        dictionary = json.loads(value)
    except Exception:
        # User might have corrupted the JSON string via the settings UI, fallback gracefully
        dictionary = {"en": str(value)}
    try:
        return dictionary[lang]
    except KeyError:
        return dictionary.get("en", "")


def setSNConfig(key, value, lang):
    fullValue = config.conf["sentencenav"][key]
    try:
        dictionary = json.loads(fullValue)
    except Exception:
        dictionary = {}
    dictionary[lang] = value
    config.conf["sentencenav"][key] = json.dumps(dictionary)


def getCurrentLanguage():
    s = speech.getCurrentLanguage()
    return s[:2]


# ──────────────────────────────────────────────
#  Utility helpers
# ──────────────────────────────────────────────

def sign(x):
    if x > 0:
        return 1
    elif x < 0:
        return -1
    return 0


def myAssert(condition):
    if not condition:
        raise RuntimeError("Assertion failed")


def countCharacters(textInfo):
    try:
        return len(textInfo.text)
    except AttributeError:
        pass
    try:
        myAssert(len(list(textInfo._getTextInfos())) == 1)
        return countCharacters(list(textInfo._getTextInfos())[0])
    except AttributeError:
        pass
    try:
        myAssert(textInfo._start == textInfo._end)
        return countCharacters(textInfo._start)
    except AttributeError:
        pass
    raise RuntimeError("Unable to count characters for %s" % str(textInfo))


def getCaretIndexWithinParagraph(caretTextInfo):
    paragraphTextInfo = caretTextInfo.copy()
    paragraphTextInfo.expand(textInfos.UNIT_PARAGRAPH)
    preInfo = paragraphTextInfo.copy()
    preInfo.setEndPoint(caretTextInfo, "endToStart")
    return (countCharacters(preInfo), paragraphTextInfo)


def preprocessNewLines(s):
    s = s.replace("\r\n", "\n")
    s = s.replace("\r", "\n")
    return s.replace("\n", " ")


# ──────────────────────────────────────────────
#  Context — paragraph caching for sentence parsing
# ──────────────────────────────────────────────

def _getElementBoundaries(textInfo):
    """Return positions in textInfo.text that separate VB child elements.

    Uses two methods for reliability:
    1. Scans the original text for \\n (inserted by VB between sibling nodes).
    2. Falls back to _getTextInfos() for inline boundaries without \\n.
    Positions are in RAW text (preprocessNewLines not applied).
    """
    if not getSNConfig("breakAtElementBoundaries"):
        return []
    text = textInfo.text
    # Normalize line endings so positions match preprocessNewLines output
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    # Method 1: \\n positions (most reliable for VB)
    newlinePositions = [i for i, ch in enumerate(normalized) if ch == '\n']
    boundaries = [p for p in newlinePositions if 0 < p < len(text)]
    # Method 2: inline element boundaries (no \\n, e.g. <b>, <a> within a line)
    if hasattr(textInfo, "_getTextInfos"):
        try:
            subInfos = list(textInfo._getTextInfos())
            if len(subInfos) > 1:
                pos = 0
                for i, sub in enumerate(subInfos):
                    pos += len(sub.text)
                    if i < len(subInfos) - 1 and pos > 0:
                        # Avoid duplicating a \\n-based boundary already found
                        if pos not in boundaries:
                            boundaries.append(pos)
        except Exception:
            pass
    return sorted(set(boundaries))

class Context:
    def __init__(self, textInfo, caretIndex, caretInfo=None):
        self.texts = [preprocessNewLines(textInfo.text)]
        self.textInfos = [textInfo]
        self.caretIndex = caretIndex
        self.caretInfo = caretInfo
        self.current = 0

    def addParagraph(self, index, textInfo):
        if index >= 0:
            self.textInfos.insert(index, textInfo)
            self.texts.insert(index, preprocessNewLines(textInfo.text))
        else:
            self.textInfos.append(textInfo)
            self.texts.append(preprocessNewLines(textInfo.text))
        if (index >= 0) and (self.current >= index):
            self.current += 1

    def makeTextInfo(self, paragraphInfo, offset):
        index = self.textInfos.index(paragraphInfo)
        if index != self.current or self.caretInfo is None:
            info = paragraphInfo.copy()
            text = self.texts[index]
            if len(text) == offset:
                info.collapse(end=True)
                return info
            info.collapse()
            result = info.move(textInfos.UNIT_CHARACTER, offset)
            if (offset > 0) and (result == 0):
                raise Exception("Unexpected! Failed to move!")
            return info
        info = self.caretInfo.copy()
        info.move(textInfos.UNIT_CHARACTER, offset - self.caretIndex)
        return info

    def makeSentenceInfo(self, startTi, startOffset, endTi, endOffset):
        start = self.makeTextInfo(startTi, startOffset)
        end = self.makeTextInfo(endTi, endOffset)
        if endOffset == len(startTi.text):
            start.move(textInfos.UNIT_CHARACTER, endOffset - startOffset, endPoint='end')
        else:
            start.setEndPoint(end, "endToEnd")
        return start

    def isTouchingBoundary(self, direction, startTi, startOffset, endTi, endOffset):
        if (
            (direction > 0 and endTi == self.textInfos[-1] and endOffset == len(self.texts[-1]))
            or (direction < 0 and startTi == self.textInfos[0] and startOffset == 0)
        ):
            return True
        return False

    def findByOffset(self, paragraphInfo, offset):
        index = self.textInfos.index(paragraphInfo)
        if offset < 0:
            if index == 0:
                raise Exception("Impossible!")
            self.current = index - 1
            self.caretIndex = len(self.texts[index - 1]) - 1
            self.caretInfo = None
        else:
            self.current = index
            self.caretIndex = offset
            self.caretInfo = None

    def find(self, textInfo):
        which = "start"
        for i in range(len(self.textInfos)):
            if textInfo.compareEndPoints(self.textInfos[i], which + "ToStart") >= 0:
                if textInfo.compareEndPoints(self.textInfos[i], which + "ToEnd") < 0:
                    self.current = i
                    indexTextInfo = self.textInfos[i].copy()
                    indexTextInfo.setEndPoint(textInfo, "endTo" + which.capitalize())
                    self.caretIndex = countCharacters(indexTextInfo)
                    self.caretInfo = textInfo
                    return
        raise RuntimeError("Could not find textInfo in this context.")


# ──────────────────────────────────────────────
#  Regex builders
# ──────────────────────────────────────────────

def re_grp(s):
    return "(?:%s)" % s

def re_set(s, allowRanges=False):
    for c in "\\[]":
        s = s.replace(c, "\\" + c)
    if not allowRanges:
        if "-" in s:
            s = "-" + s.replace("-", "")
    return "[" + s + "]"

def re_escape(s):
    for c in "\\.?*()[]{}$^":
        s = s.replace(c, "\\" + c)
    return s

def nlb(s):
    return u"(?<!" + s + u"(?=[.]))"

def nla(s):
    return f"(?!{s})"


regexCache = {}

def getRegex(lang):
    try:
        return regexCache[lang]
    except KeyError:
        pass
    regex = u""
    regex += nlb("\\b" + re_set(getSNConfig("capitalLetters", lang), allowRanges=True))
    for abbr in getSNConfig("exceptionalAbbreviations", lang).strip().split():
        regex += nlb(re_escape(abbr))
    breakers = getSNConfig("sentenceBreakers")
    if "." in breakers:
        breakers = [breakers.replace(".", ""), "."]
    else:
        breakers = [breakers]
    rrr = []
    for bi in range(len(breakers)):
        rr = re_set(breakers[bi]) + "+"
        rr += re_set(getSNConfig("skippable")) + "*"
        if getSNConfig("breakOnWikiReferences"):
            wikiReference = re_grp("\\[[\\w\\s]+\\]")
            rr += wikiReference + "*"
        rr += "\\s+"
        if bi == 1:
            rr += nla(re_set(getSNConfig("lowerCaseLetters", lang), allowRanges=True))
        rrr.append(rr)
    regex += re_grp("|".join(rrr))
    fullWidth = re_set(getSNConfig("fullWidthSentenceBreakers"))
    doubleNewLine = re_grp("\n\\s*")
    doubleNewLine = "%s{2,}" % doubleNewLine
    regex = u"^|{regex}|{fullWidth}+\\s*|{doubleNewLine}|\\s*$".format(
        regex=regex, fullWidth=re_grp(fullWidth), doubleNewLine=re_grp(doubleNewLine))
    try:
        result = re.compile(regex, re.UNICODE)
    except Exception:
        ui.message("Couldn't compile regular expression for sentences")
        raise
    regexCache[lang] = result
    return result


phraseRegex = None

def getPhraseRegex():
    global phraseRegex
    if phraseRegex is not None:
        return phraseRegex
    regex = u""
    regex += re_set(getSNConfig("phraseBreakers")) + "+"
    regex += "\\s+"
    fullWidth = re_set(getSNConfig("fullWidthPhraseBreakers"))
    doubleNewLine = re_grp("\n\\s*")
    doubleNewLine = "%s{2,}" % doubleNewLine
    regex = u"^|{regex}|{fullWidth}+\\s*|{doubleNewLine}|\\s*$".format(
        regex=regex, fullWidth=re_grp(fullWidth), doubleNewLine=re_grp(doubleNewLine))
    try:
        result = re.compile(regex, re.UNICODE)
    except Exception:
        ui.message("Couldn't compile regular expression for phrases")
        raise
    phraseRegex = result
    return result

def clearRegexCaches():
    global phraseRegex
    regexCache.clear()
    phraseRegex = None

_sentence_nav_registrations = []
try:
    from config import post_configSave, post_configReset, post_configProfileSwitch
    _sentence_nav_registrations.append(post_configSave.register(clearRegexCaches))
    _sentence_nav_registrations.append(post_configReset.register(clearRegexCaches))
    _sentence_nav_registrations.append(post_configProfileSwitch.register(clearRegexCaches))
except (ImportError, AttributeError):
    pass

def _unregister_sentence_nav_hooks():
    try:
        from config import post_configSave, post_configReset, post_configProfileSwitch
        for action in (post_configSave, post_configReset, post_configProfileSwitch):
            try:
                action.unregister(clearRegexCaches)
            except (ValueError, AttributeError):
                pass
    except ImportError:
        pass


# ──────────────────────────────────────────────
#  SentenceNavMixin — to be inherited by the main GlobalPlugin
# ──────────────────────────────────────────────

class SentenceNavMixin:
    """
    Mixin providing SentenceNav's sentence & phrase navigation.
    Inherit alongside globalPluginHandler.GlobalPlugin.
    """

    @functools.lru_cache(maxsize=100)
    def splitParagraphIntoSentences(text, regex):
        result = [m.end() for m in regex.finditer(text)]
        def slideForward(i):
            if i == 0:
                return i
            while i < len(text) and text[i].isspace():
                i += 1
            return i
        result = map(slideForward, result)
        result = sorted(list(set(result)))
        return result

    def findCurrentSentence(self, context, regex):
        texts = context.texts
        tis = context.textInfos
        n = len(texts)
        myAssert(n == len(tis))
        joinString = "\n"
        s = joinString.join(texts)
        index = sum([len(texts[t]) for t in range(context.current)]) + len(joinString) * context.current + context.caretIndex
        parStartIndices = [0]
        for i in range(1, n):
            parStartIndices.append(parStartIndices[i - 1] + len(texts[i - 1]) + len(joinString))
        boundaries = SentenceNavMixin.splitParagraphIntoSentences(s, regex=regex)
        if getSNConfig("breakAtElementBoundaries"):
            # Paragraph transitions are sentence boundaries (each VB element is a unit)
            for i in range(1, n):
                p = parStartIndices[i]
                if 0 < p < len(s):
                    boundaries.append(p)
            # Element boundaries (within each paragraph: \n separators, inline transitions)
            for i, ti in enumerate(tis):
                extra = _getElementBoundaries(ti)
                if extra:
                    offset = parStartIndices[i]
                    for b in extra:
                        bAbs = offset + b
                        if 0 < bAbs < len(s):
                            boundaries.append(bAbs)
            boundaries = sorted(set(boundaries))
            # Slide past whitespace (same treatment as regex boundaries)
            def slideForward(i):
                if i == 0:
                    return i
                while i < len(s) and s[i].isspace():
                    i += 1
                return i
            boundaries = [slideForward(b) for b in boundaries]
            boundaries = sorted(set(boundaries))
        j = bisect.bisect_right(boundaries, index)
        i = j - 1
        if len(boundaries) == 1:
            t1i = bisect.bisect_right(parStartIndices, boundaries[i]) - 1
            t1 = tis[t1i]
            return (texts[t1i], t1, 0, t1, len(texts[t1i]))
        if j == len(boundaries):
            ti = tis[-1]
            moveDistance = boundaries[i] - parStartIndices[-1]
            return ("", tis[-1], moveDistance, tis[-1], len(texts[-1]))
        sentenceStr = s[boundaries[i]:boundaries[j]]
        t1i = bisect.bisect_right(parStartIndices, boundaries[i]) - 1
        t1 = tis[t1i]
        t1offset = boundaries[i] - parStartIndices[t1i]
        t2i = bisect.bisect_right(parStartIndices, boundaries[j]) - 1
        t2 = tis[t2i]
        t2offset = boundaries[j] - parStartIndices[t2i]
        return (sentenceStr, t1, t1offset, t2, t2offset)

    def nextParagraph(self, textInfo, direction, shouldTurnPageIfNecessary=False):
        ti = textInfo.copy()
        for _attempt in [1, 2]:
            ti.collapse()
            result = ti.move(textInfos.UNIT_PARAGRAPH, direction)
            if result == 0:
                if shouldTurnPageIfNecessary:
                    focus = textInfo.obj
                    if isinstance(focus, textInfos.DocumentWithPageTurns) and 'kindle' in str(type(focus)):
                        try:
                            focus.turnPage(previous=direction < 0)
                        except RuntimeError:
                            return None
                        else:
                            paragraph = focus.makeTextInfo(textInfos.POSITION_FIRST if direction > 0 else textInfos.POSITION_LAST)
                            paragraph.expand(textInfos.UNIT_PARAGRAPH)
                            return paragraph
                return None
            ti.expand(textInfos.UNIT_PARAGRAPH)
            if sign(ti.compareEndPoints(textInfo, "startToStart")) == sign(direction):
                return ti
        return None

    def expandSentence(self, context, regex, direction, compatibilityFunc=None):
        if direction == 0:
            self.expandSentence(context, regex, -1, compatibilityFunc=compatibilityFunc)
            return self.expandSentence(context, regex, 1, compatibilityFunc=compatibilityFunc)
        elif direction > 0:
            cindex = -1
        else:
            cindex = 0
        counter = 0
        while True:
            counter += 1
            if counter > 1000:
                raise RuntimeError("Infinite loop detected.")
            sentenceStr, startTi, startOffset, endTi, endOffset = self.findCurrentSentence(context, regex)
            if not context.isTouchingBoundary(direction, startTi, startOffset, endTi, endOffset):
                return (sentenceStr, startTi, startOffset, endTi, endOffset)
            nextTextInfo = self.nextParagraph(context.textInfos[cindex], direction)
            if nextTextInfo is None:
                return (sentenceStr, startTi, startOffset, endTi, endOffset)
            if compatibilityFunc is not None:
                if not compatibilityFunc(nextTextInfo, context.textInfos[cindex]):
                    return (sentenceStr, startTi, startOffset, endTi, endOffset)
            context.addParagraph(cindex, nextTextInfo)

    styleFields = [
        "level", "font-family", "font-size", "color",
        "background-color", "bold", "italic",
    ]

    def getParagraphStyle(self, info):
        formatField = textInfos.FormatField()
        formatConfig = _cached_doc_formatting
        for field in info.getTextWithFields(formatConfig):
            if isinstance(field, textInfos.FieldCommand):
                formatField.update(field.field)
        result = [formatField.get(fieldName, None) for fieldName in self.styleFields]
        return tuple(result)

    def moveExtended(self, context, direction, regex, errorMsg="Error", reconstructMode="sameIndent"):
        chimeIfAcrossParagraphs = False
        if reconstructMode == "always":
            compatibilityFunc = lambda x, y: True
        elif reconstructMode == "sameIndent":
            compatibilityFunc = lambda ti1, ti2: (
                ti1.NVDAObjectAtStart.location[0] == ti2.NVDAObjectAtStart.location[0]
            ) and (self.getParagraphStyle(ti1) == self.getParagraphStyle(ti2))
        elif reconstructMode == "never":
            compatibilityFunc = lambda x, y: False
        else:
            raise ValueError()

        sentenceStr, startTi, startOffset, endTi, endOffset = self.expandSentence(
            context, regex, direction, compatibilityFunc=compatibilityFunc)
        if direction == 0:
            return sentenceStr, context.makeSentenceInfo(startTi, startOffset, endTi, endOffset), startOffset
        elif direction > 0:
            cindex = -1
        else:
            cindex = 0
        if context.isTouchingBoundary(direction, startTi, startOffset, endTi, endOffset):
            paragraph = context.textInfos[cindex]
            counter = 0
            while True:
                counter += 1
                if counter > 1000:
                    raise RuntimeError("Infinite loop detected.")
                paragraph = self.nextParagraph(paragraph, direction, shouldTurnPageIfNecessary=True)
                if paragraph is None:
                    self._sn_chimeNoNextSentence(errorMsg)
                    return (None, None, None)
                if not speech.isBlank(paragraph.text):
                    break
            self._sn_chimeCrossParagraphBorder()
            context = Context(paragraph, 0)
            if direction < 0:
                context.findByOffset(paragraph, len(context.texts[0]) - 1)
        else:
            if direction > 0:
                context.findByOffset(endTi, endOffset)
            else:
                context.findByOffset(startTi, startOffset - 1)
            chimeIfAcrossParagraphs = True
        sentenceStr2, startTi2, startOffset2, endTi2, endOffset2 = self.expandSentence(
            context, regex, direction, compatibilityFunc=compatibilityFunc)
        if chimeIfAcrossParagraphs:
            if (
                (direction > 0 and startOffset2 == 0)
                or (direction < 0 and startOffset == 0)
            ):
                self._sn_chimeCrossParagraphBorder()
        info = context.makeSentenceInfo(startTi2, startOffset2, endTi2, endOffset2)
        return sentenceStr2, info, startOffset2

    # --- Chime helpers ---
    def _sn_chimeNoNextSentence(self, errorMsg="Error"):
        import globalPlugins.audiothemes as at
        handler = getattr(at.GlobalPlugin, "_instance_handler", None)
        if handler and handler.play_theme_sound("no_next_sentence"):
            pass
        else:
            self._sn_fancyBeep("HF", 100, _sn_cached_chime_volume, _sn_cached_chime_volume)
            
        if getSNConfig("noNextSentenceMessage"):
            ui.message(errorMsg)

    def _sn_chimeCrossParagraphBorder(self):
        import globalPlugins.audiothemes as at
        handler = getattr(at.GlobalPlugin, "_instance_handler", None)
        if handler and handler.play_theme_sound("paragraph_chime"):
            return
            
        self._sn_fancyBeep("AC#EG#", 30, _sn_cached_paragraph_chime_volume, _sn_cached_paragraph_chime_volume)

    # --- Beep helpers ---
    NOTES = "A,B,H,C,C#,D,D#,E,F,F#,G,G#".split(",")
    NOTE_RE = re.compile("[A-H][#]?")
    _SN_BASE_FREQ = 220

    def _sn_getChordFrequencies(self, chord):
        myAssert(len(self.NOTES) == 12)
        prev = -1
        result = []
        for m in self.NOTE_RE.finditer(chord):
            s = m.group()
            i = self.NOTES.index(s)
            while i < prev:
                i += 12
            result.append(int(self._SN_BASE_FREQ * (2 ** (i / 12.0))))
            prev = i
        return result

    def _sn_fancyBeep(self, chord, length, left=10, right=10, category="sentencenav"):
        from .utils import is_sound_suppressed
        if is_sound_suppressed(category):
            return
        # Apply audio ducking
        try:
            from .. import frenzy
            df = frenzy.get_ducking_factor(category)
            if df < 1.0:
                left = int(left * df)
                right = int(right * df)
        except Exception:
            pass
        beepLen = length
        freqs = self._sn_getChordFrequencies(chord)
        intSize = 8
        bufSize = max([NVDAHelper.localLib.generateBeep(None, freq, beepLen, right, left) for freq in freqs])
        if bufSize % intSize != 0:
            bufSize += intSize
            bufSize -= (bufSize % intSize)
        tones.player.stop()
        result = [0] * (bufSize // intSize)
        for freq in freqs:
            buf = ctypes.create_string_buffer(bufSize)
            NVDAHelper.localLib.generateBeep(buf, freq, beepLen, right, left)
            bb = bytearray(buf)
            unpacked = struct.unpack("<%dQ" % (bufSize // intSize), bb)
            result = map(operator.add, result, unpacked)
        maxInt = 1 << (8 * intSize)
        result = map(lambda x: x % maxInt, result)
        packed = struct.pack("<%dQ" % (bufSize // intSize), *result)
        tones.player.feed(packed)

    # --- Pass-through check ---
    def _sn_maybePassThrough(self, gesture):
        focus = api.getFocusObject()
        if not focus or not focus.appModule:
            return False
        appName = getattr(focus.appModule, 'appName', '') or ''
        if appName.lower() in getSNConfig("applicationsBlacklist").lower().strip().split(","):
            gesture.send()
            return True
        return False

    # --- Core move ---
    _sn_virtualCaret = None  # (paragraphText, caretOffset) - bypass VB caret drift

    def _sn_move(self, gesture, regex, increment, errorMsg):
        focus = api.getFocusObject()
        if not getSNConfig("enableInWord") and (
            isinstance(focus, winword.WordDocument) or (
                "Dynamic_IAccessibleRichEdit" in str(type(focus))
                and hasattr(focus, "script_caret_nextSentence")
                and hasattr(focus, "script_caret_previousSentence")
            )
        ):
            if increment > 0:
                focus.script_caret_nextSentence(gesture)
            elif increment < 0:
                focus.script_caret_previousSentence(gesture)
            return
        if hasattr(focus, "treeInterceptor") and focus.treeInterceptor is not None and hasattr(focus.treeInterceptor, "makeTextInfo"):
            focus = focus.treeInterceptor
        elif focus.role in [ROLE_COMBOBOX, ROLE_LISTITEM, ROLE_BUTTON]:
            try:
                focus.treeInterceptor.script_collapseOrExpandControl(gesture)
            except AttributeError:
                gesture.send()
            return
        try:
            caretInfo = focus.makeTextInfo(textInfos.POSITION_CARET)
        except NotImplementedError:
            gesture.send()
            return
        caretIndex, paragraphInfo = getCaretIndexWithinParagraph(caretInfo)
        paraText = preprocessNewLines(paragraphInfo.text)
        # Use virtual caret to bypass VB caret drift on treeInterceptors
        # Invalidate after single use; will be re-stored after successful move
        if self._sn_virtualCaret is not None:
            storedText, storedOffset = self._sn_virtualCaret
            if storedText == paraText:
                caretIndex = storedOffset
        context = Context(paragraphInfo, caretIndex, caretInfo)
        reconstructMode = getSNConfig("reconstructMode")
        sentenceStr, ti, sn_startOffset = self.moveExtended(context, increment, regex=regex, errorMsg=errorMsg, reconstructMode=reconstructMode)
        if ti is None:
            self._sn_virtualCaret = None
            return
        if increment != 0:
            if sn_startOffset is not None:
                # Store the actual paragraph text containing the target sentence
                # to ensure paragraphText and offset always belong together
                try:
                    caretCopy = ti.copy()
                    caretCopy.collapse()
                    caretCopy.expand(textInfos.UNIT_PARAGRAPH)
                    actualParaText = preprocessNewLines(caretCopy.text)
                    self._sn_virtualCaret = (actualParaText, sn_startOffset)
                except Exception:
                    self._sn_virtualCaret = (paraText, sn_startOffset)
            newCaret = ti.copy()
            newCaret.collapse()
            newCaret.updateCaret()
            # Verify caret wasn't drifted by VirtualBuffer; retry via _setCaret if needed
            try:
                verifyCaret = focus.makeTextInfo(textInfos.POSITION_CARET)
                verifyCaret.collapse()
                if newCaret.compareEndPoints(verifyCaret, "startToStart") != 0:
                    if hasattr(focus, "_setCaret"):
                        focus._setCaret(newCaret)
            except Exception:
                pass
            review.handleCaretMove(newCaret)
            braille.handler.handleCaretMove(focus)
            vision.handler.handleCaretMove(focus)
        if willSayAllResume(gesture):
            return
        speech.speakText(sentenceStr)

    # ── Scripts (bound to Alt+Arrows) ──

    @script(description=_("Move to next sentence."), category="Advanced Audio Themes", gestures=['kb:Alt+DownArrow'],
            resumeSayAllMode=CURSOR_CARET)
    def script_nextSentence(self, gesture):
        try:
            focus = api.getFocusObject()
            if 'NvdaPythonConsoleUIOutputCtrl' in str(type(focus)):
                return focus.script_moveToNextResult(gesture)
        except AttributeError:
            pass
        if self._sn_maybePassThrough(gesture):
            return
        regex = getRegex(getCurrentLanguage())
        errorMsg = _("No next sentence")
        self._sn_move(gesture, regex, 1, errorMsg)

    @script(description=_("Move to previous sentence."), category="Advanced Audio Themes", gestures=['kb:Alt+UpArrow'],
            resumeSayAllMode=CURSOR_CARET)
    def script_previousSentence(self, gesture):
        try:
            focus = api.getFocusObject()
            if 'NvdaPythonConsoleUIOutputCtrl' in str(type(focus)):
                return focus.script_moveToPrevResult(gesture)
        except AttributeError:
            pass
        if self._sn_maybePassThrough(gesture):
            return
        regex = getRegex(getCurrentLanguage())
        errorMsg = _("No previous sentence")
        self._sn_move(gesture, regex, -1, errorMsg)

    @script(description=_("Speak current sentence."), category="Advanced Audio Themes", gestures=['kb:NVDA+Alt+S'])
    def script_currentSentence(self, gesture):
        if self._sn_maybePassThrough(gesture):
            return
        regex = getRegex(getCurrentLanguage())
        self._sn_move(gesture, regex, 0, "")

    @script(description=_("Move to next phrase."), category="Advanced Audio Themes", gestures=['kb:Alt+Windows+DownArrow'],
            resumeSayAllMode=CURSOR_CARET)
    def script_nextPhrase(self, gesture):
        if self._sn_maybePassThrough(gesture):
            return
        regex = getPhraseRegex()
        errorMsg = _("No next phrase")
        self._sn_move(gesture, regex, 1, errorMsg)

    @script(description=_("Move to previous phrase."), category="Advanced Audio Themes", gestures=['kb:Alt+Windows+UpArrow'],
            resumeSayAllMode=CURSOR_CARET)
    def script_previousPhrase(self, gesture):
        if self._sn_maybePassThrough(gesture):
            return
        regex = getPhraseRegex()
        errorMsg = _("No previous phrase")
        self._sn_move(gesture, regex, -1, errorMsg)

    @script(description=_("Speak current phrase."), category="Advanced Audio Themes", gestures=[])
    def script_currentPhrase(self, gesture):
        if self._sn_maybePassThrough(gesture):
            return
        regex = getPhraseRegex()
        self._sn_move(gesture, regex, 0, "")

    @script(description=_("Move to next paragraph containing text."), category="Advanced Audio Themes", gestures=['kb:Alt+Shift+DownArrow'])
    def script_nextText(self, gesture):
        if self._sn_maybePassThrough(gesture):
            return
        self._sn_moveToText(gesture, 1, _("No next paragraph with text"))

    @script(description=_("Move to previous paragraph containing text."), category="Advanced Audio Themes", gestures=['kb:Alt+Shift+UpArrow'])
    def script_previousText(self, gesture):
        if self._sn_maybePassThrough(gesture):
            return
        self._sn_moveToText(gesture, -1, _("No previous paragraph with text"))

    def _sn_moveToText(self, gesture, increment, errorMsg="Error"):
        focus = api.getFocusObject()
        if hasattr(focus, "treeInterceptor") and focus.treeInterceptor is not None and hasattr(focus.treeInterceptor, "makeTextInfo"):
            focus = focus.treeInterceptor
        try:
            textInfo = focus.makeTextInfo(textInfos.POSITION_CARET)
        except NotImplementedError:
            gesture.send()
            return
            
        distance = 0
        while True:
            textInfo.collapse()
            result = textInfo.move(textInfos.UNIT_PARAGRAPH, increment)
            if result == 0:
                import globalPlugins.audiothemes as at
                handler = getattr(at.GlobalPlugin, "_instance_handler", None)
                if handler and handler.play_theme_sound("no_next_text"):
                    pass
                else:
                    volume = getSNConfig("noNextTextChimeVolume")
                    self._sn_fancyBeep("HF", 100, volume, volume, category="textnav")
                
                if getSNConfig("noNextTextMessage"):
                    ui.message(errorMsg)
                return
            distance += 1
            if distance == 1000:
                ui.message(_("TextNav error: Infinite loop"))
                return
            textInfo.expand(textInfos.UNIT_PARAGRAPH)
            text = textInfo.text

            text2 = text + " FinalWord"
            boundaries = SentenceNavMixin.splitParagraphIntoSentences(text2, getRegex(getCurrentLanguage()))
            if len(boundaries) >= 3:
                textInfo.updateCaret()
                from .browserNavEngine.beeper import Beeper
                Beeper().simpleCrackle(distance, getSNConfig("textCrackleVolume"), category="textnav")
                if getSNConfig("speakFormatted"):
                    speech.speakTextInfo(textInfo, reason=REASON_CARET)
                else:
                    speech.speakText(text)
                break

