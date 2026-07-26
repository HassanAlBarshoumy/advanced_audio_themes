# -*- coding: UTF-8 -*-
# A part of the Advanced Audio Themes addon for NVDA
# Originally part of the Earcons and Speech rules addon for NVDA by Tony Malykh.
# Integrated and maintained by Hassan AlBarshoumy.
# Special thanks: Ahmed Sami
# This file is covered by the GNU General Public License.

import addonHandler
import api
import characterProcessing
import config
import collections
import controlTypes
import copy
import core
from enum import Enum
from functools import lru_cache
import globalVars
import gui
from gui import guiHelper, nvdaControls
from gui.settingsDialogs import SettingsPanel
import json
from logHandler import log
import os
import re
from scriptHandler import script
import speech
import speech.commands
import threading
import tones
import wx

from .common import *
from .utils import *
from .commands import *
from .emoji_handler import is_emoji_enabled, is_emoji_sound_enabled, is_emoji_prefix_enabled, get_emoji_prefix_text, get_emoji_suffix_text, get_emoji_position, get_emoji_sound_position, get_emoji_repeat, get_emoji_volume, find_emojis, is_category_enabled, get_special_prop_for_category, get_emoji_sound_repeat, get_emoji_prefix_repeat, is_emoji_sound_category_enabled, get_emoji_prefix_text_for_category, get_emoji_suffix_text_for_category, get_emoji_volume_for_category, get_emoji_sound_position_for_category, get_emoji_delay_before, get_emoji_delay_after, is_emoji_suppress_role_sound, is_emoji_blacklisted, get_emoji_custom_description
from .handler import SpecialProps
from . import commands
from . import frenzy
from . import utils as _utils_mod
from config.configFlags import ReportLineIndentation
import languageHandler
import shutil
import globalCommands


# audioRuleTypes and audioRule* constants are imported from .common via wildcard import above.
# Do NOT redefine them here — common.py has the complete list including numericProsody, textSubstitution, and noop.

class MaskedString:
    """
    We convert a string into Masked string to prevent rules from acting on it.
    This is useful when we have processed some punctuation marks, such as a comma,
    and would like to feed it to the synth, and avoid any other rules from acting upon it.
    So we temporarily mask the comma, and unmask it at the end.
    """
    
    def __init__(self, s):
        self.s = s

