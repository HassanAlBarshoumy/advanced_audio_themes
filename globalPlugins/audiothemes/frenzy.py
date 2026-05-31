# -*- coding: UTF-8 -*-
# A part of the Advanced Audio Themes addon for NVDA
# Originally part of the Earcons and Speech rules addon for NVDA by Tony Malykh.
# Integrated and maintained by Hassan AlBarshoumy.
# Special thanks: Ahmed Sami
# This file is covered by the GNU General Public License.

import addonHandler
import api
import bisect
import characterProcessing
import config
import collections
import controlTypes
import copy
import core
import ctypes
from ctypes import create_string_buffer, byref
from enum import Enum
import globalPluginHandler
import globalVars
import gui
from gui import guiHelper, nvdaControls
from gui.settingsDialogs import SettingsPanel
import itertools
import json
from logHandler import log
import NVDAHelper
from NVDAObjects.window import winword
import nvwave
import operator
import os
from queue import Queue
import re
from scriptHandler import script, willSayAllResume
import speech
import speech.commands
import struct
import textInfos
import threading
from threading import Thread
import time
import tones
import ui
import wave
import wx

from .common import *
from .utils import *
from . import utils
from .commands import *

from .commands import PpSynchronousCommand, PpWaveFileCommand
from . import phoneticPunctuation as pp
from controlTypes import OutputReason
from config.configFlags import ReportLineIndentation


def _get_blacklisted_roles():
    try:
        val = config.conf["audiothemes"].get("blacklisted_roles", "[19]")
        if isinstance(val, list):
            if all(isinstance(r, int) for r in val):
                return val
            return [19]
        if isinstance(val, str):
            import json
            parsed = json.loads(val)
            if isinstance(parsed, list) and all(isinstance(r, int) for r in parsed):
                return parsed
    except Exception:
        pass
    return [19]


original_getObjectPropertiesSpeech = None

import json
def new_getObjectPropertiesSpeech(
        obj,
        reason = controlTypes.OutputReason.QUERY,
        _prefixSpeechCommand = None,
        **allowedProperties
):
    if obj is None:
        return original_getObjectPropertiesSpeech(
            obj,reason , _prefixSpeechCommand , **allowedProperties
        )

    import config
    import json
    global_fmt = config.conf["audiothemes"].get("announceFormat", "0")
    
    # Load per-role overrides
    try:
        roleFormatsJson = config.conf["audiothemes"].get("roleAnnounceFormats", "{}")
        if not hasattr(utils, '_cachedRoleFormatsJson') or utils._cachedRoleFormatsJson != roleFormatsJson:
            utils._cachedRoleFormatsJson = roleFormatsJson
            utils._cachedRoleFormatsDict = json.loads(roleFormatsJson)
        roleFormatsDict = utils._cachedRoleFormatsDict
    except Exception:
        roleFormatsDict = {}
    
    # Determine format for this specific role
    role_key = str(obj.role.value) if hasattr(obj.role, 'value') else str(obj.role)
    fmt = roleFormatsDict.get(role_key, None)
    if fmt is None or fmt == "global":
        fmt = global_fmt
        
    # Helper to generate properties specifically
    def get_prop(**props):
        res = []
        patchedProps = props.copy()
        
        if props.get('role', False):
            import config
            if not config.conf["audiothemes"].get("speak_roles", True):
                patchedProps['role'] = False

        if props.get('role', False) and isPhoneticPunctuationEnabled():
            role = obj.role
            if role in roleRules and roleRules[role].enabled:
                rule = roleRules[role]
                speechBehavior = getattr(rule, 'speechBehavior', 0)
                if speechBehavior != 1:
                    patchedProps['role']=False
                command = rule.speechCommand
                if command:
                    res.append(command)
                if speechBehavior == 2 and getattr(rule, 'customSpeechText', ""):
                    res.append(rule.customSpeechText)
                    
        try:
            orig_res = original_getObjectPropertiesSpeech(obj, reason=reason, _prefixSpeechCommand=None, **patchedProps)
        except (Exception, __import__('_ctypes').COMError):
            orig_res = []
        
        import re
        cleaned_orig_res = []
        for item in orig_res:
            if isinstance(item, str):
                item = item.replace(PROPERTY_SPEECH_SIGNATURE2, "")
                if PROPERTY_SPEECH_SIGNATURE in item:
                    item = item.replace(PROPERTY_SPEECH_SIGNATURE, "")
            if item:
                cleaned_orig_res.append(item)
                
        res.extend(cleaned_orig_res)
        return res

    # If it is standard NVDA formatting or they aren't asking for name/role/states together
    if fmt == "0" or not allowedProperties.get("name", False) or (not allowedProperties.get("role", False) and not allowedProperties.get("states", False)):
        seq = []
        if _prefixSpeechCommand:
            seq.append(_prefixSpeechCommand)
        seq.extend(get_prop(**allowedProperties))
        return seq

    # We are using custom formatting (rsc or sc) AND NVDA is requesting multiple properties
    base_kwargs = {k: False for k, v in allowedProperties.items() if isinstance(v, bool)}
    seq = []
    if _prefixSpeechCommand:
        seq.append(_prefixSpeechCommand)
        
    def add_part(part_name):
        if allowedProperties.get(part_name, False):
            kwargs = base_kwargs.copy()
            kwargs[part_name] = True
            part_seq = get_prop(**kwargs)
            if part_seq:
                seq.extend(part_seq)
                if seq and isinstance(seq[-1], str) and not seq[-1].endswith(" "):
                    seq[-1] = seq[-1] + " "

    if fmt == "rsc":
        add_part("role")
        add_part("states")
        add_part("name")
    elif fmt == "sc":
        add_part("states")
        add_part("name")
        add_part("role")

    # Add remaining requested properties in default NVDA order
    remaining_kwargs = base_kwargs.copy()
    for k, v in allowedProperties.items():
        if isinstance(v, bool):
            if k not in ("role", "states", "name"):
                remaining_kwargs[k] = v
        else:
            remaining_kwargs[k] = v

    if any(v for k, v in remaining_kwargs.items() if isinstance(v, bool)):
        seq.extend(get_prop(**remaining_kwargs))
        
    return seq


    # monkey patch speak was removed as it caused double speech and deduplication bugs

def monkeyPatch():
    global original_getObjectPropertiesSpeech
    # Only re-capture the original if it hasn't been set yet.
    # __init__.py installs new_getObjectPropertiesSpeech unconditionally at startup
    # and stores the NVDA original. If we overwrite original_getObjectPropertiesSpeech
    # here (when speech.speech.getObjectPropertiesSpeech is already our function),
    # monkeyUnpatch would restore to our own function instead of the real original.
    if speech.speech.getObjectPropertiesSpeech is not new_getObjectPropertiesSpeech:
        original_getObjectPropertiesSpeech = speech.speech.getObjectPropertiesSpeech
        speech.speech.getObjectPropertiesSpeech = new_getObjectPropertiesSpeech


    global original_getTextInfoSpeech
    if speech.speech.getTextInfoSpeech is not new_getTextInfoSpeech:
        original_getTextInfoSpeech = speech.speech.getTextInfoSpeech
        speech.speech.getTextInfoSpeech = new_getTextInfoSpeech
        speech.sayAll.SayAllHandler._getTextInfoSpeech = speech.speech.getTextInfoSpeech
    
    global original_getPropertiesSpeech, original_getControlFieldSpeech
    if speech.speech.getPropertiesSpeech is not new_getPropertiesSpeech:
        original_getPropertiesSpeech = speech.speech.getPropertiesSpeech
        speech.speech.getPropertiesSpeech = new_getPropertiesSpeech
        speech.getPropertiesSpeech = speech.speech.getPropertiesSpeech
    if speech.speech.getControlFieldSpeech is not new_getControlFieldSpeech:
        original_getControlFieldSpeech = speech.speech.getControlFieldSpeech
        speech.speech.getControlFieldSpeech = new_getControlFieldSpeech
        speech.getControlFieldSpeech = speech.speech.getControlFieldSpeech
    
    global original_processAndLabelStates
    if controlTypes.processAndLabelStates is not new_processAndLabelStates:
        original_processAndLabelStates = controlTypes.processAndLabelStates
        controlTypes.processAndLabelStates = new_processAndLabelStates

    global original_getTextInfoSpeech_considerSpelling    
    if hasattr(speech.speech, "_getTextInfoSpeech_considerSpelling") and speech.speech._getTextInfoSpeech_considerSpelling is not new_getTextInfoSpeech_considerSpelling:
        original_getTextInfoSpeech_considerSpelling = speech.speech._getTextInfoSpeech_considerSpelling
        speech.speech._getTextInfoSpeech_considerSpelling = new_getTextInfoSpeech_considerSpelling

    # Track speech time for audio ducking
    global _speech_time_handler, _original_speak, last_speech_time
    try:
        _speech_time_handler = speech.manager.pre_synthSpeak.register(_track_speech_time)
    except Exception:
        try:
            if speech.speech.speak is not _tracking_speak:
                _original_speak = speech.speech.speak
                speech.speech.speak = _tracking_speak
        except Exception:
            log.warning("Audio ducking: could not hook speech")