class AudioRule:
    jsonFields = "comment pattern ruleType wavFile builtInWavFile tone duration enabled caseSensitive startAdjustment endAdjustment prosodyName prosodyOffset prosodyMultiplier volume passThrough frenzyType frenzyValue minNumericValue maxNumericValue prosodyMinOffset prosodyMaxOffset replacementPattern suppressStateClutter applicationFilterRegex windowTitleRegex urlRegex speechBehavior customSpeechText customLabel voiceChangeSynthId voiceChangeVoiceId".split()
    def __init__(
        self,
        comment,
        pattern,
        ruleType,
        wavFile=None,
        builtInWavFile=None,
        startAdjustment=0,
        endAdjustment=0,
        tone=None,
        duration=None,
        enabled=True,
        caseSensitive=True,
        prosodyName=None,
        prosodyOffset=None,
        prosodyMultiplier=None,
        volume=100,
        passThrough=False,
        frenzyType=FrenzyType.TEXT.name,
        frenzyValue="",
        minNumericValue=1,
        maxNumericValue=5,
        prosodyMinOffset=-10,
        prosodyMaxOffset=10,
        replacementPattern=None,
        suppressStateClutter=False,
        applicationFilterRegex="",
        windowTitleRegex="",
        urlRegex="",
        speechBehavior=0,
        customSpeechText="",
        customLabel="",
        voiceChangeSynthId="",
        voiceChangeVoiceId="",
    ):
        self.comment = comment
        self.pattern = pattern
        self.ruleType = ruleType
        self.wavFile = wavFile
        self.builtInWavFile = builtInWavFile
        self.startAdjustment = startAdjustment
        self.endAdjustment = endAdjustment
        self.tone = tone
        self.duration = duration
        self.enabled = enabled
        self.caseSensitive = caseSensitive
        self.prosodyName = prosodyName
        self.prosodyOffset = prosodyOffset
        self.prosodyMultiplier = prosodyMultiplier
        self.volume = volume
        self.passThrough = passThrough
        if isinstance(frenzyType, FrenzyType):
            self.frenzyType = frenzyType.name
        else:
            self.frenzyType = frenzyType
        if isinstance(frenzyValue, Enum):
            self.frenzyValue = frenzyValue.name
        else:
            self.frenzyValue = frenzyValue
        self.minNumericValue = minNumericValue
        self.maxNumericValue = maxNumericValue
        self.prosodyMinOffset = prosodyMinOffset
        self.prosodyMaxOffset = prosodyMaxOffset
        self.replacementPattern = replacementPattern
        self.suppressStateClutter = suppressStateClutter
        self.applicationFilterRegex = applicationFilterRegex
        self.windowTitleRegex = windowTitleRegex
        self.urlRegex = urlRegex
        self.speechBehavior = speechBehavior
        self.customSpeechText = customSpeechText
        self.customLabel = customLabel
        self.voiceChangeSynthId = voiceChangeSynthId
        self.voiceChangeVoiceId = voiceChangeVoiceId

        self.regexp = re.compile(self.pattern, 0 if self.caseSensitive else re.IGNORECASE)
        self._applicationFilterRegex = re.compile(applicationFilterRegex)
        self._windowTitleRegex = re.compile(windowTitleRegex)
        self._urlRegex = re.compile(urlRegex)
        self.speechCommand, self.postSpeechCommand = self.getSpeechCommand()

    def getDisplayName(self):
        if getattr(self, "customLabel", ""):
            return self.customLabel
        ft = self.getFrenzyType()
        if ft in [FrenzyType.TEXT, FrenzyType.CHARACTER]:
            return self.comment or self.pattern
        if ft is None:
            return self.comment or self.pattern
        return f"{FRENZY_NAMES_SINGULAR[ft]}:{self.getFrenzyValueStr()}"

    def getReplacementDescription(self):
        if self.ruleType == audioRuleWave:
            return f"Wav: {self.wavFile}"
        elif self.ruleType == audioRuleBuiltInWave:
            return self.builtInWavFile
        elif self.ruleType == audioRuleBeep:
            return f"Beep: {self.tone}@{self.duration}"
        elif self.ruleType == audioRuleProsody:
            if self.prosodyName == VOICE_CHANGE_PROSODY:
                return f"VoiceChange: {self.voiceChangeSynthId}/{self.voiceChangeVoiceId}"
            return f"Prosody: {self.prosodyName}:{self.prosodyOffset}:{self.prosodyMultiplier}"
        elif self.ruleType in [audioRuleTextSubstitution]:
            return f"TextSubstitution: '{self.replacementPattern}'"
        elif self.ruleType in [audioRuleNumericProsody]:
            return "DynamicNumericProsody"
        elif self.ruleType in [audioRuleNoop]:
            return "Noop"
        else:
            raise ValueError()

    def asDict(self):
        return {k:v for k,v in self.__dict__.items() if k in self.jsonFields}
        
    def getFrenzyType(self):
        if not self.frenzyType or len(self.frenzyType) == 0:
            return None
        return getattr(FrenzyType, self.frenzyType)
    
    def getFrenzyValue(self):
        if self.frenzyValue is None:
            return None
        if len(self.frenzyValue) == 0:
            return None
        type = self.getFrenzyType()
        s = self.frenzyValue
        if type == FrenzyType.ROLE:
            return getattr(controlTypes.Role, s)
        elif type in [FrenzyType.STATE, FrenzyType.NEGATIVE_STATE]:
            return getattr(controlTypes.State, s)
        elif type == FrenzyType.FORMAT:
            return getattr(TextFormat, s)
        elif type == FrenzyType.NUMERIC_FORMAT:
            return getattr(NumericTextFormat, s)
        elif type == FrenzyType.OTHER_RULE:
            return getattr(OtherRule, s)
        else:
            raise ValueError

    def getFrenzyValueStr(self):
        if self.frenzyValue is None or len(self.frenzyValue) == 0:
            return None
        type = self.getFrenzyType()
        s = self.frenzyValue
        try:
            if type == FrenzyType.ROLE:
                return controlTypes.role._roleLabels.get(getattr(controlTypes.Role, s, None), s)
            elif type in [FrenzyType.STATE, FrenzyType.NEGATIVE_STATE]:
                return controlTypes.state._stateLabels.get(getattr(controlTypes.State, s, None), s)
            elif type == FrenzyType.FORMAT:
                return TEXT_FORMAT_NAMES.get(self.getFrenzyValue(), s)
            elif type == FrenzyType.NUMERIC_FORMAT:
                return NUMERIC_TEXT_FORMAT_NAMES.get(self.getFrenzyValue(), s)
            elif type == FrenzyType.OTHER_RULE:
                return OTHER_RULE_NAMES.get(self.getFrenzyValue(), s)
            else:
                return s
        except Exception:
            return s

    def getSpeechCommand(self):
        if self.ruleType in [audioRuleBuiltInWave, audioRuleWave]:
            if self.ruleType == audioRuleBuiltInWave:
                wavFile = os.path.join(getSoundsPath(), self.builtInWavFile)
            else:
                wavFile = self.wavFile
            return PpWaveFileCommand(
                wavFile,
                startAdjustment=self.startAdjustment,
                endAdjustment=self.endAdjustment,
                volume=self.volume,
            ), None
        elif self.ruleType == audioRuleBeep:
            return PpBeepCommand(self.tone, self.duration, left=self.volume, right=self.volume), None
        elif self.ruleType == audioRuleProsody:
            if self.prosodyName == VOICE_CHANGE_PROSODY:
                return None, None
            classClass = getProsodyClass(self.prosodyName)
            if self.prosodyOffset is not None:
                # We shouldn't set offset to zero because it means restore defaults and confuses our nested prosody commands algorithm.
                offset = self.prosodyOffset or 0.001
                preCommand = classClass(offset=offset)
            else:
                preCommand = classClass(multiplier=self.prosodyMultiplier)
            postCommand = classClass()
            return preCommand, postCommand
        elif self.ruleType in [audioRuleTextSubstitution]:
            if self.replacementPattern is None:
                raise ValueError
            return self.replacementPattern, None
        elif self.ruleType in [audioRuleNumericProsody, audioRuleNoop]:
            return None, None
        else:
            raise ValueError()

    def getNumericSpeechCommand(self, numericValue):
        if self.ruleType == audioRuleNumericProsody:
            if (
                self.prosodyName is None or
                self.minNumericValue is None or
                self.maxNumericValue is None or 
                self.prosodyMinOffset is None or 
                self.prosodyMaxOffset  is None
            ):
                raise ValueError
            className = self.prosodyName
            className = className[0].upper() + className[1:] + 'Command'
            classClass = getattr(speech.commands, className)
            numericValue = max(self.minNumericValue, min(self.maxNumericValue, numericValue))
            if self.maxNumericValue == self.minNumericValue:
                offset = self.prosodyMinOffset
            else:
                offset = self.prosodyMinOffset + (self.prosodyMaxOffset - self.prosodyMinOffset) * (numericValue - self.minNumericValue) / (self.maxNumericValue - self.minNumericValue)
            if offset == 0:
                offset = 0.001
            preCommand = classClass(offset=offset)
            postCommand = classClass()
            return preCommand, postCommand
        elif self.ruleType == audioRuleTextSubstitution:
            if self.replacementPattern is None:
                raise ValueError
            preCommand = self.replacementPattern.format(numericValue)
            return preCommand, None
        else:
            raise ValueError()

    def processString(self, s, *args, **kwargs):
        if not self.enabled:
            yield s
            return
        for command in self.processStringInternal(s, *args, **kwargs):
            if command is None:
                continue
            if isinstance(command, str):
                if len(command) > 0:
                    yield command
            else:
                yield command

    def processStringInternal(self, s, symbolLevel, language):
        index = 0
        for match in self.regexp.finditer(s):
            index2 = match.start(0)
            yield s[index:index2]
            if self.speechCommand is not None:
                yield self.speechCommand
            
            speechBehavior = getattr(self, 'speechBehavior', 0)
            customText = getattr(self, 'customSpeechText', "")
            
            spoken_item = None
            if speechBehavior == 1 or (speechBehavior == 0 and self.passThrough):
                # returning masked string to avoid other rules processing this punctuation mark again
                spoken_item = MaskedString(match.group(0))
            elif speechBehavior == 2 and customText:
                spoken_item = MaskedString(customText)
            elif self.postSpeechCommand is not None:
                # For prosody commands with no explicit text behavior, we must output the original text
                spoken_item = match.group(0)
                
            if spoken_item is not None:
                yield spoken_item
                
            if self.postSpeechCommand is not None:
                yield self.postSpeechCommand
            index = match.end(0)
        yield s[index:]


rulesByFrenzy = None
characterRules = None
allProsodies = None
cached_passThrough_regex = None
rulesFileName = os.path.join(globalVars.appArgs.configPath, "earconsAndSpeechRules.json")
ppRulesFileName = os.path.join(globalVars.appArgs.configPath, "phoneticPunctuationRules.json")
defaultRulesFileName = os.path.join(os.path.dirname(__file__), "defaultEarconsAndSpeechRules.json")
_rules_lock = threading.Lock()
def reloadRules():
    global rulesByFrenzy, characterRules, allProsodies
    initialAttempt = rulesByFrenzy == None
    if not os.path.exists(rulesFileName):
        if os.path.exists(ppRulesFileName):
            shutil.copy(ppRulesFileName, rulesFileName)
            os.replace(ppRulesFileName, ppRulesFileName + ".bak")
            wx.CallAfter(
                gui.messageBox,
                _(
                    "Phonetic punctuation add-on has been renamed to Earcons and Speech Rules.\n"
                    "We have automatically migrated all your phonetic punctuation rules to Earcons and Speech Rules add-on, so no further action is required.\n"
                    "Please feel free to explore add-on settings to discover new features.\n"
                ),
                _("Earcons and Speech Rules add-on"),
                wx.OK|wx.ICON_INFORMATION,
            )
        else:
            shutil.copy(defaultRulesFileName, rulesFileName)
        
    with open(rulesFileName, "r", encoding="utf-8") as f:
        rulesConfig = f.read()
    newRulesByFrenzy = {
        frenzy: []
        for frenzy in FrenzyType
    }
    newAllProsodies = set()
    errors = []
    for ruleDict in json.loads(rulesConfig):
        try:
            rule = AudioRule(**ruleDict)
        except Exception as e:
            errors.append(e)
        else:
            try:
                frenzyType = rule.getFrenzyType()
            except Exception as e:
                errors.append(e)
                continue
            if frenzyType is None:
                errors.append(ValueError(f"Rule {rule.pattern!r} returned None for getFrenzyType()"))
                continue
            newRulesByFrenzy[frenzyType].append(rule)
            if rule.enabled and rule.ruleType == audioRuleProsody and rule.prosodyName != VOICE_CHANGE_PROSODY:
                newAllProsodies.add(rule.prosodyName)
    if len(errors) > 0:
        log.exception(f"Failed to load {len(errors)} audio rules; last exception:", errors[-1])
        wx.CallAfter(
            gui.messageBox,
            _("Failed to load {count} audio rule(s). They may have invalid fields or be corrupted.\nCheck the NVDA log for details.").format(count=len(errors)),
            _("Earcons and Speech Rules"),
            wx.OK|wx.ICON_WARNING,
        )
    
    newCharacterRules = {
        rule.pattern: rule
        for rule in newRulesByFrenzy[FrenzyType.CHARACTER]
        if rule.enabled
    }
    
    pattern = "|".join([
        rule.pattern
        for rule in newRulesByFrenzy[FrenzyType.TEXT]
        if rule.enabled and rule.passThrough
    ])
    if pattern:
        pattern = f"({pattern})+"
        try:
            new_cached_passThrough_regex = re.compile(pattern, re.UNICODE)
        except Exception as e:
            log.warning(f"Failed to compile passThrough regex {pattern!r}: {e}")
            new_cached_passThrough_regex = None
    else:
        new_cached_passThrough_regex = None

    # global _rules_lock, cached_passThrough_regex
    with _rules_lock:
        rulesByFrenzy = newRulesByFrenzy
        allProsodies = newAllProsodies
        characterRules = newCharacterRules
        cached_passThrough_regex = new_cached_passThrough_regex
    _prosody_setting_cache.clear()

    frenzy.updateRules()

def onPostNvdaStartup():
    # Deferred reloadRules from module-level __init__ to avoid blocking startup.
    try:
        reloadRules()
    except Exception:
        log.error("AudioThemes: Failed to reload rules at startup", exc_info=True)
    if rulesByFrenzy and any([len(rule.urlRegex) > 0 for rule in rulesByFrenzy.get(FrenzyType.TEXT, [])]) and not isURLResolutionAvailable():
        log.warning("BrowserNav not available; text rules with URL filter will be disabled")
        wx.CallAfter(
            gui.messageBox,
            _(
                "Error initializing some text rules of Earcons and Speech Rules add-on since they contain URL filter.\n"
                "URL detection feature requires BrowserNav v2.6.2 or later add-on to be installed.\n"
                "However it is either not installed, or failed to initialize.\n"
                "Please install the latest BrowserNav add-on from add-on store and restart NVDA.\n"
                "In the mean time all text rules with URL filter will be disabled.\n"
            ),
            _("Earcons and speech rules add-on Error"),
            wx.ICON_ERROR | wx.OK,
        )
    # Load CLDR emoji data in background (lazy, will use cache or download)
    import threading
    threading.Thread(target=_load_cldr_emoji_data, daemon=True).start()
    # Patch NVDAExtensionGlobalPlugin's speech paths if present
    import sys
    for mod_name in list(sys.modules.keys()):
        if 'NVDAExtensionGlobalPlugin' in mod_name and 'speechEx' in mod_name:
            try:
                speechEx = sys.modules[mod_name]
                if not hasattr(speechEx, '_myGetTextInfoSpeech') or not callable(speechEx._myGetTextInfoSpeech):
                    log.debugWarning(f"NVDAExtensionGlobalPlugin module {mod_name} has no callable _myGetTextInfoSpeech, skipping patch")
                    break
                from speech import sayAll
                global _original_ext_speechEx, _original_ext_sayAll
                _original_ext_speechEx = speechEx._myGetTextInfoSpeech
                _original_ext_sayAll = sayAll.SayAllHandler._getTextInfoSpeech
                def _patched_myGet(info, useCache=True, formatConfig=None, unit=None, reason=None, _prefixSpeechCommand=None, onlyInitialFields=False, suppressBlanks=False):
                    if reason is None:
                        reason = controlTypes.OutputReason.QUERY
                    yield from frenzy.new_getTextInfoSpeech(info, useCache, formatConfig, unit, reason, _prefixSpeechCommand, onlyInitialFields, suppressBlanks)
                speechEx._myGetTextInfoSpeech = _patched_myGet
                # Also patch SayAllHandler._getTextInfoSpeech, which received a direct
                # reference to the original _myGetTextInfoSpeech at initialize() time.
                sayAll.SayAllHandler._getTextInfoSpeech = _patched_myGet
                log.warning(f"Patched NVDAExtensionGlobalPlugin speech paths in module: {mod_name}")
            except Exception as e:
                log.warning(f"Failed to patch NVDAExtensionGlobalPlugin speech paths: {e}", exc_info=True)
            break