def monkeyUnpatch():
    if original_getObjectPropertiesSpeech is not None:
        speech.speech.getObjectPropertiesSpeech = original_getObjectPropertiesSpeech

    speech.speech.getTextInfoSpeech = original_getTextInfoSpeech
    speech.sayAll.SayAllHandler._getTextInfoSpeech = speech.speech.getTextInfoSpeech
    speech.speech.getPropertiesSpeech = original_getPropertiesSpeech
    speech.speech.getControlFieldSpeech = original_getControlFieldSpeech
    
    speech.getPropertiesSpeech = speech.speech.getPropertiesSpeech
    speech.getControlFieldSpeech = speech.speech.getControlFieldSpeech
    
    controlTypes.processAndLabelStates = original_processAndLabelStates
    
    if original_getTextInfoSpeech_considerSpelling is not None and hasattr(speech.speech, "_getTextInfoSpeech_considerSpelling"):
        speech.speech._getTextInfoSpeech_considerSpelling = original_getTextInfoSpeech_considerSpelling

    # Restore speech time tracking for audio ducking
    global _speech_time_handler, _original_speak
    if _speech_time_handler is not None:
        try:
            _speech_time_handler.unregister()
        except Exception:
            pass
        _speech_time_handler = None
    if _original_speak is not None:
        try:
            speech.speech.speak = _original_speak
        except Exception:
            pass
        _original_speak = None

roleRules = None
stateRules = None
stateDict = None
negativeStateDict=None
formatRules = None
numericFormatRules = None
otherRules = None
roleRules = {}
stateRules = {}
negativeStateRules = {}
formatRules = {}
numericFormatRules = {}
otherRules = {}


# Audio ducking speech tracking
last_speech_time = 0.0
_speech_time_handler = None
_original_speak = None
_ducking_categories_json = ""
_ducking_categories_dict = {}

_DEFAULT_DUCKING_CATEGORIES = {
    "theme_sounds": True,
    "typing_sounds": True,
    "earcons": True,
    "browsernav": True,
    "sentencenav": True,
    "textnav": True,
    "ui_beeps": True,
}

def _load_ducking_categories():
    global _ducking_categories_json, _ducking_categories_dict
    try:
        raw = config.conf.get("audiothemes", {}).get("ducking_categories", "")
        if raw == _ducking_categories_json:
            return
        _ducking_categories_json = raw
        if raw:
            import json
            _ducking_categories_dict = json.loads(raw)
        else:
            _ducking_categories_dict = {}
    except Exception:
        _ducking_categories_dict = {}

def _track_speech_time():
    global last_speech_time
    last_speech_time = time.time()

def _tracking_speak(sequence):
    global last_speech_time
    last_speech_time = time.time()
    if _original_speak:
        _original_speak(sequence)

def get_ducking_factor(category="theme_sounds"):
    try:
        if config.conf.get("audiothemes", {}).get("audio_ducking_enabled", True):
            _load_ducking_categories()
            if not _ducking_categories_dict.get(category, True):
                return 1.0
            if time.time() - last_speech_time < 1.0:
                return config.conf.get("audiothemes", {}).get("audio_ducking_volume", 30) / 100.0
    except Exception:
        pass
    return 1.0

def apply_ducking_to_pcm(pcm_bytes, df, sample_width=2):
    if df >= 1.0:
        return pcm_bytes
    import array
    if sample_width == 2:
        arr = array.array('h')
        arr.frombytes(pcm_bytes)
        for i in range(len(arr)):
            arr[i] = int(arr[i] * df)
        return arr.tobytes()
    elif sample_width == 1:
        arr = array.array('b')
        arr.frombytes(pcm_bytes)
        for i in range(len(arr)):
            val = int((arr[i] - 128) * df)
            arr[i] = max(0, min(255, val + 128))
        return arr.tobytes()
    elif sample_width == 4:
        arr = array.array('i')
        arr.frombytes(pcm_bytes)
        for i in range(len(arr)):
            arr[i] = int(arr[i] * df)
        return arr.tobytes()
    return pcm_bytes

def updateRules():
    global roleRules, stateRules, negativeStateRules, formatRules, numericFormatRules, otherRules
    
    def buildList(frenzyType):
        d = collections.defaultdict(list)
        for rule in pp.rulesByFrenzy[frenzyType]:
            if rule.enabled:
                d[rule.getFrenzyValue()].append(rule)
        return dict(d)

    roleRules = buildList(FrenzyType.ROLE)
    stateRules = buildList(FrenzyType.STATE)
    negativeStateRules = buildList(FrenzyType.NEGATIVE_STATE)
    formatRules = buildList(FrenzyType.FORMAT)
    numericFormatRules = buildList(FrenzyType.NUMERIC_FORMAT)
    otherRules = buildList(FrenzyType.OTHER_RULE)

class _LRUCache:
    def __init__(self, capacity: int):
        self.cache = collections.OrderedDict()
        self.capacity = capacity
        self.lock = threading.Lock()

    def get(self, key):
        with self.lock:
            if key not in self.cache:
                return False, None
            self.cache.move_to_end(key)
            return True, self.cache[key]

    def put(self, key, value):
        with self.lock:
            self.cache[key] = value
            self.cache.move_to_end(key)
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)

_active_rule_cache = _LRUCache(256)

def getActiveRuleContext(ruleList, appName, windowTitle, url):
    if not ruleList:
        return None
        
    cache_key = (id(ruleList), appName, windowTitle, url)
    found, cached_val = _active_rule_cache.get(cache_key)
    if found:
        return cached_val

    matched_rule = None
    for rule in ruleList:
        if len(rule.applicationFilterRegex) > 0 and not rule._applicationFilterRegex.search(appName):
            continue
        if len(rule.windowTitleRegex) > 0 and not rule._windowTitleRegex.search(windowTitle):
            continue
        if len(rule.urlRegex) > 0 and (url is None or not rule._urlRegex.search(url)):
            continue
        matched_rule = rule
        break
        
    _active_rule_cache.put(cache_key, matched_rule)
    return matched_rule

def getRuleStateValue(rule, is_negative=False):
    verbose = utils.getConfig("stateVerbose")
    speechBehavior = getattr(rule, 'speechBehavior', 0)
    customText = getattr(rule, 'customSpeechText', "")
    
    if speechBehavior == 1:
        try:
            if is_negative:
                orig_text = controlTypes.State(rule.getFrenzyValue()).negativeDisplayString
            else:
                orig_text = controlTypes.State(rule.getFrenzyValue()).displayString
        except Exception:
            try:
                if is_negative:
                    orig_text = controlTypes.negativeStateLabels[rule.getFrenzyValue()]
                else:
                    orig_text = controlTypes.stateLabels[rule.getFrenzyValue()]
            except Exception:
                orig_text = ""
        return [rule.speechCommand, orig_text] if rule.speechCommand else orig_text
    elif speechBehavior == 2 and customText:
        return [rule.speechCommand, customText] if rule.speechCommand else customText
    elif not verbose and rule.suppressStateClutter:
        return ""
    elif rule.ruleType == audioRuleNoop:
        return None
    else:
        return rule.speechCommand

class FakeTextInfo:
    def __init__(self, info, formatConfig, preventSpellingCharacters, addFakeEmptyText):
        self.info = info
        self.formatConfig = formatConfig.copy()
        self.preventSpellingCharacters = preventSpellingCharacters
        fields = info.getTextWithFields(formatConfig)
        if addFakeEmptyText:
            specialFormatIndices = [
                i 
                for i,field in enumerate(fields)
                if
                    isinstance(field,textInfos.FieldCommand)
                    and field.command == "controlStart"
                    and field.field.get('role', None) in [
                        controlTypes.Role.HEADING,
                        controlTypes.Role.MARKED_CONTENT,
                    ]
            ]
            if len(specialFormatIndices) > 0:
                index = specialFormatIndices[0]
                strings = [
                    field
                    for i,field in enumerate(fields)
                    if
                        isinstance(field,str)
                ]
                if len(strings) > 0:
                    firstString = strings[0]
                    if hasattr(speech.speech, "RE_INDENTATION_CONVERT"):
                        if m:=speech.speech.RE_INDENTATION_CONVERT.search(firstString):
                            fields.insert(index, m.group() + "\n")
        self.fields = fields
    
    def setSkipSet(self, skipSet):
        self.skipSet = skipSet
        
    def setStartAndEnd(self, start, end):
        self.start, self.end = start, end

    def getTextWithFields(self, formatConfig= None):
        # We tweak indentation reporting, so it's ok that indentation reporting field value is different.
        # However for sanity check we would like to ensure that all the other fields are identical.
        try:
            self.formatConfig["reportLineIndentation"] = formatConfig["reportLineIndentation"]
        except KeyError:
            pass
        # Also in MSWord in Legacy non-UIA mode somehow 'autoLanguageSwitching' gets changed, so tweaking it as well
        try:
            self.formatConfig ["autoLanguageSwitching"] = formatConfig["autoLanguageSwitching"]
        except KeyError:
            pass
        if formatConfig != self.formatConfig:
            #raise ValueError
            pass
        stack = []
        info = self.info
        skipSet = self.skipSet
        start = self.start
        end = self.end
        result = []
        fields = self.fields
        controlStackDepth = 0
        for i, field in enumerate(fields[:end]):
            if i in skipSet:
                continue
            if isinstance(field,textInfos.FieldCommand):
                if field.command == "controlStart":
                    controlStackDepth += 1
                elif field.command == "controlEnd":
                    controlStackDepth -= 1
            if i < start:
                if isinstance(field,textInfos.FieldCommand):
                    if field.command == "controlStart":
                        result.append(field)
                    elif field.command == "controlEnd":
                        del result[-1]
            else:
                # If we are just closing the previous controlStart without any content - drop that controlStart instead
                if (
                    len(result) > 0
                    and isinstance(result[-1], textInfos.FieldCommand)
                    and isinstance(field,textInfos.FieldCommand)
                    and result[-1].command == "controlStart"
                    and field.command == "controlEnd"
                ):
                    del result[-1]
                else:
                    # In order to avoid single spaces being spoken in a longer line when speaking by word, line or paragraph, augment them with another character to avoid spelling symbol names.
                    if self.preventSpellingCharacters and isinstance(field, str):
                        field = field + '\n'
                    result.append(field)
        for i in range(controlStackDepth):
            # If we are just closing the previous controlStart without any content - drop that controlStart instead
            if (
                len(result) > 0
                and isinstance(result[-1], textInfos.FieldCommand)
                and isinstance(field,textInfos.FieldCommand)
                and result[-1].command == "controlStart"
            ):
                del result[-1]
            else:
                result.append(textInfos.FieldCommand("controlEnd", field=None))
        return result
    
    def getControlFieldSpeech(
            self,
            attrs,
            ancestorAttrs,
            fieldType,
            formatConfig = None,
            extraDetail = False,
            reason= None
    ):
        return self.info.getControlFieldSpeech(
            attrs,
            ancestorAttrs,
            fieldType,
            formatConfig,
            extraDetail,
            reason,
        )

    def getFormatFieldSpeech(
            self,
            attrs,
            attrsCache= None,
            formatConfig= None,
            reason = None,
            unit = None,
            extraDetail = False,
            initialFormat = False,
    ):
        return self.info.getFormatFieldSpeech(
            attrs,
            attrsCache,
            formatConfig,
            reason ,
            unit ,
            extraDetail ,
            initialFormat ,
        )
    @property
    def obj(self):
        return self.info.obj
    
    def getMathMl(self, field):
        return self.info.getMathMl(field)

def findControlEnd(fields, start):
    i = start
    stack = []
    while i < len(fields):
        field = fields[i]
        if isinstance(field,textInfos.FieldCommand):
            if field.command == "controlStart":
                stack.append(field)
            elif field.command == "controlEnd":
                del stack[-1]
        if len(stack) == 0:
            return i
        i += 1
    raise RuntimeError()


def findAllControlFields(fields, role=controlTypes.Role.HEADING):
    for i, field in enumerate(fields):
        if isinstance(field,textInfos.FieldCommand):
            if field.command == "controlStart":
                try:
                    if field.field.get('role', None) == role:
                        yield i
                except KeyError:
                    pass

def findAllFormatFieldBrackets(fields):
    currentStartIndex = None
    for i, field in enumerate(fields):
        if isinstance(field,textInfos.FieldCommand):
            if currentStartIndex is not None:
                yield (currentStartIndex, i)
                currentStartIndex = None
            if field.command == "formatChange":
                currentStartIndex = i
    if currentStartIndex is not None:
        yield (currentStartIndex, len(fields))

def isBlankSequence(sequence):
    for grouping  in sequence:
        for s in grouping:
            if isinstance(s, str)  and not speech.speech.isBlank(s):
                return False
    return True

def computeStackAtIndex(fields, index):
    stack = []
    for field in fields[:index]:
        if isinstance(field,textInfos.FieldCommand):
            if field.command == "controlStart":
                stack.append(field)
            elif field.command == "controlEnd":
                del stack[-1]
    return stack

def computeCacheableStateAtEnd(fields):
    stringFieldIndices = [i for i, field in enumerate(fields) if isinstance(field, str)]
    if len(stringFieldIndices) == 0:
        return {}
    lastIndex = stringFieldIndices[-1]
    stack = computeStackAtIndex(fields, lastIndex)
    result = {}
    for field in stack:
        if field.field.get('role', None) == controlTypes.Role.HEADING:
            headingLevel = field.field.get('level', None)
            if headingLevel is not None:
                result['headingLevel'] = int(headingLevel)
        if field.field.get('role', None) == controlTypes.Role.MARKED_CONTENT:
            result['highlighted'] = True
    return result