def _load_cldr_emoji_data():
    from . import emoji_cldr_data
    emoji_cldr_data.load()

_pp_post_startup_handler = core.postNvdaStartup.register(onPostNvdaStartup)

originalSpeechSpeechSpeak = None
originalSpeechCancel = None
originalProcessSpeechSymbols = None

_cached_speech_symbolLevel = 100

def refreshCachedConfig():
    global _cached_speech_symbolLevel
    try:
        _cached_speech_symbolLevel = config.conf["speech"]["symbolLevel"]
    except Exception:
        _cached_speech_symbolLevel = 100
    _utils_mod._reset_pp_enabled_cache()

def preSpeak(speechSequence, symbolLevel=None, *args, **kwargs):
    global speechCancelledFlag
    _utils_mod._reset_pp_enabled_cache()
    try:
        if isPhoneticPunctuationEnabled():
            if symbolLevel is None:
                symbolLevel = _cached_speech_symbolLevel
            newSequence = speechSequence
            language = speech.getCurrentLanguage()
            appName, windowTitle, url = getCurrentContext()
            with _rules_lock:
                text_rules = rulesByFrenzy.get(FrenzyType.TEXT, []) if rulesByFrenzy else []
            for rule in text_rules:
                try:
                    if len(rule.applicationFilterRegex) > 0 and not rule._applicationFilterRegex.search(appName):
                        continue
                    if len(rule.windowTitleRegex) > 0 and not rule._windowTitleRegex.search(windowTitle):
                        continue
                    if (
                        len(rule.urlRegex) > 0 
                        and (
                            url is None
                            or not rule._urlRegex.search(url)
                        )
                    ):
                        continue
                    newSequence = processRule(newSequence, rule, symbolLevel, language)
                except Exception:
                    continue
            resetProsodiesSequence = []
            if speechCancelledFlag:
                try:
                    resetProsodiesSequence = resetProsodies([])
                except Exception:
                    resetProsodiesSequence = []
                speechCancelledFlag = False
            newSequence = postProcessSynchronousCommands(newSequence, symbolLevel)
            newSequence = resetProsodiesSequence + newSequence
            mylog(str(newSequence))
        else:
            newSequence = speechSequence
        # Emoji processing
        if is_emoji_enabled():
            newSequence = _processEmojiSequence(newSequence)
        newSequence = newSequence + [' '] # Otherwise v2024.2 throws weird Braille Exception + 
        
        return originalSpeechSpeechSpeak(newSequence, symbolLevel=symbolLevel, *args, **kwargs)
    except Exception as e:
        log.error(f"AudioThemes preSpeak error: {e}", exc_info=True)
        if originalSpeechSpeechSpeak is not None:
            return originalSpeechSpeechSpeak(speechSequence, symbolLevel=symbolLevel, *args, **kwargs)

class EmojiSoundCommand(speech.commands.BaseCallbackCommand):
    """Plays emoji sound at the correct position during speech.
    Tries category-specific sound first, then emoji_before/emoji_after/emoji, then general fallback.
    """
    def __init__(self, category=None, position=None, sound_key=SpecialProps.emoji):
        self.category = category
        self.position = position
        self.sound_key = sound_key

    def run(self):
        try:
            handler = _utils_mod._handler_ref
            if handler and handler.enabled and handler.active_theme:
                cat_prop = get_special_prop_for_category(self.category) if self.category is not None else None
                vol = get_emoji_volume_for_category(self.category) if self.category is not None else get_emoji_volume()
                with handler.active_theme._lock:
                    keys_to_try = []
                    if cat_prop is not None:
                        keys_to_try.append(cat_prop)
                    if self.sound_key != SpecialProps.emoji:
                        keys_to_try.append(self.sound_key)
                    keys_to_try.append(SpecialProps.emoji)
                    key = None
                    for k in keys_to_try:
                        if k in handler.active_theme.sounds:
                            key = k
                            break
                if key is not None:
                    handler.play({"name": "emoji", "role": 0, "volume_override": vol / 100.0}, key)
        except Exception as e:
            log.warning(f"EmojiSoundCommand.run() failed: {e}")


# Module-level flag for emoji role sound suppression
_suppress_role_sound_flag = False
_suppress_role_sound_lock = threading.Lock()

def _processEmojiSequence(sequence):
    global _suppress_role_sound_flag
    master_enabled = is_emoji_enabled()
    if not master_enabled:
        with _suppress_role_sound_lock:
            _suppress_role_sound_flag = False
        return sequence
    do_prefix_global = is_emoji_prefix_enabled()
    do_sound_global = is_emoji_sound_enabled()
    global_position = get_emoji_position()
    global_sound_position = get_emoji_sound_position()
    global_prefix = get_emoji_prefix_text()
    global_suffix = get_emoji_suffix_text()
    sound_repeat = get_emoji_sound_repeat()
    prefix_repeat = get_emoji_prefix_repeat()
    delay_before = get_emoji_delay_before()
    delay_after = get_emoji_delay_after()
    suppress_role = is_emoji_suppress_role_sound()
    found_emoji = False

    def _make_emoji_commands(cat, snd_pos, delay_b, delay_a, emoji_char=None):
        before = []
        after = []
        effective_snd_pos = snd_pos
        if cat is not None:
            cat_snd_pos = get_emoji_sound_position_for_category(cat)
            if cat_snd_pos != get_emoji_sound_position():
                effective_snd_pos = cat_snd_pos
        effective_prefix = get_emoji_prefix_text_for_category(cat) if cat is not None else global_prefix
        effective_suffix = get_emoji_suffix_text_for_category(cat) if cat is not None else global_suffix
        effective_pos = global_position
        if do_sound_global and effective_snd_pos != "none":
            if delay_b > 0:
                before.append(speech.commands.BreakCommand(delay_b))
            if effective_snd_pos in ("before", "both"):
                before.append(EmojiSoundCommand(category=cat, position="before", sound_key=SpecialProps.emoji_before))
            if effective_snd_pos in ("after", "both"):
                after.append(EmojiSoundCommand(category=cat, position="after", sound_key=SpecialProps.emoji_after))
            if delay_a > 0:
                after.append(speech.commands.BreakCommand(delay_a))
        if do_prefix_global and effective_pos != "none":
            prefix_text = effective_prefix + " " if effective_prefix else ""
            suffix_text = effective_suffix + " " if effective_suffix else ""
            if effective_pos in ("before", "both") and prefix_text.strip():
                before.append(prefix_text)
            if effective_pos in ("after", "both") and suffix_text.strip():
                after.append(suffix_text)
        return before, after

    def _get_emoji_text(emoji_char):
        desc = get_emoji_custom_description(emoji_char)
        if desc:
            return desc
        return emoji_char

    newSeq = []
    for item in sequence:
        if not isinstance(item, str):
            newSeq.append(item)
            continue
        emojis = find_emojis(item)
        if not emojis:
            newSeq.append(item)
            continue
        cats = {cat for _, cat, _, _ in emojis}
        if not any(is_category_enabled(c) for c in cats):
            newSeq.append(item)
            continue

        found_emoji = True

        # Filter blacklisted emojis
        emojis = [(e, c, s, en) for e, c, s, en in emojis if not is_emoji_blacklisted(e)]
        if not emojis:
            newSeq.append(item)
            continue

        # Determine if we have any sound or prefix to add
        has_any_sound = do_sound_global and global_sound_position != "none"
        has_any_prefix = do_prefix_global and global_position != "none"

        if not has_any_sound and not has_any_prefix:
            newSeq.append(item)
            continue

        # Determine repeat modes
        effective_sound_repeat = sound_repeat
        effective_prefix_repeat = prefix_repeat

        if effective_sound_repeat == "per_block" and effective_prefix_repeat == "per_block":
            # Both per_block: single block-level instructions
            before_cmds, after_cmds = _make_emoji_commands(None, global_sound_position, delay_before, delay_after)
            newSeq.extend(before_cmds)
            newSeq.append(item)
            newSeq.extend(after_cmds)
        elif effective_sound_repeat == "per_block" and effective_prefix_repeat == "per_emoji":
            # Sound per_block, prefix per_emoji
            # Insert block sound commands around the whole block, prefix per emoji inside
            snd_before_cmds, snd_after_cmds = _make_emoji_commands(None, global_sound_position, delay_before, delay_after)
            items = []
            items.extend(snd_before_cmds)
            last_end = 0
            for emoji, cat, start, end in emojis:
                if not is_category_enabled(cat):
                    continue
                items.append(item[last_end:start])
                pfx_before, pfx_after = _make_emoji_commands(cat, "none", 0, 0)
                items.extend(pfx_before)
                items.append(_get_emoji_text(emoji))
                items.extend(pfx_after)
                last_end = end
            items.append(item[last_end:])
            items.extend(snd_after_cmds)
            merged = _merge_strings(items)
            newSeq.extend(merged)
        elif effective_sound_repeat == "per_emoji" and effective_prefix_repeat == "per_block":
            # Sound per_emoji, prefix per_block
            pfx_before, pfx_after = _make_emoji_commands(None, "none", 0, 0)
            items = []
            items.extend(pfx_before)
            last_end = 0
            for emoji, cat, start, end in emojis:
                if not is_category_enabled(cat):
                    continue
                items.append(item[last_end:start])
                snd_before, snd_after = _make_emoji_commands(cat, global_sound_position, delay_before, delay_after)
                items.extend(snd_before)
                items.append(_get_emoji_text(emoji))
                items.extend(snd_after)
                last_end = end
            items.append(item[last_end:])
            items.extend(pfx_after)
            merged = _merge_strings(items)
            newSeq.extend(merged)
        else:
            # Both per_emoji: insert sound and prefix per emoji
            items = []
            last_end = 0
            for emoji, cat, start, end in emojis:
                if not is_category_enabled(cat):
                    continue
                items.append(item[last_end:start])
                before_cmds, after_cmds = _make_emoji_commands(cat, global_sound_position, delay_before, delay_after)
                items.extend(before_cmds)
                items.append(_get_emoji_text(emoji))
                items.extend(after_cmds)
                last_end = end
            items.append(item[last_end:])
            merged = _merge_strings(items)
            newSeq.extend(merged)
    with _suppress_role_sound_lock:
        _suppress_role_sound_flag = found_emoji and suppress_role
    return newSeq


def _merge_strings(items):
    """Merge adjacent string items in a list."""
    merged = []
    buf = ""
    for x in items:
        if isinstance(x, str):
            buf += x
        else:
            if buf:
                merged.append(buf)
                buf = ""
            merged.append(x)
    if buf:
        merged.append(buf)
    return merged

speechCancelledFlag = False

def is_emoji_suppress_role_flag_set():
    """Check if the current utterance should suppress role sounds due to emoji presence."""
    with _suppress_role_sound_lock:
        return _suppress_role_sound_flag

def preCancelSpeech(*args, **kwargs):
    global speechCancelledFlag
    speechCancelledFlag = True
    _utils_mod._reset_pp_enabled_cache()
    try:
        if isPhoneticPunctuationEnabled():
            commands.terminateCurrentChain()
    except Exception:
        pass
    originalSpeechCancel(*args, **kwargs)
    

def preProcessSpeechSymbols(locale, text, level):
    if not cached_passThrough_regex:
        return originalProcessSpeechSymbols(locale, text, level)
    try:
        r = cached_passThrough_regex
        prevIndex = 0
        result = []
        for m in r.finditer(text):
            start = m.start(0)
            end = m.end(0)
            prefix = text[prevIndex:start]
            if len(prefix) > 0 and not speech.isBlank(prefix):
                chunk = originalProcessSpeechSymbols(locale, prefix, level)
                result.append(chunk)
            result.append(m.group(0))
            prevIndex = end
        suffix = text[prevIndex:]
        if (
            prevIndex == 0
            or (
                len(suffix) > 0 and
                not speech.isBlank(suffix)
            )
        ):
            chunk = originalProcessSpeechSymbols(locale, suffix, level)
            result.append(chunk)
        finalResult = "".join(result)
        return finalResult
    except Exception as e:
        log.error(f"AudioThemes preProcessSpeechSymbols error: {e}", exc_info=True)
        return originalProcessSpeechSymbols(locale, text, level)