original_getTextInfoSpeech = None
def new_getTextInfoSpeech(
        info,
        useCache = True,
        formatConfig= None,
        unit = None,
        reason = OutputReason.QUERY,
        _prefixSpeechCommand= None,
        onlyInitialFields = False,
        suppressBlanks = False
):
    if not isPhoneticPunctuationEnabled():
        yield from original_getTextInfoSpeech(
            info,
            useCache ,
            formatConfig,
            unit ,
            reason ,
            _prefixSpeechCommand,
            onlyInitialFields,
            suppressBlanks,
        )
        return
    if True:
        # Computing formatConfig - identical to logic in the original function
        extraDetail = unit in (textInfos.UNIT_CHARACTER, textInfos.UNIT_WORD)
        if not formatConfig:
            formatConfig = config.conf["documentFormatting"]
        formatConfig = formatConfig.copy()
        if extraDetail:
            formatConfig["extraDetail"] = True
        # For performance reasons, when navigating by paragraph or table cell, spelling errors will not be announced.
        if unit in (textInfos.UNIT_PARAGRAPH, textInfos.UNIT_CELL) and reason == OutputReason.CARET:
            formatConfig["reportSpellingErrors"] = False
    appName, windowTitle, url = utils.getCurrentContext()
    
    headingRule = getActiveRuleContext(formatRules.get(TextFormat.HEADING, []), appName, windowTitle, url)
    headingLevelRules = {
        level: getActiveRuleContext(formatRules.get(getattr(TextFormat, f'HEADING{level}'), []), appName, windowTitle, url)
        for level in range(1, 7)
    }
    headingLevelRule = getActiveRuleContext(numericFormatRules.get(NumericTextFormat.HEADING_LEVEL, []), appName, windowTitle, url)
    fontSizeRule = getActiveRuleContext(numericFormatRules.get(NumericTextFormat.FONT_SIZE, []), appName, windowTitle, url)
    highlightedRule = getActiveRuleContext(formatRules.get(TextFormat.HIGHLIGHTED, []), appName, windowTitle, url)
    processHeadings = True
    
    # Dynamically override formatConfig for roles/states that have active speech rules
    role_to_format_key = {
        controlTypes.Role.LINK: "reportLinks",
        controlTypes.Role.HEADING: "reportHeadings",
        controlTypes.Role.TABLE: "reportTables",
        controlTypes.Role.LIST: "reportLists",
        controlTypes.Role.BLOCKQUOTE: "reportBlockQuotes",
        controlTypes.Role.FRAME: "reportFrames",
        controlTypes.Role.LANDMARK: "reportLandmarks",
        controlTypes.Role.ARTICLE: "reportArticles",
        controlTypes.Role.COMMENT: "reportComments",
    }
    for r, key in role_to_format_key.items():
        if getActiveRuleContext(roleRules.get(r, []), appName, windowTitle, url) is not None:
            formatConfig[key] = True

    # Check for states that require specific document formatting settings
    if getActiveRuleContext(stateRules.get(controlTypes.State.CLICKABLE, []), appName, windowTitle, url) is not None:
        formatConfig["reportClickable"] = True
    if getActiveRuleContext(stateRules.get(controlTypes.State.VISITED, []), appName, windowTitle, url) is not None:
        formatConfig["reportLinks"] = True
        
    firstHeadingLevelCommand = None
    preventSpellingCharacters = (
        unit not in  [textInfos.UNIT_CHARACTER, textInfos.UNIT_WORD]
        or len(info.text) != 1
    )
    
    fakeTextInfo  = FakeTextInfo(info, formatConfig, preventSpellingCharacters=preventSpellingCharacters, addFakeEmptyText=False)
    fields = fakeTextInfo.fields

    #skip set contains indices where heading controls start and end.
    # We will filter them out before returning from this function as we don't want built-in NVDA logic to double-process headings.
    # They also serve as boundaries for other font attribute processing as typically text formatting changes when we enter/exit a heading.
    skipSet = set()
    newCommands = collections.defaultdict(lambda: [])
    try:
        cache = info.obj.ppCache
    except AttributeError:
        cache = {}
    newCache = {}
    try:
        newCache['fontSize'] = cache['fontSize']
    except KeyError:
        pass
    if processHeadings:
        headingStarts = list(findAllControlFields(fields))
        headingEnds = [findControlEnd(fields, headingSstart) for headingSstart in headingStarts]
        nHeadings = len(headingStarts)
        # Filter out nested headings.
        # Nested headings happen on very few web pages and typically are not meaningful.
        # In theory we can handle nested headings properly, but this greatly overcomplicates the code with only marginal return.
        lastHeadingEnd = -1
        nestedHeadingIndices = set()
        for i in range(nHeadings):
            if headingStarts[i] < lastHeadingEnd:
                nestedHeadingIndices.add(i)
            lastHeadingEnd = headingEnds[i]

        for i, (start, end) in enumerate(zip(headingStarts, headingEnds)):
            if i in nestedHeadingIndices:
                continue
            level = fields[start].field.get('level', None)
            try:
                level = int(level)
            except (ValueError, TypeError):
                continue
                
            hlr = headingLevelRules.get(level, None)
            if hlr is None:
                hlr = headingRule
                
            # If no rule applies (neither earcon nor numeric prosody), let NVDA handle it natively
            if hlr is None and headingLevelRule is None:
                continue
                
            skipSet.add(start)
            skipSet.add(end)

            if headingLevelRule is not None:
                preCommand, postCommand = headingLevelRule.getNumericSpeechCommand(level)
                if isinstance(preCommand, speech.commands.BaseProsodyCommand):
                    pass
                elif isinstance(preCommand, (str, PpSynchronousCommand)):
                    if i == 0 and unit in [textInfos.UNIT_CHARACTER, textInfos.UNIT_WORD]:
                        # Compare with cached heading level - we don't want to repeat heading level on every char or word move
                        if cache.get('headingLevel', None) == level:
                            continue
                    elif reason == OutputReason.QUICKNAV:
                        # During quickNav speak Heading level at the end.
                        preCommand, postCommand = postCommand, preCommand
                elif preCommand is None:
                    pass  # no command configured
                else:
                    log.error(f"new_getTextInfoSpeech: unexpected preCommand type {type(preCommand)} for headingLevelRule")
                if preCommand is not None:
                    if firstHeadingLevelCommand is None:
                        firstHeadingLevelCommand = preCommand
                    newCommands[start].append(preCommand)
                if postCommand is not None:
                    newCommands[end].insert(0, postCommand)
                    
            if hlr is None:
                # If there's a numeric rule but no text rule, we still need to restore the native NVDA text
                # because we added this heading to skipSet
                try:
                    orig_text = original_getPropertiesSpeech(reason=reason, **fields[start].field)
                    if orig_text:
                        newCommands[start].extend(orig_text)
                except Exception as e:
                    log.error(f"Error getting original properties: {e}", exc_info=True)
            else:
                preCommand, postCommand = hlr.speechCommand, hlr.postSpeechCommand
                if isinstance(preCommand, speech.commands.BaseProsodyCommand):
                    pass
                elif isinstance(preCommand, (str, PpSynchronousCommand)):
                    if i == 0 and unit in [textInfos.UNIT_CHARACTER, textInfos.UNIT_WORD]:
                        # Compare with cached heading level - we don't want to repeat heading level on every char or word move
                        if cache.get('headingLevel', None) == level:
                            continue
                    elif reason == OutputReason.QUICKNAV and isinstance(preCommand, str):
                        # During quickNav speak Heading level at the end.
                        preCommand, postCommand = postCommand, preCommand
                elif preCommand is None:
                    pass  # no command configured for this heading level
                else:
                    log.error(f"new_getTextInfoSpeech: unexpected preCommand type {type(preCommand)} for hlr rule")
                    
                speechBehavior = getattr(hlr, 'speechBehavior', 0)
                customText = getattr(hlr, 'customSpeechText', "")
                
                if preCommand is not None:
                    if firstHeadingLevelCommand is None:
                        firstHeadingLevelCommand = preCommand
                    newCommands[start].append(preCommand)
                    
                if speechBehavior == 2 and customText:
                    newCommands[start].append(customText)
                elif speechBehavior == 1:
                    try:
                        orig_text = original_getPropertiesSpeech(reason=reason, **fields[start].field)
                        if orig_text:
                            newCommands[start].extend(orig_text)
                    except Exception as e:
                        log.error(f"Error getting original properties: {e}", exc_info=True)
                        
                if postCommand is not None:
                    newCommands[end].insert(0, postCommand)
                    
    if highlightedRule is not None:
        highlightedStarts = list(findAllControlFields(fields, role=controlTypes.Role.MARKED_CONTENT))
        highlightedEnds = [findControlEnd(fields, highlightedSstart) for highlightedSstart in highlightedStarts]
        nHighlighteds = len(highlightedStarts)
        # Filter out nested highlighteds.
        # This has never been observed in real life.
        lastHighlightedEnd = -1
        nestedHighlightedIndices = set()
        for i in range(nHighlighteds):
            if highlightedStarts[i] < lastHighlightedEnd:
                nestedHighlightedIndices.add(i)
            lastHighlightedEnd = highlightedEnds[i]
        skipSet.update(highlightedStarts)
        skipSet.update(highlightedEnds)
        for i, (start, end) in enumerate(zip(highlightedStarts, highlightedEnds)):
            if i in nestedHighlightedIndices:
                continue
            if highlightedRule is not None:
                preCommand, postCommand = highlightedRule.speechCommand, highlightedRule.postSpeechCommand
                if isinstance(preCommand, str):
                    if i == 0 and unit in [textInfos.UNIT_CHARACTER, textInfos.UNIT_WORD]:
                        # Compare with cached heading level - we don't want to repeat heading level on every char or word move
                        if cache.get('highlighted', None) == True:
                            continue
                    elif reason == OutputReason.QUICKNAV:
                        # During quickNav speak highlighted at the end.
                        preCommand, postCommand = postCommand, preCommand
                if preCommand is not None:
                    newCommands[start].append(preCommand)
                if postCommand is not None:
                    newCommands[end].insert(0, postCommand)

    if fontSizeRule is not None:
        samplePreCommand, samplePostCommand = fontSizeRule.getNumericSpeechCommand(10)
        # If configured to report heading levels and font size via same prosody  command, then skip headings to avoid interference
        skipHeadingsForFontSize = headingLevelRule is not None and isinstance(samplePreCommand, speech.commands.BaseProsodyCommand) and type(samplePreCommand) == type(firstHeadingLevelCommand)
        for begin, end in findAllFormatFieldBrackets(fields):
            if skipHeadingsForFontSize and any(headingStart < begin < headingEnd for headingStart, headingEnd in zip(headingStarts, headingEnds)):
                continue
            try:
                fontSizeStr = fields[begin].field['font-size']
                fontSizeStr =re.sub(" ?pt$", "", fontSizeStr)
                fontSize = float(fontSizeStr)
            except (KeyError, ValueError):
                try:
                    del newCache['fontSize']
                except KeyError:
                    pass
                continue
            prevFontSize = newCache.get('fontSize', None)
            newCache['fontSize'] = fontSize
            preCommand, postCommand = fontSizeRule.getNumericSpeechCommand(fontSize)
            if isinstance(preCommand, speech.commands.BaseProsodyCommand):
                pass
            elif isinstance(preCommand, str):
                if True:
                    # Compare with cached font size
                    if prevFontSize == fontSize:
                        continue
            else:
                raise RuntimeError
            if preCommand is not None:
                newCommands[begin].append(preCommand)
            if postCommand is not None:
                newCommands[end].insert(0, postCommand)
    # italic and bold and stuff
    for textFormatting in [
        TextFormat.BOLD,
        TextFormat.ITALIC,
        TextFormat.UNDERLINE,
        TextFormat.STRIKETHROUGH,
    ]:
        try:
            fRule = formatRules[textFormatting]
        except KeyError:
            continue
        for begin, end in findAllFormatFieldBrackets(fields):
            value = fields[begin].field.get(textFormatting.value, None)
            prevValue = newCache.get(textFormatting.value, None)
            newCache[textFormatting.value] = value
            if value:
                preCommand, postCommand = fRule.speechCommand, fRule.postSpeechCommand
                if isinstance(preCommand, str):
                    if True:
                        # Compare with cached value
                        if prevValue == value:
                            continue
                if preCommand is not None:
                    newCommands[begin].append(preCommand)
                if postCommand is not None:
                    newCommands[end].insert(0, postCommand)
    newCache.update(computeCacheableStateAtEnd(fields))
    info.obj.ppCache = newCache
    
    previousIndex = 0
    fakeTextInfo.setSkipSet(skipSet)
    nFields = len(fields)
    intervalsAndCommands = []
    nIntervals = 0
    emptyIntervals = set()
    newCommandKeys = sorted(newCommands.keys())
    if nFields not in newCommandKeys:
        newCommandKeys.append(nFields)
    for i in newCommandKeys:
        intervalsAndCommands.append((previousIndex, i))
        nIntervals += 1
        # If there are no str fields in this range, skip it, otherwise it'll believe we exited some controls and store that in the cache.
        isEmpty = not any(isinstance(field, str) for field in fields[previousIndex:i])
        if isEmpty:
            emptyIntervals.add(len(intervalsAndCommands) - 1)
        try:
            intervalsAndCommands.append(newCommands[i])
        except KeyError:
            pass
        previousIndex = i
    emptyIndex = 0
    allEmpty = nIntervals == len(emptyIntervals)
    filteredIntervalsAndCommands = []
    # Filtering out empty intervals. However, if all intervals are empty, we would like to keep the first one.
    for i, interval in enumerate(intervalsAndCommands):
        if isinstance(interval, list):
            # injected commands - always keep them
            filteredIntervalsAndCommands.append(interval)
        elif isinstance(interval, tuple):
            isEmpty = i in emptyIntervals
            if not isEmpty or (allEmpty and emptyIndex ==0):
                filteredIntervalsAndCommands.append(interval)
            emptyIndex += int(isEmpty)
        else:
            raise RuntimeError
    
    # Here is the meaning of buffer
    # upstream speech commands return lists of speech sequences
    # We can't merge these lists, otherwise this affects some synthesizers,
    # For example when characters  are being spelled, eSpeak would spell delta as 
    # delta echo lima tango alpha
    # That's because we switch to spelling mode in the first sequence and send delta in the second sequence
    # We also can't have too  many separate sequences, because OneCore is pretty sluggish
    # and adds extra delay on each sequence.
    # Trying to find a good balance point by merging what we can merge,
    # but when upstream function returns a list of 2+ sequences,
    # then yielding them separately.
    buffer = []
    # Even though we have already filtered out empty intervals (e.g. intervals containingg no string to speak),
    # Some of the intervals might still be blank, e.g., if an interval only contains a single whitespace character,
    # NVDA would speak it as blank".
    # We would like to avoid that, so we will suppress blanks on all intervals except for the last one if all previous are blank.
    lastIntervalIndex = [i for i, interval in enumerate(filteredIntervalsAndCommands) if isinstance(interval, tuple)][-1]
    isBlankSoFar = True
    for i, item in enumerate(filteredIntervalsAndCommands):
        if isinstance(item, list):
            # Injected commands
            buffer.extend(item)
        elif isinstance(item, tuple):
            # Interval
            start, end = item
            fakeTextInfo.setStartAndEnd(start, end)
            effectiveSuppressBlanks=True if i < lastIntervalIndex or not isBlankSoFar else suppressBlanks
            if not effectiveSuppressBlanks:
                # We are not suppressing the blanks
                # 1. back up cache
                # 2. Get the sequence with blanks suppressed, so that we can compare it later and decide whether blank is to be spoken
                # 3. Restore the cache if applicable
                if isinstance(useCache, speech.speech.SpeakTextInfoState):
                    useCacheBackup = useCache.copy()
                elif useCache:
                    speakTextInfoStateBackup = speech.speech.SpeakTextInfoState(info.obj)
                suppressedSequences = list(original_getTextInfoSpeech(
                    fakeTextInfo,
                    useCache ,
                    formatConfig,
                    unit ,
                    reason ,
                    _prefixSpeechCommand,
                    onlyInitialFields,
                    suppressBlanks=True,
                ))
                if isinstance(useCache, speech.speech.SpeakTextInfoState):
                    useCache = useCacheBackup
                elif useCache:
                    speakTextInfoStateBackup.updateObj()
            sequences = list(original_getTextInfoSpeech(
                fakeTextInfo,
                useCache ,
                formatConfig,
                unit ,
                reason ,
                _prefixSpeechCommand,
                onlyInitialFields,
                suppressBlanks=effectiveSuppressBlanks,
            ))
            if not effectiveSuppressBlanks:
                blankRule = getActiveRuleContext(otherRules.get(OtherRule.BLANK, []), appName, windowTitle, url)
                if blankRule is not None:
                    # only compare string commands
                    sequenceStrings = [s for ss in sequences for s in ss if isinstance(s, str)]
                    suppressedSequenceStrings = [s for ss in suppressedSequences for s in ss if isinstance(s, str)]
                    if len(sequenceStrings) == 1 + len(suppressedSequenceStrings) and sequenceStrings[:-1] == suppressedSequenceStrings:
                        # Blank detected!
                        blankString = sequenceStrings[-1]
                        blankCommand = blankRule.speechCommand
                        speechBehavior = getattr(blankRule, 'speechBehavior', 0)
                        customText = getattr(blankRule, 'customSpeechText', "")
                        
                        replacement = []
                        if blankCommand:
                            replacement.append(blankCommand)
                        if speechBehavior == 1:
                            replacement.append(blankString)
                        elif speechBehavior == 2 and customText:
                            replacement.append(customText)
                            
                        for idx, subsequence in enumerate(sequences):
                            new_subseq = []
                            for command in subsequence:
                                if command == blankString:
                                    new_subseq.extend(replacement)
                                else:
                                    new_subseq.append(command)
                            sequences[idx] = new_subseq
            isBlank = isBlankSequence(sequences)
            if not isBlank:
                isBlankSoFar = False
            for i, subsequence in enumerate(sequences):
                if i > 0:
                    yield buffer
                    buffer = []
                buffer.extend(subsequence)
            # Whatever is the original value of indentation reporting,
            # we should only report it for the first interval and turn off for all the rest.
            formatConfig["reportLineIndentation"] = ReportLineIndentation.OFF
    if len(buffer) > 0:
        yield buffer