highLevelSpeakFunctionNames = {
    speech.speech: [
        #'speakMessage',
        #'speakSsml',
        #'speakSpelling',
        #'speakObjectProperties',
        #'speakObject',
        #'speakText',
        #'speakPreselectedText',
        #'speakSelectionMessage',
        'speakTextInfo',
    ],
    globalCommands.GlobalCommands: [
        #'script_navigatorObject_current',
        #'script_reportCurrentFocus',
    ],
}
originalHighLevelSpeakFunctions = {}
def monkeyPatchRestoreProsodyInAllHighLevelSpeakFunctions():
    def createFunctor(targetFunction, functionName):
        def functor(*args, **kwargs):
            return targetFunction(*args, **kwargs)
        return functor
    
    for module, functionNames in highLevelSpeakFunctionNames.items():
        originalHighLevelSpeakFunctions[module] = {}
        for functionName in functionNames:
            try:
                function = getattr(module, functionName)
            except AttributeError:
                continue
            originalHighLevelSpeakFunctions[module][functionName] = function
            replacementFunctor = createFunctor(function, functionName)
            setattr(module, functionName, replacementFunctor)
            if module == speech.speech:
                setattr(speech, functionName, replacementFunctor)

def monkeyUnpatchRestoreProsodyInAllHighLevelSpeakFunctions():
    for module, d in originalHighLevelSpeakFunctions.items():
        for functionName, originalFunction in d.items():
            setattr(module, functionName, originalFunction)
            if module == speech.speech:
                setattr(speech, functionName, originalFunction)
    
def injectMonkeyPatches():
    global originalSpeechSpeechSpeak, originalSpeechCancel, originalProcessSpeechSymbols
    
    if originalSpeechSpeechSpeak is None:
        originalSpeechSpeechSpeak = speech.speech.speak
    speech.speech.speak = preSpeak
    speech.speak = speech.speech.speak
    try:
        speech.sayAll.SayAllHandler.speechWithoutPausesInstance.speak = speech.speech.speak
    except Exception:
        pass
    
    if originalSpeechCancel is None:
        originalSpeechCancel = speech.speech.cancelSpeech
    speech.speech.cancelSpeech = preCancelSpeech
    speech.cancelSpeech = speech.speech.cancelSpeech
    
    if originalProcessSpeechSymbols is None:
        originalProcessSpeechSymbols = characterProcessing.processSpeechSymbols
    characterProcessing.processSpeechSymbols = preProcessSpeechSymbols
    
    # Register reloadRules to config profile switch instead of monkey patching tones.initialize
    import config
    try:
        config.post_configProfileSwitch.register(reloadRules)
    except AttributeError:
        pass # Not available in older NVDA versions
    
    try:
        frenzy.monkeyPatch()
    except Exception as e:
        log.warning(f"AudioThemes: frenzy.monkeyPatch() failed: {e}", exc_info=True)
    
    global original_processSpeechSymbol
    if original_processSpeechSymbol is None:
        original_processSpeechSymbol = characterProcessing.processSpeechSymbol
    characterProcessing.processSpeechSymbol = new_processSpeechSymbol
    
    global original_getIndentationSpeech
    if original_getIndentationSpeech is None:
        original_getIndentationSpeech = speech.speech.getIndentationSpeech
    speech.speech.getIndentationSpeech = new_getIndentationSpeech
    
    global original_getSelectionMessageSpeech
    if original_getSelectionMessageSpeech is None:
        original_getSelectionMessageSpeech = speech.speech._getSelectionMessageSpeech
    speech.speech._getSelectionMessageSpeech = new_getSelectionMessageSpeech
    
    #monkeyPatchRestoreProsodyInAllHighLevelSpeakFunctions()

def restoreMonkeyPatches():
    # global originalSpeechSpeechSpeak, originalSpeechCancel
    # CRITICAL: frenzy.monkeyUnpatch() must run BEFORE we restore speak,
    # because frenzy.monkeyUnpatch() sets speech.speech.speak = _original_speak,
    # which was captured as preSpeak (our function), not the real NVDA original.
    frenzy.monkeyUnpatch()
    if originalSpeechSpeechSpeak is not None:
        speech.speech.speak = originalSpeechSpeechSpeak
        speech.speak = speech.speech.speak
        try:
            speech.sayAll.SayAllHandler.speechWithoutPausesInstance.speak = speech.speech.speak
        except Exception:
            pass
    if originalSpeechCancel is not None:
        speech.speech.cancelSpeech = originalSpeechCancel
        speech.cancelSpeech = speech.speech.cancelSpeech
    if originalProcessSpeechSymbols is not None:
        characterProcessing.processSpeechSymbols = originalProcessSpeechSymbols
    
    if original_processSpeechSymbol is not None:
        characterProcessing.processSpeechSymbol = original_processSpeechSymbol
    if original_getIndentationSpeech is not None:
        speech.speech.getIndentationSpeech = original_getIndentationSpeech
    if original_getSelectionMessageSpeech is not None:
        speech.speech._getSelectionMessageSpeech = original_getSelectionMessageSpeech
    
    # Restore NVDAExtensionGlobalPlugin speech patches
    if _original_ext_speechEx is not None:
        try:
            import sys
            for mod_name in list(sys.modules.keys()):
                if 'NVDAExtensionGlobalPlugin' in mod_name and 'speechEx' in mod_name:
                    speechEx = sys.modules[mod_name]
                    if hasattr(speechEx, '_myGetTextInfoSpeech'):
                        speechEx._myGetTextInfoSpeech = _original_ext_speechEx
                    break
        except Exception as e:
            log.debugWarning(f"Failed to restore NVDAExtensionGlobalPlugin speechEx patch: {e}")
    if _original_ext_sayAll is not None:
        try:
            from speech import sayAll
            sayAll.SayAllHandler._getTextInfoSpeech = _original_ext_sayAll
        except Exception as e:
            log.debugWarning(f"Failed to restore SayAllHandler patch: {e}")
    
    try:
        import config
        config.post_configProfileSwitch.unregister(reloadRules)
    except (AttributeError, ValueError):
        pass
    from core import postNvdaStartup
    try:
        postNvdaStartup.unregister(onPostNvdaStartup)
    except (AttributeError, ValueError):
        pass


def processRule(speechSequence, rule, symbolLevel, language):
    newSequence = []
    for command in speechSequence:
        if isinstance(command, str):
            try:
                newSequence.extend(rule.processString(command, symbolLevel, language))
            except Exception:
                newSequence.append(command)
        else:
            newSequence.append(command)
    return newSequence

def postProcessSynchronousCommands(speechSequence, symbolLevel):
    """
    This function groups together adjacent earcons.
    For some reason if we issue multiple adjacent wave commands, then either some of them don't get triggered at all,
    or there are extra silence in between.
    To work around that we replace adjacent earcons with a single PPChainCommand,
    that is clever enough to play all earcons with the right timing.
    Then we apply some more tweaks to fix other glitches.
    We also connect earcons separated by some meaningless commands together into a single chain.
    Examples of meaningless commands are LangChain commands or empty strings.
    """
    def isEmptyString(command):
        if not isinstance(command, str):
            return False
        if not command.strip():
            return True
        return False
    hasNonEmptyString = False
    newSequence = []
    excludeIndices = set()
    for i, command in enumerate(speechSequence):
        if i in excludeIndices:
            continue
        if isinstance(command, PpSynchronousCommand):
            chain = [command]
            for j in range(i+1, len(speechSequence)):
                cj = speechSequence[j]
                if isinstance(cj, PpSynchronousCommand):
                    chain.append(cj)
                    excludeIndices.add(j)
                elif isEmptyString(cj):
                    excludeIndices.add(j)
                elif isinstance(cj, (speech.commands.LangChangeCommand, MaskedString, speech.commands.BaseProsodyCommand)):
                    pass
                else:
                    break
            chainCommand = PpChainCommand(chain)
            duration = chainCommand.getDuration()
            newSequence.append(chainCommand)
            # Removed BreakCommand to allow speech and audio to play simultaneously without delay
            # newSequence.append(speech.commands.BreakCommand(duration))
        elif not isEmptyString(command):
            if isinstance(command, str):
                hasNonEmptyString = True
            newSequence.append(command)
    newSequence = eloquenceFix(newSequence, hasNonEmptyString)
    newSequence = unmaskMaskedStrings(newSequence)
    newSequence = fixProsodyCommands(newSequence)
    return newSequence

def eloquenceFix(speechSequence, hasNonEmptyString=None):
    """
    With some versions of eloquence driver, when the entire utterance has been replaced with audio icons, and therefore there is nothing else to speak,
    the driver for some reason issues the callback command after the break command, not before.
    To work around this, we detect this case and remove break command completely.
    """
    if hasNonEmptyString is not None:
        hasNonEmpty = hasNonEmptyString
    else:
        language = speech.getCurrentLanguage()
        symbolLevel = _cached_speech_symbolLevel
        try:
            hasNonEmpty = any(
                isinstance(element, str)
                and not speech.isBlank(speech.processText(language, element, symbolLevel))
                for element in speechSequence
            )
        except Exception:
            hasNonEmpty = any(isinstance(element, str) and element.strip() for element in speechSequence)
    if hasNonEmpty:
        return speechSequence
    indicesToRemove = []
    for i in range(1, len(speechSequence)):
        if  (
            isinstance(speechSequence[i], speech.commands.BreakCommand)
            and isinstance(speechSequence[i-1], PpChainCommand)
        ):
            indicesToRemove.append(i)
    return [speechSequence[i] for i in range(len(speechSequence)) if i not in indicesToRemove]

def unmaskMaskedStrings(sequence):
    result = []
    for item in sequence:
        if isinstance(item, MaskedString):
            result.append(item.s)
        else:
            result.append(item)
    return result

prosodyStacks = collections.defaultdict(lambda: [])
prosodyOffsets = collections.defaultdict(lambda: 0)
_prosody_setting_cache = {}
def _findProsodySetting(cls):
    cached = _prosody_setting_cache.get(cls)
    if cached is not None or cls in _prosody_setting_cache:
        return cached
    clsName = cls.__name__
    commandSuffix = 'Command'
    if not clsName.endswith(commandSuffix):
        return None
    prosodyName = clsName[:-len(commandSuffix)].lower()
    for srs in globalVars.settingsRing.settings:
        if srs.setting.id == prosodyName:
            _prosody_setting_cache[cls] = srs
            return srs
    _prosody_setting_cache[cls] = None
    return None
def fixProsodyCommands(sequence):
    """
    Prosody commands in NVDA don't support nesting natively.
    E.g., if you increase pitch by 10, and then increase pitch by 10 again, these numbers don't add up.
    The latter pitch command will simply override the former one.
    That is not desired behavior; we would like pitch offsets to be additive.
    We can't deal with multiplicative  prosody commands, so we just don't support them here.
    Adjusting prosody offsets in this function so that they support nesting.
    """
    # global prosodyStacks, prosodyOffsets
    try:
        result = []
        for i, command in enumerate(sequence):
            if isinstance(command, speech.commands.BaseProsodyCommand):
                cls = type(command)
                if command._multiplier != 1:
                    log.error("Multiplicative prosody commands detected. This is not supported by Earcons and Speech Rules add-on.")
                    return sequence
                commandOffset = command._offset
                if commandOffset == 0:
                    # stack pop
                    if len(prosodyStacks[cls]) == 0:
                        log.error("Stack underflow during fixProsodyCommands in Earcons and Speech Rules add-on.")
                        return sequence
                    prosodyOffsets[cls] = prosodyStacks[cls][-1]
                    del prosodyStacks[cls][-1]
                else:
                    prosodyStacks[cls].append(prosodyOffsets[cls])
                    prosodyOffsets[cls] += commandOffset
                command = copy.copy(command)
                # Let's make sure the offset doesn't go beyond (0, 100) interval - otherwise synths will ignore this command.
                ps = _findProsodySetting(cls)
                if ps is not None:
                    maxOffset = ps.max - ps.value
                    minOffset = ps.min - ps.value
                    effectiveOffset = max(
                        minOffset,
                        min(
                            maxOffset,
                            prosodyOffsets[cls]
                        )
                    )
                else:
                    effectiveOffset = prosodyOffsets[cls]
                command._offset = effectiveOffset
                command.isDefault = command._offset == 0
            result.append(command)
        return result
    except Exception as e:
        log.error(f"AudioThemes fixProsodyCommands error: {e}", exc_info=True)
        return sequence