# some random funny Unicode characters
PROPERTY_SPEECH_SIGNATURE = "🪛🪕🚛"
PROPERTY_SPEECH_SIGNATURE2 = "🪼‣⁋"
original_getPropertiesSpeech = None
ignore_get_properties_hook = False
def new_getPropertiesSpeech(
    reason: OutputReason = OutputReason.QUERY,
    **propertyValues,
):
    import config
    import json
    from . import common
    from . import utils
    
    if not isPhoneticPunctuationEnabled() or ignore_get_properties_hook:
        return original_getPropertiesSpeech(reason, **propertyValues)
        
    role = propertyValues.get('role', None)
    
    earcon_signature = None
    customText = None
    speechBehavior = 0
    speak_roles = config.conf["audiothemes"].get("speak_roles", True)
    
    pre_numeric_cmd = None
    post_numeric_cmd = None
    
    if role is not None:
        appName, windowTitle, url = utils.getCurrentContext()
        rule = None
        
        if role == controlTypes.Role.HEADING:
            level = propertyValues.get('level', None)
            if level is not None:
                try:
                    lvl = int(level)
                    headingLevelRules = formatRules.get(getattr(common.TextFormat, f'HEADING{lvl}'), [])
                    rule = getActiveRuleContext(headingLevelRules, appName, windowTitle, url)
                except (ValueError, TypeError):
                    pass
            if rule is None:
                rule = getActiveRuleContext(formatRules.get(common.TextFormat.HEADING, []), appName, windowTitle, url)
                
        if rule is None and role in roleRules:
            rule = getActiveRuleContext(roleRules[role], appName, windowTitle, url)
            
        has_numeric_rule = False
        num_rule = None
        if rule is None and role == controlTypes.Role.HEADING:
            num_rule = getActiveRuleContext(numericFormatRules.get(common.NumericTextFormat.HEADING_LEVEL, []), appName, windowTitle, url)
            if num_rule is not None:
                has_numeric_rule = True
                try:
                    level = int(propertyValues.get('level', 1))
                    pre_numeric_cmd, post_numeric_cmd = num_rule.getNumericSpeechCommand(level)
                except (ValueError, TypeError):
                    pass

        if rule is not None or has_numeric_rule:
            earcon_signature = f"{PROPERTY_SPEECH_SIGNATURE}{role.name}{PROPERTY_SPEECH_SIGNATURE}"
            if rule is not None:
                speechBehavior = getattr(rule, 'speechBehavior', 0)
                if speechBehavior == 2:
                    customText = getattr(rule, 'customSpeechText', "")

    global_fmt = config.conf["audiothemes"].get("announceFormat", "0")
    try:
        roleFormatsJson = config.conf["audiothemes"].get("roleAnnounceFormats", "{}")
        if not hasattr(utils, '_cachedRoleFormatsJson') or utils._cachedRoleFormatsJson != roleFormatsJson:
            utils._cachedRoleFormatsJson = roleFormatsJson
            utils._cachedRoleFormatsDict = json.loads(roleFormatsJson)
        roleFormatsDict = utils._cachedRoleFormatsDict
    except Exception:
        roleFormatsDict = {}

    fmt = "0"
    if role is not None:
        role_key = str(role.value) if hasattr(role, 'value') else str(role)
        fmt = roleFormatsDict.get(role_key, None)
        if fmt is None or fmt == "global":
            fmt = global_fmt

    if len(propertyValues) == 1:
        if 'role' in propertyValues and earcon_signature:
            result = []
            if pre_numeric_cmd:
                result.append(pre_numeric_cmd)
            result.append(earcon_signature)
            if speechBehavior == 2 and customText:
                result.append(customText)
            else:
                role_val = propertyValues['role']
                if hasattr(role_val, 'value'): role_val = role_val.value
                blacklisted_roles = _get_blacklisted_roles()
                user_wants_speech = (speak_roles or role_val == controlTypes.Role.HEADING) and role_val not in blacklisted_roles
                if user_wants_speech and fmt != "sc":
                    result.extend(original_getPropertiesSpeech(reason, **propertyValues))
            if post_numeric_cmd:
                result.append(post_numeric_cmd)
            return result
        
        if 'role' in propertyValues and (not speak_roles or fmt == "sc"):
            role_val = propertyValues['role']
            if hasattr(role_val, 'value'): role_val = role_val.value
            blacklisted_roles = _get_blacklisted_roles()
            if not (role_val == controlTypes.Role.HEADING and role_val not in blacklisted_roles and fmt != "sc"):
                return []
            
        result = original_getPropertiesSpeech(reason, **propertyValues)
        if 'role' in propertyValues and len(result) == 1:
            result = [f"{PROPERTY_SPEECH_SIGNATURE2}{result[0]}{PROPERTY_SPEECH_SIGNATURE2}"]
        return result

    speak_roles = config.conf["audiothemes"].get("speak_roles", True)

    if fmt == "0":
        role_output = []
        speak_text_role = speak_roles
        patchedValues = propertyValues.copy()
        
        if "role" in propertyValues:
            if earcon_signature:
                role_val = propertyValues['role']
                if hasattr(role_val, 'value'): role_val = role_val.value
                blacklisted_roles = _get_blacklisted_roles()
                user_wants_speech = (speak_roles or role_val == controlTypes.Role.HEADING) and role_val not in blacklisted_roles
                
                if speechBehavior == 2 and customText:
                    role_output.append(customText)
                    speak_text_role = (role_val == controlTypes.Role.HEADING)
                elif user_wants_speech:
                    speak_text_role = True
                else:
                    speak_text_role = False
                    
            if not speak_text_role:
                patchedValues.pop("role", None)

        result = original_getPropertiesSpeech(reason, **patchedValues)
        if earcon_signature or role_output or pre_numeric_cmd or post_numeric_cmd:
            # Inject earcon, custom text, and numeric commands into the result
            final_res = []
            if pre_numeric_cmd:
                final_res.append(pre_numeric_cmd)
            final_res.extend(role_output)
            if earcon_signature:
                final_res.append(earcon_signature)
            final_res.extend(result)
            if post_numeric_cmd:
                final_res.append(post_numeric_cmd)
            return final_res
        return result

    ordered_keys = []
    if fmt == "rsc":
        ordered_keys = ["role", "states", "name"]
    elif fmt == "sc":
        ordered_keys = ["states", "name", "role"]
    else:
        ordered_keys = ["name", "role", "value", "states", "description", "keyboardShortcut", "positionInfo"]

    for k in propertyValues:
        if k not in ordered_keys and k != "level":
            ordered_keys.append(k)

    result = []
    for k in ordered_keys:
        if k in propertyValues:
            if k == "role":
                role_output = []
                if pre_numeric_cmd:
                    role_output.append(pre_numeric_cmd)
                    
                speak_text_role = True
                
                if not earcon_signature:
                    role_val = propertyValues['role']
                    if hasattr(role_val, 'value'): role_val = role_val.value
                    blacklisted_roles = _get_blacklisted_roles()
                    user_wants_speech = (speak_roles or role_val == controlTypes.Role.HEADING) and role_val not in blacklisted_roles
                    
                    if fmt == "sc":
                        speak_text_role = False
                    else:
                        speak_text_role = user_wants_speech
                else:
                    if speechBehavior == 2 and customText:
                        role_output.append(customText)
                        speak_text_role = False
                    else:
                        role_val = propertyValues['role']
                        if hasattr(role_val, 'value'): role_val = role_val.value
                        blacklisted_roles = _get_blacklisted_roles()
                        user_wants_speech = (speak_roles or role_val == controlTypes.Role.HEADING) and role_val not in blacklisted_roles
                        if user_wants_speech and fmt != "sc":
                            speak_text_role = True
                        else:
                            speak_text_role = False

                if speak_text_role:
                    kwargs = {"role": propertyValues["role"]}
                    if "level" in propertyValues:
                        kwargs["level"] = propertyValues["level"]
                    part_res = original_getPropertiesSpeech(reason, **kwargs)
                    if part_res:
                        role_output.extend(part_res)
                
                if earcon_signature:
                    role_output.append(earcon_signature)
                    
                if post_numeric_cmd:
                    role_output.append(post_numeric_cmd)
                    
                result.extend(role_output)
            else:
                kwargs = {k: propertyValues[k]}
                part_res = original_getPropertiesSpeech(reason, **kwargs)
                if part_res:
                    result.extend(part_res)
                    
    return result

PROPERTY_SPEECH_PATTERN = re.compile(fr"{PROPERTY_SPEECH_SIGNATURE}(\w+){PROPERTY_SPEECH_SIGNATURE}")
PROPERTY_SPEECH_PATTERN2 = re.compile(fr"{PROPERTY_SPEECH_SIGNATURE2}(.+){PROPERTY_SPEECH_SIGNATURE2}")
original_getControlFieldSpeech = None
def new_getControlFieldSpeech(
    attrs,
    ancestorAttrs,
    fieldType,
    formatConfig=None,
    extraDetail = False,
    reason = None,
):
    import controlTypes
    if not isPhoneticPunctuationEnabled():
        try:
            if fieldType == "start" or getattr(fieldType, "value", fieldType) == "start":
                import globalPluginHandler
                for plugin in globalPluginHandler.runningPlugins:
                    if plugin.__module__ == "globalPlugins.audiothemes":
                        role = attrs.get('role')
                        if role is not None:
                            role_val = getattr(role, "value", role)
                            ignored = {
                                getattr(controlTypes.Role.DOCUMENT, "value", controlTypes.Role.DOCUMENT),
                                getattr(controlTypes.Role.PARAGRAPH, "value", controlTypes.Role.PARAGRAPH),
                                getattr(controlTypes.Role.SECTION, "value", controlTypes.Role.SECTION),
                                getattr(controlTypes.Role.TEXTFRAME, "value", controlTypes.Role.TEXTFRAME),
                                getattr(controlTypes.Role.PANE, "value", controlTypes.Role.PANE),
                                getattr(controlTypes.Role.WINDOW, "value", controlTypes.Role.WINDOW)
                            }
                            if role_val not in ignored:
                                plugin._unspoken_play_role(role_val, attrs.get("states", set()))
                        break
        except Exception:
            pass
        return original_getControlFieldSpeech(attrs, ancestorAttrs, fieldType, formatConfig, extraDetail, reason)
        
    import config
    global ignore_get_properties_hook
    appName, windowTitle, url = utils.getCurrentContext()
    
    original_format = {}
    original_formatConfig_values = {}
    role_to_format_key = {
        controlTypes.Role.LINK: "reportLinks",
        controlTypes.Role.HEADING: "reportHeadings",
        controlTypes.Role.TABLE: "reportTables",
        controlTypes.Role.LIST: "reportLists",
        controlTypes.Role.BLOCKQUOTE: "reportBlockQuotes",
        controlTypes.Role.FRAME: "reportFrames",
        controlTypes.Role.LANDMARK: "reportLandmarks",
        controlTypes.Role.ARTICLE: "reportArticles",
        controlTypes.Role.COMMENT: "reportComments",
    }
    heading_has_rule = False
    for r, key in role_to_format_key.items():
        has_active_rule = getActiveRuleContext(roleRules.get(r, []), appName, windowTitle, url) is not None
        
        if not has_active_rule and r == controlTypes.Role.HEADING:
            for lvl in range(1, 7):
                fmt = getattr(TextFormat, f'HEADING{lvl}', None)
                if fmt and getActiveRuleContext(formatRules.get(fmt, []), appName, windowTitle, url) is not None:
                    has_active_rule = True
                    break
            if not has_active_rule:
                if getActiveRuleContext(formatRules.get(TextFormat.HEADING, []), appName, windowTitle, url) is not None:
                    has_active_rule = True
            if not has_active_rule:
                if getActiveRuleContext(numericFormatRules.get(NumericTextFormat.HEADING_LEVEL, []), appName, windowTitle, url) is not None:
                    has_active_rule = True

        if has_active_rule:
            if r == controlTypes.Role.HEADING:
                heading_has_rule = True
            original_format[key] = config.conf["documentFormatting"].get(key, False)
            config.conf["documentFormatting"][key] = True
            if formatConfig is not None:
                original_formatConfig_values[key] = formatConfig.get(key, False)
                formatConfig[key] = True

    if getActiveRuleContext(stateRules.get(controlTypes.State.CLICKABLE, []), appName, windowTitle, url) is not None:
        original_format["reportClickable"] = config.conf["documentFormatting"].get("reportClickable", False)
        config.conf["documentFormatting"]["reportClickable"] = True
        if formatConfig is not None:
            original_formatConfig_values["reportClickable"] = formatConfig.get("reportClickable", False)
            formatConfig["reportClickable"] = True

    if getActiveRuleContext(stateRules.get(controlTypes.State.VISITED, []), appName, windowTitle, url) is not None:
        original_format["reportLinks"] = config.conf["documentFormatting"].get("reportLinks", False)
        config.conf["documentFormatting"]["reportLinks"] = True
        if formatConfig is not None:
            original_formatConfig_values["reportLinks"] = formatConfig.get("reportLinks", False)
            formatConfig["reportLinks"] = True
            
    level_popped = False
    popped_level_val = None
    if attrs.get('role') == controlTypes.Role.HEADING and heading_has_rule:
        if 'level' in attrs:
            popped_level_val = attrs['level']
            del attrs['level']
            level_popped = True
            
    try:
        result = original_getControlFieldSpeech(attrs, ancestorAttrs, fieldType, formatConfig, extraDetail, reason)
    finally:
        if level_popped:
            attrs['level'] = popped_level_val
        for k, v in original_format.items():
            config.conf["documentFormatting"][k] = v
        if formatConfig is not None:
            for k, v in original_formatConfig_values.items():
                formatConfig[k] = v

    result2 = []
    
    appName, windowTitle, url = utils.getCurrentContext()
    
    # Calculate heading level rules once
    headingLevelRules = {
        level: getActiveRuleContext(formatRules.get(getattr(TextFormat, f'HEADING{level}'), []), appName, windowTitle, url)
        for level in range(1, 7)
    }
    headingRule = getActiveRuleContext(formatRules.get(TextFormat.HEADING, []), appName, windowTitle, url)
    
    patched_attrs = attrs.copy()
    if 'role' in patched_attrs:
        patched_role = patched_attrs['role']
        fmt_key = role_to_format_key.get(patched_role)
        if fmt_key and not original_format.get(fmt_key, True):
            patched_attrs.pop('role', None)
            patched_attrs.pop('level', None)
            
    if 'level' in patched_attrs and 'positionInfo' not in patched_attrs:
        patched_attrs['positionInfo'] = {'level': patched_attrs['level']}
            
    if 'states' in patched_attrs:
        new_states = set(patched_attrs['states'])
        if not original_format.get("reportClickable", True) and controlTypes.State.CLICKABLE in new_states:
            new_states.remove(controlTypes.State.CLICKABLE)
        if not original_format.get("reportLinks", True) and controlTypes.State.VISITED in new_states:
            new_states.remove(controlTypes.State.VISITED)
        patched_attrs['states'] = new_states
    
    for i, utterance in enumerate(result):
        if isinstance(utterance, str):
            if m := PROPERTY_SPEECH_PATTERN.match(utterance):
                # Replacing role speech with earcon
                role_name = m.group(1)
                role = getattr(controlTypes.Role, role_name)
                
                rule = None
                if role == controlTypes.Role.HEADING:
                    level = attrs.get('level', None)
                    try:
                        level = int(level)
                        rule = headingLevelRules.get(level, None)
                    except (ValueError, TypeError):
                        pass
                    
                    if rule is None:
                        rule = headingRule
                
                if rule is None:
                    rule = getActiveRuleContext(roleRules.get(role, []), appName, windowTitle, url)
                    
                post_numeric_cmd = None
                if role == controlTypes.Role.HEADING:
                    num_rule = getActiveRuleContext(numericFormatRules.get(NumericTextFormat.HEADING_LEVEL, []), appName, windowTitle, url)
                    if num_rule is not None:
                        try:
                            level = int(attrs.get('level', 1))
                            pre_cmd, post_numeric_cmd = num_rule.getNumericSpeechCommand(level)
                            if pre_cmd is not None:
                                result2.append(pre_cmd)
                        except (ValueError, TypeError):
                            pass

                if rule is not None:
                    command = rule.speechCommand
                    speechBehavior = getattr(rule, 'speechBehavior', 0)
                    customText = getattr(rule, 'customSpeechText', "")
                    if command:
                        result2.append(command)
                        
                    if speechBehavior == 1:
                        ignore_get_properties_hook = True
                        try:
                            orig_text = speech.speech.getPropertiesSpeech(reason=reason, **patched_attrs)
                        finally:
                            ignore_get_properties_hook = False
                        result2.extend(orig_text)
                    elif speechBehavior == 2 and customText:
                        result2.append(customText)
                else:
                    ignore_get_properties_hook = True
                    try:
                        orig_text = speech.speech.getPropertiesSpeech(reason=reason, **patched_attrs)
                    finally:
                        ignore_get_properties_hook = False
                    result2.extend(orig_text)
                    
                if post_numeric_cmd is not None:
                    result2.append(post_numeric_cmd)
                continue
            elif m := PROPERTY_SPEECH_PATTERN2.match(utterance):
                # Just strip off the signature - this is just a role utterance
                result2.append(m.group(1))
                continue
            elif m := PROPERTY_SPEECH_PATTERN.search(utterance):
                # Extra characters present → "Out of <container>" scenario
                oocRule = getActiveRuleContext(otherRules.get(OtherRule.OUT_OF_CONTAINER, []), appName, windowTitle, url)
                role_name = m.group(1)
                if oocRule is not None:
                    command = oocRule.speechCommand
                    speechBehavior = getattr(oocRule, 'speechBehavior', 0)
                    customText = getattr(oocRule, 'customSpeechText', "")
                    
                    if command:
                        result2.append(command)
                    if speechBehavior == 1:
                        ignore_get_properties_hook = True
                        try:
                            orig_text = speech.speech.getPropertiesSpeech(reason=reason, **patched_attrs)
                        finally:
                            ignore_get_properties_hook = False
                        result2.extend(orig_text)
                    elif speechBehavior == 2 and customText:
                        result2.append(customText)
                    continue
                else:
                    role = getattr(controlTypes.Role, role_name)
                    rule = None
                    if role == controlTypes.Role.HEADING:
                        level = attrs.get('level', None)
                        try:
                            level = int(level)
                            rule = headingLevelRules.get(level, None)
                        except (ValueError, TypeError):
                            pass
                        if rule is None:
                            rule = headingRule
                    
                    if rule is None:
                        rule = getActiveRuleContext(roleRules.get(role, []), appName, windowTitle, url)
                        
                    if rule is not None:
                        command = rule.speechCommand
                        result2.append(_("out of"))
                        result2.append(command)
                    else:
                        orig_text = original_getPropertiesSpeech(reason=reason, **patched_attrs)
                        result2.extend(orig_text)
                    continue
            elif m := PROPERTY_SPEECH_PATTERN2.search(utterance):
                # We have the string, but there are also some other extra characters present.
                # We assume this says something like "Out of frame" - that is we are exiting a container.
                # Since "out of" is possibly translated to other languages, we can't just match it, so we detect presence of extra characters instead.
                oocRule = getActiveRuleContext(otherRules.get(OtherRule.OUT_OF_CONTAINER, []), appName, windowTitle, url)
                if oocRule is not None:
                    command = oocRule.speechCommand
                    speechBehavior = getattr(oocRule, 'speechBehavior', 0)
                    customText = getattr(oocRule, 'customSpeechText', "")
                    
                    if command:
                        result2.append(command)
                    if speechBehavior == 1:
                        restoredUtterance = PROPERTY_SPEECH_PATTERN2.sub(r'\1', utterance)
                        result2.append(restoredUtterance)
                    elif speechBehavior == 2 and customText:
                        result2.append(customText)
                    continue
                else:
                    restoredUtterance = PROPERTY_SPEECH_PATTERN2.sub(r'\1', utterance)
                    result2.append(restoredUtterance)
                    continue
        result2.append(utterance)
    return result2