def resetProsodies(sequence):
    prosodyStacks.clear()
    prosodyOffsets.clear()
    if not allProsodies or len(allProsodies) == 0:
        return sequence
    try:
        return [getProsodyClass(prosodyName)() for prosodyName in allProsodies] + sequence
    except Exception as e:
        log.error(f"AudioThemes resetProsodies error: {e}", exc_info=True)
        return sequence

original_processSpeechSymbol = None
_original_ext_speechEx = None
_original_ext_sayAll = None

@lru_cache(maxsize=256)
def _cached_native_symbol(locale, symbol, level):
    return originalProcessSpeechSymbols(locale, symbol, level)

def new_processSpeechSymbol(locale, symbol):
    if isPhoneticPunctuationEnabled():
        with _rules_lock:
            rule = characterRules.get(symbol, None) if characterRules else None
        if rule is not None:
            # Respect NVDA's symbol level setting.
            # Use the original (unpatched) processSpeechSymbols to check what NVDA
            # would do with this symbol at the current level.
            # If NVDA would keep it unchanged (i.e., below the level threshold)
            # or produce empty output, we should NOT fire the earcon either.
            currentLevel = _cached_speech_symbolLevel
            try:
                nativeOut = _cached_native_symbol(locale, symbol, currentLevel)
                if nativeOut == symbol or not nativeOut.strip():
                    return nativeOut
            except Exception as e:
                import logging
                logging.getLogger("audiothemes").error(f"AudioThemes Error: {e}", exc_info=True)
            speechBehavior = getattr(rule, 'speechBehavior', 0)
            customText = getattr(rule, 'customSpeechText', "")
            try:
                cmd = rule.getSpeechCommand()[0]
            except Exception:
                cmd = None
            
            if cmd is not None:
                try:
                    speech.speak([cmd])
                except Exception as e:
                    log.warning(f"new_processSpeechSymbol: failed to speak earcon for {symbol!r}: {e}")

            if speechBehavior == 1:
                return symbol
            elif speechBehavior == 2 and customText:
                return customText

            return ""
            
    return original_processSpeechSymbol(locale, symbol)

original_getIndentationSpeech = None
def new_getIndentationSpeech(indentation, formatConfig):
    """Retrieves the indentation speech sequence for a given string of indentation.
    @param indentation: The string of indentation.
    @param formatConfig: The configuration to use.
    """
    if not isPhoneticPunctuationEnabled():
        return original_getIndentationSpeech(indentation, formatConfig)
    try:
        speechIndentConfig = formatConfig.get("reportLineIndentation", ReportLineIndentation.OFF) in (
            ReportLineIndentation.SPEECH,
            ReportLineIndentation.SPEECH_AND_TONES,
        )
        toneIndentConfig = (
            formatConfig.get("reportLineIndentation", ReportLineIndentation.OFF)
            in (
                ReportLineIndentation.TONES,
                ReportLineIndentation.SPEECH_AND_TONES,
            )
            and getattr(getattr(speech.speech, '_speechState', None), 'speechMode', None) == speech.speech.SpeechMode.talk
        )
    except Exception:
        return original_getIndentationSpeech(indentation, formatConfig)
    indentSequence = []
    if not indentation:
        if toneIndentConfig:
            indentSequence.append(speech.commands.BeepCommand(speech.speech.IDT_BASE_FREQUENCY, speech.speech.getIndentToneDuration()))
        if speechIndentConfig:
            # mltony change
            otherRules = getattr(frenzy, 'otherRules', None) or {}
            noIndentList = otherRules.get(OtherRule.NO_INDENT, None)
            if noIndentList:
                noIndentRule = frenzy.getActiveRuleContext(noIndentList, *_utils_mod.getCurrentContext())
                if noIndentRule is None:
                    noIndentRule = noIndentList[0]
                cmd = noIndentRule.getSpeechCommand()[0]
                speechBehavior = getattr(noIndentRule, 'speechBehavior', 0)
                customText = getattr(noIndentRule, 'customSpeechText', "")
                
                if cmd:
                    indentSequence.append(cmd)
                if speechBehavior == 1:
                    indentSequence.append(_("no indent"))
                elif speechBehavior == 2 and customText:
                    indentSequence.append(customText)
            else:
                indentSequence.append(
                    # Translators: This is spoken when the given line has no indentation.
                    _("no indent"),
                )
        return indentSequence

    # The non-breaking space is semantically a space, so we replace it here.
    indentation = indentation.replace("\xa0", " ")
    res = []
    locale = languageHandler.getLanguage()
    quarterTones = 0
    for m in speech.speech.RE_INDENTATION_CONVERT.finditer(indentation):
        raw = m.group()
        symbol = characterProcessing.processSpeechSymbol(locale, raw[0])
        count = len(raw)
        if symbol == raw[0]:
            # There is no replacement for this character, so do nothing.
            res.append(raw)
        elif count == 1:
            res.append(symbol)
        else:
            # @mltony Changed here: supporting earcons for symbols
            #res.append("{count} {symbol}".format(count=count, symbol=symbol))
            res.append(f"{count}")
            res.append(symbol)
        quarterTones += count * 4 if raw[0] == "\t" else count

    speak = speechIndentConfig
    if toneIndentConfig:
        if quarterTones <= speech.speech.IDT_MAX_SPACES:
            pitch = speech.speech.IDT_BASE_FREQUENCY * 2 ** (quarterTones / 24.0)  # 24 quarter tones per octave.
            indentSequence.append(speech.commands.BeepCommand(pitch, speech.speech.getIndentToneDuration()))
        else:
            # we have more than 72 spaces (18 tabs), and must speak it since we don't want to hurt the users ears.
            speak = True
    if speak:
        indentSequence.extend(res)
    return indentSequence

original_getSelectionMessageSpeech = None
def new_getSelectionMessageSpeech(
	message,
	text,
):
    """
    When we replace say space character with an earcon, then "space selected" message doesn't work well.
    Fixing that behavior.
    """
    if isPhoneticPunctuationEnabled() and not isinstance(text, str):
        # Assuming that str is an earcon rather than string
        return [
            message.replace('%s', ''),
            text,
        ]
        
    return original_getSelectionMessageSpeech(message, text)