original_processAndLabelStates = None
def new_processAndLabelStates(
    role,
    states,
    reason,
    positiveStates= None,
    negativeStates=None,
    positiveStateLabelDict={},
    negativeStateLabelDict={},
):
    # Braille provides custom dictionaries for positive and negative states - we don't mess with Braille.
    # However when the dictionaries are empty, we provide our own custom dictionaries.
    if isPhoneticPunctuationEnabled() and len(positiveStateLabelDict) == 0 and len(negativeStateLabelDict) == 0:
        appName, windowTitle, url = utils.getCurrentContext()
        pDict = {}
        for state, ruleList in stateRules.items():
            rule = getActiveRuleContext(ruleList, appName, windowTitle, url)
            if rule is not None:
                val = getRuleStateValue(rule, is_negative=False)
                if val is not None:
                    pDict[state] = val
                        
        nDict = {}
        for state, ruleList in negativeStateRules.items():
            rule = getActiveRuleContext(ruleList, appName, windowTitle, url)
            if rule is not None:
                val = getRuleStateValue(rule, is_negative=True)
                if val is not None:
                    nDict[state] = val
                            
        positiveStateLabelDict = pDict
        negativeStateLabelDict = nDict
    res = original_processAndLabelStates(
        role,
        states,
        reason,
        positiveStates,
        negativeStates,
        positiveStateLabelDict,
        negativeStateLabelDict,
    )
    
    flattened = []
    for item in res:
        if isinstance(item, list):
            flattened.extend(item)
        else:
            flattened.append(item)
    return flattened

original_getTextInfoSpeech_considerSpelling = None
def new_getTextInfoSpeech_considerSpelling(
    unit,
    onlyInitialFields,
    textWithFields,
    reason,
    speechSequence,
    language,
):
    """
    For some reason the original function is set up to drop all the previous commands unless a string is present.
    This inadvertently drops our earcons when navigating by character.
    Specifically "out of container" earcon.
    Overriding the whole function to patch that behavior.
    """
    #if onlyInitialFields or any(isinstance(x, str) for x in speechSequence):
    if onlyInitialFields or any(isinstance(x, (str, PpSynchronousCommand, speech.commands.BaseProsodyCommand)) for x in speechSequence):
        yield speechSequence
    if not onlyInitialFields:
        spellingSequence = list(
            speech.speech.getSpellingSpeech(
                textWithFields[0],
                locale=language,
            ),
        )
        speech.types.logBadSequenceTypes(spellingSequence)
        yield spellingSequence
        if (
            reason == OutputReason.CARET
            and unit == textInfos.UNIT_CHARACTER
            and config.conf["speech"]["delayedCharacterDescriptions"]
        ):
            descriptionSequence = list(
                speech.speech.getSingleCharDescription(
                    textWithFields[0],
                    locale=language,
                ),
            )
            yield descriptionSequence

