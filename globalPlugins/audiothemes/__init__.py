# coding: utf-8


# This file is covered by the GNU General Public License.

"""
  Audio Themes Add-on — Unified Edition
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  This add-on creates a virtual audio display that plays sounds when focusing or navigating objects.
  It also enables the user to activate, install, remove, edit, create, and distribute audio theme packages.

  CREDITS & ACKNOWLEDGEMENTS:
  - Hassan AlBarshoumy: Main developer, maintainer, and unifier of this add-on (Advanced Audio Themes).
  - Ahmed Sami: Special thanks and acknowledgements.
  - Musharraf Omer: Original author of the "Audio Themes 3D" add-on.
  - Austin Hicks & Bryan Smart: Original creators of the "Unspoken" add-on.
  - Tony Malykh: Original author of "Earcons and Speech Rules", "Phonetic Punctuation", "BrowserNav", and "SentenceNav".
"""

from contextlib import suppress
from functools import lru_cache, wraps
import ctypes
import _ctypes
import time
import tones
import wx
import config
import globalPluginHandler
import keyboardHandler
from keyboardHandler import KeyboardInputGesture

import scriptHandler
from scriptHandler import script
import NVDAObjects
import gui
import speech
import controlTypes
import globalCommands
import eventHandler
import ui
import textInfos
import logHandler
log = logHandler.log

from .handler import AudioThemesHandler, SpecialProps, role_int_to_name, showPendingConflicts, STATE_OFFSET
from .settings import AudioThemesSettingsPanel
from .studio import AudioThemesStudioStartupDialog
from .update_checker import check_for_updates_auto

from . import phoneticPunctuation as pp
from .phoneticPunctuation import is_emoji_suppress_role_flag_set
from . import utils
from .utils import is_sound_suppressed
from . import frenzy
from .clipboard import ClipboardManager

# Import the SentenceNav engine (Alt+Arrow sentence/phrase navigation)
from .sentenceNavEngine import SentenceNavMixin, initSentenceNavConfiguration

 # Import the BrowserNav engine (NVDA+Alt+Arrow browser navigation, QuickJump, etc.)
from .browserNavEngine import BrowserNavMixin

_cached_desktop_location = None
_cached_desktop_location_time = 0.0

_HEADING_LEVEL_MAP = {
    7: SpecialProps.heading7,
    8: SpecialProps.heading8,
    9: SpecialProps.heading9,
}

import api
import winUser

import addonHandler
try:
    addonHandler.initTranslation()
except AttributeError:
    pass

utils.initConfiguration()
try:
    pp.reloadRules()
except Exception:
    log.error("AudioThemes: Failed to reload rules at startup", exc_info=True)

from . import quicknav

# Initialize SentenceNav config section
initSentenceNavConfiguration()

from .navLayer import NavLayerMixin

@lru_cache(maxsize=256)
def _text_contains_emoji(text):
    """Check if text contains any emoji characters."""
    if not text:
        return False
    if text.isascii():
        return False
    i = 0
    n = len(text)
    while i < n:
        cp = ord(text[i])
        if 0xD800 <= cp <= 0xDBFF and i + 1 < n:
            low = ord(text[i + 1])
            if 0xDC00 <= low <= 0xDFFF:
                cp = 0x10000 + (cp - 0xD800) * 0x400 + (low - 0xDC00)
                i += 1
        i += 1
        if cp > 0xFFFF:
            return True
        if 0x2600 <= cp <= 0x27BF:
            return True
        if 0x2B50 == cp or 0x2934 == cp or 0x2935 == cp:
            return True
        if 0x2B05 <= cp <= 0x2B07:
            return True
        if 0x2B1B <= cp <= 0x2B1C:
            return True
        if 0x3030 == cp or 0x303D == cp or 0x3297 == cp or 0x3299 == cp:
            return True
        if 0xFE00 <= cp <= 0xFE0F:
            return True
        if 0x1F000 <= cp <= 0x1FFFF:
            return True
    return False

import weakref
_snapshot_cache = weakref.WeakKeyDictionary()

class GlobalPlugin(SentenceNavMixin, BrowserNavMixin, NavLayerMixin, globalPluginHandler.GlobalPlugin):

    scriptCategory = "Advanced Audio Themes"

    # -- COM-safety: extract everything on the main thread ---------------
    @staticmethod
    def _snapshot_obj(obj, extra_snd=None, foreground_app=None):
        """Build a plain dict from a live NVDAObject."""
        try:
            cached = _snapshot_cache.get(obj)
            if cached is not None and cached.get("_extra_snd") == extra_snd and cached.get("_fg") == foreground_app:
                return cached.copy()
        except Exception:
            pass
        info = {}
        try:
            info["role"] = obj.role
        except Exception:
            info["role"] = 0
        # Map HEADING roles with level 7-9 to SpecialProps heading7/8/9
        if info.get("role", 0) == controlTypes.Role.HEADING:
            heading_level = None
            try:
                val = obj.value
                if val is not None:
                    heading_level = int(val)
            except Exception:
                pass
            if heading_level is None or heading_level < 1 or heading_level > 9:
                try:
                    val = obj.description
                    if val and val.isdigit():
                        heading_level = int(val)
                except Exception:
                    pass
            if heading_level is not None and heading_level >= 7:
                h_key = _HEADING_LEVEL_MAP.get(heading_level)
                if h_key is not None:
                    info["role"] = h_key.value
        try:
            info["states"] = frozenset(obj.states)
        except Exception:
            info["states"] = frozenset()
        try:
            info["name"] = obj.name or ""
        except Exception:
            info["name"] = ""
        try:
            info["location"] = tuple(obj.location) if obj.location else None
        except Exception:
            info["location"] = None
        try:
            info["windowClassName"] = obj.windowClassName or ""
        except Exception:
            info["windowClassName"] = ""
        handler = GlobalPlugin._instance_handler if hasattr(GlobalPlugin, '_instance_handler') else None
        fl_cfg = getattr(handler, '_cached_config', None) or {}
        # --- getOrder data (parent / previous / next roles) ---
        # Now collected for ALL roles to support universal first/last detection.
        if fl_cfg.get("enable_audio_themes", True):
            try:
                info["parent_role"] = obj.parent.role if obj.parent else None
            except Exception:
                info["parent_role"] = None
            try:
                info["previous_role"] = obj.previous.role if obj.previous else None
            except Exception:
                info["previous_role"] = None
            try:
                info["next_role"] = obj.next.role if obj.next else None
            except Exception:
                info["next_role"] = None
            # Multi-hop traversal for same-role sibling detection
            # Capped at 1 level to avoid expensive COM tree walks (was 3, caused 40s freezes)
            fl_mode = fl_cfg.get("fl_detection_mode", "smart")
            if fl_mode in ("strict", "smart"):
                _role = info.get("role")
                try:
                    p = obj.previous
                    if p is not None and p.role == _role:
                        info["prev_same_role"] = p.role
                    else:
                        info["prev_same_role"] = None
                except Exception:
                    info["prev_same_role"] = None
                try:
                    n = obj.next
                    if n is not None and n.role == _role:
                        info["next_same_role"] = n.role
                    else:
                        info["next_same_role"] = None
                except Exception:
                    info["next_same_role"] = None
            else:
                info["prev_same_role"] = None
                info["next_same_role"] = None
        else:
            info["parent_role"] = None
            info["previous_role"] = None
            info["next_role"] = None
            info["prev_same_role"] = None
            info["next_same_role"] = None
        # Carry forward a custom snd override (e.g. SpecialProps.notify).
        info["snd"] = extra_snd
        # Desktop dimensions for 3D audio (avoids COM call on worker thread).
        global _cached_desktop_location, _cached_desktop_location_time
        now = time.monotonic()
        if _cached_desktop_location is None or (now - _cached_desktop_location_time) > 30.0:
            try:
                desktop = NVDAObjects.api.getDesktopObject()
                _cached_desktop_location = tuple(desktop.location) if desktop and desktop.location else None
                _cached_desktop_location_time = now
            except Exception:
                _cached_desktop_location = None
                _cached_desktop_location_time = now

        info["desktop_location"] = _cached_desktop_location
        if foreground_app is None:
            try:
                appName, _, _ = utils.getCurrentContext()
                info["foreground_app"] = appName
            except Exception:
                info["foreground_app"] = None
        else:
            info["foreground_app"] = foreground_app
        try:
            info["_extra_snd"] = extra_snd
            info["_fg"] = foreground_app
            _snapshot_cache[obj] = info.copy()
        except Exception:
            pass
        return info

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        log.info("Starting Advanced Audio Themes version 9.37")
        utils.threadPool.restart()
        self.handler = AudioThemesHandler()
        GlobalPlugin._instance_handler = self.handler
        from .utils import _set_handler_ref
        _set_handler_ref(self.handler)
        
        # Patch Quick Nav Interceptor
        try:
            self.quicknav_interceptor = quicknav.BrowseModeQuickNavInterceptor(self.handler)
            self.quicknav_interceptor.patch()
        except Exception:
            log.error("AudioThemes: Failed to init quicknav interceptor", exc_info=True)
        
        try:
            gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(
                AudioThemesSettingsPanel
            )
        except Exception:
            log.error("AudioThemes: Failed to add settings panel", exc_info=True)
        self._previous_mouse_object = None
        self._last_navigator_object = None
        self._last_play_time = 0  # debounce: monotonic timestamp of last dispatch
        self._last_focused_obj = None   # for gainFocus / becomeNavigator dedup
        self._last_focus_time = 0.0
        self._last_progress_times = {}  # debounce: {obj_id: timestamp} for progress bars
        self._audio_beacon_location = None
        self._audio_beacon_desktop = None
        self._last_focus_is_editable = False
        # Defer menu item creation — the main window may not be ready yet
        wx.CallAfter(self._add_tray_menu_items)

        # Auto-check for updates (runs in background thread, respects config)
        # Delayed 15 seconds to let the add-on fully initialize first
        wx.CallLater(15000, check_for_updates_auto)

        # Browse-mode navigation timer: polls the navigator object every 180ms.
        # This is the ONLY way to detect arrow-key movement inside a virtual
        # buffer (browse mode), because NVDA does not fire event_gainFocus or
        # event_becomeNavigatorObject during virtual-buffer caret moves.
        self._navigation_timer = wx.Timer()
        self._navigation_timer.Bind(wx.EVT_TIMER, self._onNavigationTimer)
        self._navigation_timer.Start(250)

        # Phonetic Punctuation Initialization
        try:
            self.injectMonkeyPatches()
        except Exception:
            log.error("AudioThemes: Failed to install speech patches", exc_info=True)
        
        self._keyboard_hooked = False
        try:
            self._hook_keyboard()
        except Exception:
            log.error("AudioThemes: Failed to hook keyboard", exc_info=True)
        
        # Restore caretMovementScriptHelper hook for arrow keys
        self.orig_caretMovementScriptHelper = None
        try:
            import speech
            if hasattr(speech, "_caretMovementScriptHelper"):
                self.orig_caretMovementScriptHelper = speech._caretMovementScriptHelper
                speech._caretMovementScriptHelper = self._hook_caretMovementScriptHelper
        except Exception as e:
            log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
        # ── BrowserNav initialization ──
        # Wire up all BrowserNav monkey patches, browse-mode keystrokes,
        # QuickJump system, and URL tracking.
        try:
            self.initBrowserNav()
        except Exception:
            log.exception("Failed to initialize BrowserNav engine")

        self.toggling = False
        self._audioThemesLayerGestures = {
            "kb:F1": "openHelp",
            "kb:h": "audioThemesHelp",
            "kb:t": "toggleAudioThemes",
            "kb:p": "togglePp",
            "kb:n": "nextAudioTheme",
            "kb:b": "previousAudioTheme",
            "kb:upArrow": "increaseAudioThemesVolume",
            "kb:downArrow": "decreaseAudioThemesVolume",
            "kb:s": "toggleStateVerbosity",
            "kb:c": "speakHeadingLevel",
            "kb:o": "rotateSpeechOrder",
            "kb:y": "cycleAudioThemes",
            "kb:i": "cycleTypingSounds",
            "kb:u": "toggleTypingSounds",
            "kb:a": "toggleAudioBeacon",
            "kb:r": "audioSonar",
            "kb:w": "speakObject",
            "kb:d": "toggleAudioDucking",
            "kb:e": "toggleEmojiSounds",
            "kb:f": "toggleAppProfiles",
            "kb:g": "toggle3DAudio",
            "kb:j": "speakCurrentURL",
            "kb:k": "toggleClipboard",
            "kb:l": "toggleSystemStatus",
            "kb:m": "openStudio",
            "kb:q": "toggleSpeakRoles",
            "kb:v": "openSettings",
            "kb:x": "toggleOutputMode",
            "kb:z": "reportSystemStatus",
        }
        self._helpDialog = None
        self._helpPending = False
        self._studioDialog = None
        self._clipboard_mgr = ClipboardManager(self.handler)
        self._rebindInstanceGestures()
        wx.CallAfter(showPendingConflicts)

    def _on_toggle_from_menu(self, event):
        state = event.IsChecked()
        config.conf["audiothemes"]["enable_audio_themes"] = state
        self.handler.configure()
        if hasattr(self, '_tray_toggle_item') and self._tray_toggle_item:
            self._tray_toggle_item.Check(state)
        if state:
            ui.message(_("Audio themes enabled"))
        else:
            import ui
            ui.message(_("Audio themes disabled"))

    def _add_tray_menu_items(self):
        try:
            import gui
            import wx
            tray = gui.mainFrame.sysTrayIcon
            if not tray or not tray.menu:
                wx.CallLater(500, self._add_tray_menu_items)
                return
            menu = tray.menu
            self._tray_studio_item = menu.Append(
                wx.ID_ANY,
                _("&Audio Themes Studio"),
                _("Open the Audio Theme Studio to create and edit themes")
            )
            tray.Bind(wx.EVT_MENU, self.on_studio_item_clicked, self._tray_studio_item)
            self._tray_toggle_item = menu.AppendCheckItem(
                wx.ID_ANY,
                _("Enable Audio Themes"),
                _("Toggle audio themes on or off")
            )
            self._tray_toggle_item.Check(config.conf["audiothemes"]["enable_audio_themes"])
            tray.Bind(wx.EVT_MENU, self._on_toggle_from_menu, self._tray_toggle_item)
        except Exception:
            import logHandler
            logHandler.log.error("AudioThemes: Failed to add tray menu items", exc_info=True)

    def _remove_tray_menu_items(self):
        try:
            import gui
            tray = gui.mainFrame.sysTrayIcon
            if tray and tray.menu:
                for attr in ("_tray_studio_item", "_tray_toggle_item"):
                    item = getattr(self, attr, None)
                    if item:
                        tray.menu.Remove(item)
                        setattr(self, attr, None)
        except Exception:
            pass

    def _hook_caretMovementScriptHelper(self, extraDetail, unit, direction, posConstant=textInfos.POSITION_CARET, *args, **kwargs):
        if self.orig_caretMovementScriptHelper:
            self.orig_caretMovementScriptHelper(extraDetail, unit, direction, posConstant, *args, **kwargs)
        try:
            current_nav = api.getNavigatorObject()
            if current_nav and getattr(current_nav, 'treeInterceptor', None) and not current_nav.treeInterceptor.passThrough:
                if current_nav != getattr(self, "_last_navigator_object", None):
                    self._last_navigator_object = current_nav
                    self._last_play_time = time.monotonic()
                    obj_info = self._snapshot_obj(current_nav)
                    utils.threadPool.add_task(self.playObject, obj_info)
                    utils.threadPool.add_task(self._play_beacon_sonar, obj_info)
        except Exception as e:
            log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
    def _rebindInstanceGestures(self):
        # ── SentenceNav & TextNav Initialization ──
        # Bind gestures explicitly to ensure NVDA's ScriptableObject metaclass 
        # registers them even when inherited from mixins.
        self.bindGesture("kb:Alt+DownArrow", "nextSentence")
        self.bindGesture("kb:Alt+UpArrow", "previousSentence")
        self.bindGesture("kb:NVDA+Alt+S", "currentSentence")
        self.bindGesture("kb:Alt+Windows+DownArrow", "nextPhrase")
        self.bindGesture("kb:Alt+Windows+UpArrow", "previousPhrase")
        self.bindGesture("kb:Alt+Shift+DownArrow", "nextText")
        self.bindGesture("kb:Alt+Shift+UpArrow", "previousText")
        
        # Navigation Layer
        self.bindGesture("kb:NVDA+windows+n", "navigationLayer")

    @script(description=_("Audio themes command layer. Press this then a command key (e.g. h for help)."), gestures=['kb:NVDA+shift+a'])
    def script_audioThemesLayer(self, gesture):
        if getattr(self, "toggling", False):
            self.finish()
            return
        self.bindGestures(self._audioThemesLayerGestures)
        self.toggling = True
        from .utils import is_sound_suppressed
        if not is_sound_suppressed("ui_beeps"):
            try:
                from . import frenzy
                df = frenzy.get_ducking_factor("ui_beeps")
                if df < 1.0:
                    tones.beep(200, 40, left=int(25*df), right=int(25*df))
                else:
                    tones.beep(200, 40, left=25, right=25)
            except Exception:
                tones.beep(200, 40)
        ui.message(_("Command layer. Press h for commands list, F1 for help."))

    def getScript(self, gesture):
        if not getattr(self, "toggling", False) or not isinstance(gesture, KeyboardInputGesture):
            return super().getScript(gesture)
        
        script = super().getScript(gesture)
        if not script:
            script = self._finally(self.script_error, self.finish)
            return self._finally(script, self.finish)
        
        if hasattr(script, "noFinish") and script.noFinish:
            return self._finally(script, self.noFinish)
        return self._finally(script, self.finish)

    def _finally(self, func, final):
        @wraps(func)
        def new(*args, **kwargs):
            try:
                func(*args, **kwargs)
            finally:
                final()
        return new

    def finish(self):
        self.toggling = False
        for ident in self._audioThemesLayerGestures:
            try:
                self.removeGestureBinding(ident)
            except (LookupError, ValueError):
                pass

    def noFinish(self):
        pass

    def script_error(self, gesture):
        from .utils import is_sound_suppressed
        if is_sound_suppressed("ui_beeps"):
            return
        try:
            from . import frenzy
            df = frenzy.get_ducking_factor("ui_beeps")
            if df < 1.0:
                tones.beep(420, 40, left=int(25*df), right=int(25*df))
            else:
                tones.beep(420, 40, left=25, right=25)
        except Exception:
            tones.beep(420, 40)

    @script(description=_("Opens the add-on help file for your language."), gestures=[])
    def script_openHelp(self, gesture):
        import os
        import languageHandler
        import addonHandler
        lang = languageHandler.getLanguage()
        addonDir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        docPath = os.path.join(addonDir, "doc", lang, "readme.html")
        if not os.path.isfile(docPath):
            docPath = os.path.join(addonDir, "doc", "en", "readme.html")
        if os.path.isfile(docPath):
            os.startfile(docPath)
        else:
            ui.message(_("Help file not found."))

    @script(description=_("Shows audio themes commands help."), gestures=[])
    def script_audioThemesHelp(self, gesture):
        if self._helpDialog is not None:
            try:
                self._helpDialog.Raise()
                return
            except Exception:
                self._helpDialog = None
        if self._helpPending:
            try:
                self._helpDialog.Raise()
                return
            except Exception:
                self._helpDialog = None
        if self._helpPending:
            return
        self._helpPending = True
        import wx
        from gui import mainFrame
        
        def runDialog():
            dlg = wx.SingleChoiceDialog(
                mainFrame,
                _("Select an audio themes command to execute:"),
                _("Audio Themes Commands"),
                [
                    "F1: " + _("Open Help File"),
                    "t: " + _("Toggle Audio Themes"),
                    "p: " + _("Toggle Earcons and Speech Rules"),
                    "n: " + _("Next Audio Theme"),
                    "b: " + _("Previous Audio Theme"),
                    "upArrow: " + _("Increase Audio Themes Volume"),
                    "downArrow: " + _("Decrease Audio Themes Volume"),
                    "s: " + _("Toggle state verbosity"),
                    "c: " + _("Speak current heading level"),
                    "o: " + _("Rotate global speech order"),
                    "y: " + _("Cycle Audio Themes"),
                    "i: " + _("Cycle Typing Sounds"),
                    "u: " + _("Toggle Typing Sounds"),
                    "a: " + _("Toggle Audio Beacon"),
                    "r: " + _("Audio Sonar"),
                    "w: " + _("Speak Object 3D Coordinates") + " " + _("(Plays 3D sound even if 3D mode is disabled)"),
                    "d: " + _("Toggle Audio Ducking"),
                    "e: " + _("Toggle Emoji Sounds"),
                    "f: " + _("Toggle App Profiles"),
                    "g: " + _("Toggle 3D Audio"),
                    "j: " + _("Speak Current URL"),
                    "k: " + _("Toggle Clipboard Announcements"),
                    "l: " + _("Toggle System Status Sounds"),
                    "m: " + _("Open Audio Themes Studio"),
                    "q: " + _("Toggle Speak Roles"),
                    "v: " + _("Open Audio Themes Settings"),
                    "x: " + _("Toggle Output Mode (Stereo/Mono)"),
                    "z: " + _("Report System Power Status"),
                    "NVDA+windows+n: " + _("Navigation Layer (arrows, s=spell, r=read all, c=copy)"),
                ]
            )
            self._helpDialog = dlg
            if dlg.ShowModal() == wx.ID_OK:
                sel = dlg.GetSelection()
                cmds = [
                    self.script_openHelp,
                    self.script_toggleAudioThemes,
                    self.script_togglePp,
                    self.script_nextAudioTheme,
                    self.script_previousAudioTheme,
                    self.script_increaseAudioThemesVolume,
                    self.script_decreaseAudioThemesVolume,
                    self.script_toggleStateVerbosity,
                    self.script_speakHeadingLevel,
                    self.script_rotateSpeechOrder,
                    self.script_cycleAudioThemes,
                    self.script_cycleTypingSounds,
                    self.script_toggleTypingSounds,
                    self.script_toggleAudioBeacon,
                    self.script_audioSonar,
                    self.script_speakObject,
                    self.script_toggleAudioDucking,
                    self.script_toggleEmojiSounds,
                    self.script_toggleAppProfiles,
                    self.script_toggle3DAudio,
                    self.script_speakCurrentURL,
                    self.script_toggleClipboard,
                    self.script_toggleSystemStatus,
                    self.script_openStudio,
                    self.script_toggleSpeakRoles,
                    self.script_openSettings,
                    self.script_toggleOutputMode,
                    self.script_reportSystemStatus,
                    self.script_navigationLayer,
                ]
                if 0 <= sel < len(cmds):
                    try:
                        cmds[sel](None)
                    except Exception:
                        pass
            dlg.Destroy()
            self._helpDialog = None
            self._helpPending = False
        wx.CallAfter(runDialog)

    def terminate(self):
        with suppress(Exception):
            gui.settingsDialogs.NVDASettingsDialog.categoryClasses.remove(
                AudioThemesSettingsPanel
            )
        with suppress(Exception):
            self._remove_tray_menu_items()
        with suppress(Exception):
            self.restoreMonkeyPatches()
        with suppress(Exception):
            self._unhook_keyboard()
        if self.orig_caretMovementScriptHelper:
            with suppress(Exception):
                import speech
                if hasattr(speech, "_caretMovementScriptHelper"):
                    speech._caretMovementScriptHelper = self.orig_caretMovementScriptHelper
        with suppress(Exception):
            self.quicknav_interceptor.terminate()
        with suppress(Exception):
            self.handler.close()
        with suppress(Exception):
            self._navigation_timer.Stop()
        with suppress(Exception):
            from .sentenceNavEngine import _unregister_sentence_nav_hooks
            _unregister_sentence_nav_hooks()
        with suppress(Exception):
            utils.threadPool.shutdown(wait=False)
        # ── BrowserNav termination ──
        with suppress(Exception):
            self.terminateBrowserNav()
        # Ensure mixin classes (SentenceNavMixin, BrowserNavMixin) clean up properly.
        with suppress(Exception):
            super().terminate()

    def injectMonkeyPatches(self):
        pp.injectMonkeyPatches()

    def restoreMonkeyPatches(self):
        pp.restoreMonkeyPatches()

    # Browse-mode navigation: timer-based polling of navigator object.
    def _onNavigationTimer(self, event):
        """Check if the navigator object changed (e.g. arrow keys in browse mode)."""
        try:
            current_nav = api.getNavigatorObject()
            if current_nav and current_nav.treeInterceptor and not current_nav.treeInterceptor.passThrough:
                if current_nav != getattr(self, "_last_navigator_object", None):
                    self._last_navigator_object = current_nav
                    # Debounce: skip if last dispatch was < 80ms ago.
                    now = time.monotonic()
                    if now - getattr(self, "_last_play_time", 0) < 0.08:
                        return
                    if getattr(self.handler, "last_quicknav_time", 0) and now - self.handler.last_quicknav_time < 0.3:
                        return
                    self._last_play_time = now
                    obj_info = self._snapshot_obj(current_nav)
                    utils.threadPool.add_task(self.playObject, obj_info)
                    utils.threadPool.add_task(self._play_beacon_sonar, obj_info)
        except Exception as e:
            log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
    def on_studio_item_clicked(self, event):
        if self._studioDialog is not None:
            try:
                self._studioDialog.Raise()
                return
            except Exception:
                self._studioDialog = None
        with AudioThemesStudioStartupDialog(self, _("Audio Themes Studio")) as dlg:
            self._studioDialog = dlg
            dlg.Raise()
            dlg.ShowModal()
        self._studioDialog = None

    def on_settings_item_clicked(self, event):
        import wx
        def do_open():
            try:
                if hasattr(gui.mainFrame, "popupSettingsDialog"):
                    gui.mainFrame.popupSettingsDialog(AudioThemesSettingsPanel)
                else:
                    gui.mainFrame._popupSettingsDialog(AudioThemesSettingsPanel)
            except Exception as e:
                log.error(f"Failed to open Audio Themes settings: {e}", exc_info=True)
                ui.message(_("Failed to open settings. Please open through NVDA Preferences."))
        wx.CallAfter(do_open)

    def on_toggle_item_clicked(self, event):
        enabled = not config.conf["audiothemes"]["enable_audio_themes"]
        config.conf["audiothemes"]["enable_audio_themes"] = enabled
        self.handler.configure()
        if enabled:
            ui.message(_("Audio themes enabled"))
        else:
            ui.message(_("Audio themes disabled"))

    @script(description=_("Report the object under the cursor with full 3D audio coordinates.") + " " + _("(Plays 3D sound even if 3D mode is disabled)"), gestures=['kb:nvda+tab'])
    def script_speakObject(self, gesture):
        if scriptHandler.getLastScriptRepeatCount() == 0:
            obj = api.getFocusObject()
            obj_info = self._snapshot_obj(obj)
            obj_info["force_3d"] = True
            self.playObject(obj_info)
        globalCommands.commands.script_reportCurrentFocus(gesture)

    def event_gainFocus(self, obj, nextHandler):
        """
        Snapshot all COM properties on the main thread, then dispatch the
        plain dict to a background worker.  This eliminates the COMError
        (-2147417842, RPC_E_WRONG_THREAD) that occurred when playObject()
        accessed obj.states / obj.role from a worker thread.
        """
        self._last_focused_obj = obj
        self._last_focus_time = time.monotonic()
        self._last_play_time = self._last_focus_time
        self._last_focus_is_editable = self._is_editable(obj)
        # Also sync navigator tracking so the 180ms timer doesn't double-fire
        try:
            self._last_navigator_object = api.getNavigatorObject()
        except Exception:
            self._last_navigator_object = obj
        # Cache foreground app name on handler (avoids COM calls in keyboard hook)
        try:
            app_name = obj.appModule.appName if obj.appModule else None
            self.handler._current_app_name = app_name
            if log.isEnabledFor(log.DEBUG):
                log.debug(f"event_gainFocus app={app_name} active_theme={self.handler.active_theme.folder if self.handler.active_theme else None}")
        except Exception:
            self.handler._current_app_name = None
        try:
            nextHandler()
        except StopIteration:
            raise
        except Exception as e:
            log.debugWarning(f"event_gainFocus nextHandler: {e}")
        try:
            if not self.handler._cached_config.get("enable_audio_themes", True):
                return
            obj_info = self._snapshot_obj(obj, foreground_app=self.handler._current_app_name)
            utils.threadPool.add_task(self.playObject, obj_info)
            utils.threadPool.add_task(self._play_beacon_sonar, obj_info)
        except Exception as e:
            log.debugWarning(f"event_gainFocus snapshot/dispatch: {e}")

    def _play_beacon_sonar(self, obj_info):
        if not self._audio_beacon_location or not self.handler.active_theme:
            return
        try:
            loc = obj_info.get("location")
            if not loc: return

            b_loc = self._audio_beacon_location

            b_x = b_loc[0] + (b_loc[2] / 2.0)
            b_y = b_loc[1] + (b_loc[3] / 2.0)

            c_x = loc[0] + (loc[2] / 2.0)
            c_y = loc[1] + (loc[3] / 2.0)

            dx = c_x - b_x
            dy = c_y - b_y

            desktop = self._audio_beacon_desktop
            if not desktop:
                return
            if desktop[2] == 0 or desktop[3] == 0:
                return

            nx = dx / float(desktop[2])
            ny = dy / float(desktop[3])

            # Try theme beacon sound first
            if self.handler.play_theme_sound("beacon", angle_x=nx * 90.0, angle_y=ny * 50.0):
                return

            # Fallback: generate tone when theme has no beacon sound
            if is_sound_suppressed("ui_beeps"):
                return

            distance = (dx * dx + dy * dy) ** 0.5
            max_dist = (desktop[2] * desktop[2] + desktop[3] * desktop[3]) ** 0.5
            if max_dist == 0:
                closeness = 1.0
            else:
                closeness = max(0.05, 1.0 - distance / max_dist)

            pitch = int(300 + closeness * 900)
            volume = int(25 * closeness)
            pan = max(-1.0, min(1.0, nx * 2.0))
            left = int(volume * (1.0 - max(0.0, pan)))
            right = int(volume * (1.0 - max(0.0, -pan)))

            try:
                df = frenzy.get_ducking_factor("ui_beeps", self.handler._cached_config)
                if df < 1.0:
                    tones.beep(pitch, 30, left=int(left * df), right=int(right * df))
                else:
                    tones.beep(pitch, 30, left=left, right=right)
            except Exception:
                tones.beep(pitch, 30, left=left, right=right)
        except Exception as e:
            log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
    def event_becomeNavigatorObject(self, obj, nextHandler, isFocus=False):
        """
        Snapshot on main thread, dispatch dict to worker.
        isFocus=True means gainFocus already dispatched -- skip double-play.
        Also skip if this is the same object as the last gainFocus within 300ms
        (some browsers fire both events for the same element on Tab).
        """
        # Cache app name on handler
        try:
            self.handler._current_app_name = obj.appModule.appName if obj.appModule else None
            self.handler._current_window_title = getattr(obj, 'name', None)
        except Exception:
            self.handler._current_app_name = None
            self.handler._current_window_title = None
        self.handler._current_url = None
        if isFocus:
            try:
                nextHandler()
            except StopIteration:
                raise
            except Exception as e:
                log.debugWarning(f"event_becomeNavigatorObject nextHandler (isFocus): {e}")
            return
        # Dedup: skip if gainFocus just fired for this very object
        if obj is self._last_focused_obj and (time.monotonic() - self._last_focus_time) < 0.3:
            try:
                nextHandler()
            except StopIteration:
                raise
            except Exception as e:
                log.debugWarning(f"event_becomeNavigatorObject nextHandler (dedup): {e}")
            return
        try:
            nextHandler()
        except StopIteration:
            raise
        except Exception as e:
            log.debugWarning(f"event_becomeNavigatorObject nextHandler: {e}")
        self._last_play_time = time.monotonic()
        try:
            self._last_navigator_object = api.getNavigatorObject()
        except Exception:
            self._last_navigator_object = obj
        try:
            obj_info = self._snapshot_obj(obj, foreground_app=self.handler._current_app_name)
            utils.threadPool.add_task(self.playObject, obj_info)
            utils.threadPool.add_task(self._play_beacon_sonar, obj_info)
        except Exception as e:
            log.debugWarning(f"event_becomeNavigatorObject snapshot/dispatch: {e}")

    def event_valueChange(self, obj, nextHandler):
        try:
            if obj.role == controlTypes.Role.PROGRESSBAR:
                now = time.monotonic()
                obj_id = id(obj)
                last_t = self._last_progress_times.get(obj_id, 0)
                if now - last_t < 0.5:
                    try:
                        nextHandler()
                    except StopIteration:
                        raise
                    except Exception:
                        pass
                    return
                self._last_progress_times[obj_id] = now
                if len(self._last_progress_times) > 64:
                    self._last_progress_times.clear()
                cfg = self.handler._cached_config
                if cfg.get("enable_audio_themes", True) and self.handler.active_theme:
                    val = obj.value
                    if val is not None:
                        try:
                            val_float = float(val.replace('%', '') if isinstance(val, str) else val)
                            min_val = float(getattr(obj, "minimum", 0) or 0)
                            max_val = float(getattr(obj, "maximum", 100) or 100)
                            if max_val > min_val:
                                percent = (val_float - min_val) / (max_val - min_val)
                            else:
                                percent = val_float / 100.0
                            percent = max(0.0, min(1.0, percent))

                            pan_mode = cfg.get("progress_pan_mode", "progress")
                            pan_range = cfg.get("progress_pan_range", 180)
                            pitch_shift = cfg.get("progress_pitch_shift", True)

                            obj_info = self._snapshot_obj(obj)

                            if pan_mode == "screen":
                                loc = obj_info.get("location")
                                desktop = obj_info.get("desktop_location")
                                if loc and desktop and desktop[2] > 0:
                                    bar_left = loc[0]
                                    bar_width = loc[2]
                                    sound_x = bar_left + percent * bar_width
                                    angle_x = ((sound_x - desktop[2] / 2.0) / desktop[2]) * 180.0
                                    angle_x = max(-90.0, min(90.0, angle_x))
                                else:
                                    angle_x = -(pan_range / 2.0) + (percent * pan_range)
                            else:
                                angle_x = -(pan_range / 2.0) + (percent * pan_range)

                            obj_info['progress_angle'] = angle_x
                            obj_info['progress_percent'] = percent
                            obj_info['progress_pitch_shift'] = pitch_shift
                            utils.threadPool.add_task(self.playObject, obj_info)
                        except Exception as e:
                            log.debug(f"AudioThemes event_valueChange progress: {e}")
        except Exception as e:
            log.debug(f"AudioThemes event_valueChange: {e}")
        try:
            nextHandler()
        except StopIteration:
            raise
        except Exception as e:
            log.debugWarning(f"event_valueChange nextHandler: {e}")
    def _is_editable(self, obj):
        try:
            controls = (controlTypes.Role.EDITABLETEXT, controlTypes.Role.TERMINAL, controlTypes.Role.RICHEDIT)
            return (obj.role in controls or controlTypes.State.EDITABLE in obj.states) and controlTypes.State.READONLY not in obj.states
        except (_ctypes.COMError, Exception):
            return False

    def _hook_keyboard(self):
        if self._keyboard_hooked:
            return
        import keyboardHandler
        import winInputHook
        self._original_keyDownEvent = keyboardHandler.internal_keyDownEvent
        keyboardHandler.internal_keyDownEvent = self._new_keyDownEvent
        try:
            winInputHook.setCallbacks(keyDown=self._new_keyDownEvent, keyUp=keyboardHandler.internal_keyUpEvent)
            log.info("AUDIO_THEMES: keyboard hook registered with winInputHook.setCallbacks")
        except Exception as e:
            log.error(f"AUDIO_THEMES: Failed to set winInputHook callbacks: {e}", exc_info=True)
        self._keyboard_hooked = True

    def _unhook_keyboard(self):
        if not self._keyboard_hooked:
            return
        import keyboardHandler
        import winInputHook
        keyboardHandler.internal_keyDownEvent = self._original_keyDownEvent
        try:
            winInputHook.setCallbacks(keyDown=keyboardHandler.internal_keyDownEvent, keyUp=keyboardHandler.internal_keyUpEvent)
            log.info("AUDIO_THEMES: keyboard hook restored")
        except Exception as e:
            log.error(f"AUDIO_THEMES: Failed to restore winInputHook callbacks: {e}", exc_info=True)
        self._keyboard_hooked = False

    def _new_keyDownEvent(self, vkCode, scanCode, extended, injected):
        # Only record last vkCode/extended if it is not injected, and not a modifier key
        if not injected and vkCode not in (16, 17, 18, 20, 91, 92, 144, 160, 161, 162, 163, 164, 165):
            self._last_vkCode = vkCode
            self._last_extended = extended
        # Play advanced typing sounds for non-characters
        try:
            cfg = self.handler._cached_config if hasattr(self, 'handler') else {}
            if not injected and cfg.get("typing_sounds", True):
                # Check edit only
                play = True
                if cfg.get("typing_sounds_edit_only", False):
                    play = getattr(self, "_last_focus_is_editable", True)
                
                if play:
                    # Specific keys
                    if vkCode in (0x0D, 0x08): # Enter, Backspace
                        self.handler.play_typing_sound(vkCode=vkCode, extended=extended)
                    elif vkCode in (0x10, 0x11, 0x12, 0x5B, 0x5C): # Shift, Ctrl, Alt, Win
                        self.handler.play_typing_sound(vkCode=vkCode, extended=extended)
                    # Note: printable characters will still be caught by event_typedCharacter
                    # We don't catch them here to avoid double playing, except if we want to bypass event_typedCharacter completely.
                    # Actually event_typedCharacter is safer for letters.
        except Exception as e:
            log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
        # Clipboard shortcut detection
        if not injected:
            try:
                cfg2 = self.handler._cached_config if hasattr(self, 'handler') else {}
                if cfg2.get("clipboard_enabled", True):
                    if winUser.getAsyncKeyState(winUser.VK_CONTROL) & 0x8000:
                        shift = winUser.getAsyncKeyState(winUser.VK_SHIFT) & 0x8000
                        if vkCode == 0x43:  # C
                            self._clipboard_mgr.announce("copy")
                        elif vkCode == 0x58:  # X
                            self._clipboard_mgr.announce("cut")
                        elif vkCode == 0x56:  # V
                            self._clipboard_mgr.announce("pasteplain" if shift else "paste")
                        elif vkCode == 0x41:  # A
                            self._clipboard_mgr.announce("selectall")
                        elif vkCode == 0x5A:  # Z
                            self._clipboard_mgr.announce("redo2" if shift else "undo")
                        elif vkCode == 0x59:  # Y
                            self._clipboard_mgr.announce("redo")
            except Exception:
                pass
        if self._original_keyDownEvent:
            return self._original_keyDownEvent(vkCode, scanCode, extended, injected)
        return True

    def event_typedCharacter(self, obj, nextHandler, ch):
        if hasattr(self, 'handler'):
            try:
                cfg = self.handler._cached_config
                if cfg.get("typing_sounds", True):
                    vk = getattr(self, "_last_vkCode", None)
                    ext = getattr(self, "_last_extended", None)
                    if cfg.get("typing_sounds_edit_only", False):
                        if getattr(self, "_last_focus_is_editable", True):
                            self.handler.play_typing_sound(ch=ch, vkCode=vk, extended=ext)
                    else:
                        self.handler.play_typing_sound(ch=ch, vkCode=vk, extended=ext)
            except Exception as e:
                log.debugWarning(f"event_typedCharacter: {e}")
        try:
            nextHandler()
        except StopIteration:
            raise
        except Exception as e:
            log.debugWarning(f"event_typedCharacter nextHandler: {e}")
    @script(description=_("Switches to the next audio theme."), gestures=[])
    def script_nextAudioTheme(self, gesture):
        themes = self.handler.get_installed_themes()
        if not themes: return
        current_folder = config.conf["audiothemes"].get("active_theme", "Default")
        idx = next((i for i, t in enumerate(themes) if t.folder == current_folder), -1)
        next_idx = (idx + 1) % len(themes)
        new_theme = themes[next_idx]
        config.conf["audiothemes"]["active_theme"] = new_theme.folder
        self.handler.configure()
        ui.message(new_theme.name)

    @script(description=_("Switches to the previous audio theme."), gestures=[])
    def script_previousAudioTheme(self, gesture):
        themes = self.handler.get_installed_themes()
        if not themes: return
        current_folder = config.conf["audiothemes"].get("active_theme", "Default")
        idx = next((i for i, t in enumerate(themes) if t.folder == current_folder), -1)
        prev_idx = (idx - 1) % len(themes)
        new_theme = themes[prev_idx]
        config.conf["audiothemes"]["active_theme"] = new_theme.folder
        self.handler.configure()
        ui.message(new_theme.name)

    @script(description=_("Increases the audio themes volume by 5 percent."), gestures=[])
    def script_increaseAudioThemesVolume(self, gesture):
        vol = config.conf["audiothemes"]["volume"]
        new_vol = min(100, vol + 5)
        config.conf["audiothemes"]["volume"] = new_vol
        self.handler.configure()
        ui.message(_("Volume {vol}").format(vol=new_vol))

    @script(description=_("Decreases the audio themes volume by 5 percent."), gestures=[])
    def script_decreaseAudioThemesVolume(self, gesture):
        vol = config.conf["audiothemes"]["volume"]
        new_vol = max(0, vol - 5)
        config.conf["audiothemes"]["volume"] = new_vol
        self.handler.configure()
        ui.message(_("Volume {vol}").format(vol=new_vol))

    @script(gesture="kb:NVDA+alt+n")
    def script_toggleAudioThemes(self, gesture):
        from scriptHandler import getLastScriptRepeatCount
        import ui
        isSameScript = getLastScriptRepeatCount()
        if isSameScript == 0:
            enabled = not config.conf["audiothemes"]["enable_audio_themes"]
            config.conf["audiothemes"]["enable_audio_themes"] = enabled
            if hasattr(self, '_tray_toggle_item') and self._tray_toggle_item:
                self._tray_toggle_item.Check(enabled)
            self.handler.configure()
            if enabled:
                ui.message(_("Enable audio themes"))
            else:
                ui.message(_("Disable audio themes"))
        elif isSameScript == 1:
            typing_enabled = not config.conf["audiothemes"]["typing_sounds"]
            config.conf["audiothemes"]["typing_sounds"] = typing_enabled
            if typing_enabled:
                ui.message(_("Enable typing sounds"))
            else:
                ui.message(_("Disable typing sounds"))
    script_toggleAudioThemes.__doc__ = _("Pressing it once toggles audio themes on and off. Pressing twice toggles typing sounds.")

    def event_mouseMove(self, obj, nextHandler, x, y):
        if obj is not self._previous_mouse_object:
            self._previous_mouse_object = obj
            try:
                obj_info = self._snapshot_obj(obj, foreground_app=self.handler._current_app_name)
                utils.threadPool.add_task(self.playObject, obj_info)
            except Exception as e:
                log.debugWarning(f"event_mouseMove snapshot: {e}")
        try:
            nextHandler()
        except StopIteration:
            raise
        except Exception as e:
            log.debugWarning(f"event_mouseMove nextHandler: {e}")
    def event_show(self, obj, nextHandler):
        try:
            if getattr(obj, "role", None) == controlTypes.Role.HELPBALLOON:
                obj_info = self._snapshot_obj(obj, extra_snd=SpecialProps.notify, foreground_app=self.handler._current_app_name)
                utils.threadPool.add_task(self.playObject, obj_info)
        except Exception as e:
            log.debugWarning(f"event_show: {e}")
        try:
            nextHandler()
        except StopIteration:
            raise
        except Exception as e:
            log.debugWarning(f"event_show nextHandler: {e}")
    def event_documentLoadComplete(self, obj, nextHandler):
        # Cache app name on handler
        try:
            self.handler._current_app_name = obj.appModule.appName if obj.appModule else None
        except Exception:
            self.handler._current_app_name = None
        try:
            obj_info = self._snapshot_obj(obj, extra_snd=SpecialProps.loaded, foreground_app=self.handler._current_app_name)
            utils.threadPool.add_task(self.playObject, obj_info)
        except Exception as e:
            log.debug(f"AudioThemes event_documentLoadComplete: {e}")
        try:
            nextHandler()
        except StopIteration:
            raise
        except Exception as e:
            log.debugWarning(f"event_documentLoadComplete nextHandler: {e}")
    def playObject(self, obj_info):
        """
        Resolve the sound for an object and play it.

        obj_info is a plain dict produced by _snapshot_obj() on the main
        thread.  It contains: role, states, name, location, windowClassName,
        parent_role, previous_role, next_role, snd.

        NO COM access occurs here -- everything was pre-extracted.
        """
        try:
            foreground_app = obj_info.get("foreground_app")
            theme = self.handler.get_theme_for_app(foreground_app)
            if log.isEnabledFor(log.DEBUG):
                log.debug(f"playObject app={foreground_app} theme={'present' if theme else 'None'} role={obj_info.get('role', 0)}")

            current_states = obj_info.get("states", frozenset())

            fl_cfg = getattr(self.handler, '_cached_config', None) or {}
            suppress_role = fl_cfg.get("state_sounds_suppress_role", False)

            # --- State-based sound ------------------------------------------
            if theme and current_states:
                if suppress_role:
                    # Old behavior: first matching state sound breaks, role sound skipped
                    theme_sounds = theme.sounds
                    for state in current_states:
                        state_snd = state + STATE_OFFSET
                        has_state_snd = state_snd in theme_sounds
                        if has_state_snd:
                            self.handler.play(obj_info, state_snd, _pre_resolved_theme=theme)
                            break
                else:
                    # New behavior: play ALL matching state sounds, then role sound
                    theme_sounds = theme.sounds
                    for state in current_states:
                        state_snd = state + STATE_OFFSET
                        has_state_snd = state_snd in theme_sounds
                        if has_state_snd:
                            self.handler.play(obj_info, state_snd, _pre_resolved_theme=theme)

            # --- Emoji role sound suppression ---
            emoji_suppress = fl_cfg.get("emoji_suppress_role_sound", False)
            if emoji_suppress and (
                obj_info.get("suppress_role_sound") or
                _text_contains_emoji(obj_info.get("name", ""))
            ):
                return

            # --- Role-based sound (always played unless suppress_role + a state played) ---
            order = self.getOrder(obj_info)
            snd = obj_info.get("snd")
            if snd is None:
                is_protected = (
                    controlTypes.State.PROTECTED in current_states
                )
                if is_protected:
                    snd = SpecialProps.protected
                elif order:
                    snd = order
                else:
                    snd = obj_info.get("role", 0)
                    if not snd and not obj_info.get("force_3d", False):
                        return

            self.handler.play(obj_info, snd, _pre_resolved_theme=theme)

        except Exception as e:
            log.debugWarning(f"playObject failed: {e}")
            return

    def _unspoken_play_role(self, role_val, states, heading_level=None):
        """Play a sound for a role encountered during speech output."""
        try:
            # Route heading level 7-9 to SpecialProps heading7/8/9
            if heading_level is not None and heading_level >= 7:
                h_key = _HEADING_LEVEL_MAP.get(heading_level)
                if h_key is not None:
                    role_val = h_key.value
            foreground_app = utils.getCurrentContext()[0]
            suppress_role = is_emoji_suppress_role_flag_set()
            obj_info = {
                "role": role_val,
                "states": frozenset(states) if isinstance(states, (list, set)) else frozenset(),
                "foreground_app": foreground_app,
                "snd": None,
                "force_3d": False,
                "suppress_role_sound": suppress_role,
            }
            utils.threadPool.add_task(self.playObject, obj_info)
        except Exception as e:
            log.debugWarning(f"_unspoken_play_role failed: {e}")

    def getOrder(self, obj_info, parrole=None, chrole=None):
        """Determine first/last item in any container from pre-extracted dict.

        Supports universal first/last detection for ALL roles, configurable
        via ``universal_fl_enabled``, ``fl_enabled_roles``, and
        ``fl_solo_behavior`` in the Audio Themes config.
        """
        role = obj_info.get("role")
        if not role:
            return None

        # Cache FL config once per object (snapshot from last configure())
        try:
            fl_cfg = self.handler._cached_config
        except Exception:
            fl_cfg = {}

        # Legacy mode: only LISTITEM / TREEVIEWITEM
        if not fl_cfg.get("universal_fl_enabled", True):
            if parrole is None:
                if role == controlTypes.Role.TREEVIEWITEM:
                    parrole = controlTypes.Role.TREEVIEW.value
                else:
                    parrole = controlTypes.Role.LIST.value
            if chrole is None:
                if role == controlTypes.Role.TREEVIEWITEM:
                    chrole = controlTypes.Role.TREEVIEWITEM.value
                else:
                    chrole = controlTypes.Role.LISTITEM.value
            if role != chrole:
                return None
            parent_role = obj_info.get("parent_role")
            if parent_role is not None and parent_role != parrole:
                return None
            prev_role = obj_info.get("previous_role")
            if prev_role is None or prev_role != chrole:
                return SpecialProps.first
            next_role = obj_info.get("next_role")
            if next_role is None or next_role != chrole:
                return SpecialProps.last
            return None

        # --- Universal mode ------------------------------------------------
        # Check role filter – which roles are enabled for FL detection?
        fl_enabled_set = fl_cfg.get("fl_enabled_roles_set")
        if fl_enabled_set is not None:
            r_name = role_int_to_name.get(role)
            if r_name and r_name not in fl_enabled_set:
                return None

        prev_role = obj_info.get("previous_role")
        next_role = obj_info.get("next_role")
        prev_same_role = obj_info.get("prev_same_role")
        next_same_role = obj_info.get("next_same_role")
        fl_mode = fl_cfg.get("fl_detection_mode", "smart")

        # Determine is_first / is_last based on detection mode
        if fl_mode == "strict":
            # Only same-role siblings count (ignores separators, headings, etc.)
            is_first = prev_same_role is None
            is_last = next_same_role is None
        elif fl_mode == "any_sibling":
            # Any adjacent item counts (current v9.31 behavior)
            is_first = prev_role is None
            is_last = next_role is None
        else:
            # "smart" (default) – same-role check with any-sibling fallback
            if prev_same_role is not None:
                is_first = False
            elif prev_role is None:
                is_first = True
            else:
                # prev exists but different role, no same-role found → first
                is_first = True
            if next_same_role is not None:
                is_last = False
            elif next_role is None:
                is_last = True
            else:
                is_last = True

        # Solo items: no siblings at all (regardless of mode)
        has_any_adjacent = prev_role is not None or next_role is not None
        if is_first and is_last and not has_any_adjacent:
            solo = fl_cfg.get("fl_solo_behavior", "first")
            if solo == "first":
                return SpecialProps.first
            elif solo == "last":
                return SpecialProps.last
            return None  # "none" – skip solo items

        if is_first:
            return SpecialProps.first
        if is_last:
            return SpecialProps.last
        return None

    @script(description=_("Toggle Earcons and Speech Rules."), gestures=['kb:NVDA+Alt+p'])
    def script_togglePp(self, gesture):
        enabled = utils.getConfig("enabled")
        enabled = not enabled
        utils.setConfig("enabled", enabled)
        if enabled:
            msg = _("Earcons and Speech Rules on")
        else:
            msg = _("Earcons and Speech Rules off")
        ui.message(msg)

    @script(description=_("Toggle state verbosity reporting."), gestures=['kb:NVDA+Alt+['])
    def script_toggleStateVerbosity(self, gesture):
        verbose = utils.getConfig("stateVerbose")
        verbose = not verbose
        utils.setConfig("stateVerbose", verbose)
        if verbose:
            msg = _("Verbose state reporting")
        else:
            msg = _("Concise state reporting")
        ui.message(msg)
        frenzy.updateRules()

    @script(description=_("Rotates the global speech order format."), gestures=[])
    def script_rotateSpeechOrder(self, gesture):
        fmt = config.conf["audiothemes"].get("announceFormat", "0")
        
        if fmt == "0":
            new_fmt = "rsc"
            msg = _("Speech order: Role, State, Name")
        elif fmt == "rsc":
            new_fmt = "sc"
            msg = _("Speech order: State, Name")
        else:
            new_fmt = "0"
            msg = _("Speech order: Default (Name, Role, State)")
            
        config.conf["audiothemes"]["announceFormat"] = new_fmt
        ui.message(msg)

    @script(description=_("Speak current heading level."), gestures=['kb:NVDA+h'])
    def script_speakHeadingLevel(self, gesture):
        count=scriptHandler.getLastScriptRepeatCount()
        focus  = api.getFocusObject()
        if focus is None:
            ui.message(_("No heading level information"))
            return
        if focus.treeInterceptor is not None:
            if not focus.treeInterceptor.passThrough:
                focus = focus.treeInterceptor
        try:
            info = focus.makeTextInfo(textInfos.POSITION_CARET)
        except (NotImplementedError, RuntimeError):
            ui.message(_("No heading level information"))
            return
        info.expand(textInfos.UNIT_CHARACTER)
        fields = info.getTextWithFields()
        levelFound = False
        for field in fields:
            if(
                isinstance(field,textInfos.FieldCommand)
                and field.command == "controlStart"
            ):
                try:
                    role = field.field['role']
                    level = field.field['level']
                except KeyError:
                    continue
                if count == 0 and role != controlTypes.Role.HEADING:
                    continue
                roleText = role.displayString
                ui.message(_("{roleText} level {level}").format(**locals()))
                levelFound = True
        if not levelFound:
            ui.message(_("No heading level information"))

    @script(description=_("Cycles through available audio themes."), gestures=['kb:NVDA+alt+t'])
    def script_cycleAudioThemes(self, gesture):
        themes = getattr(self.handler, "themes", {})
        if not themes:
            ui.message(_("No audio themes available"))
            return
            
        current = config.conf["audiothemes"]["active_theme"]
        theme_names = list(themes.keys())
        if not theme_names:
            return
            
        try:
            current_idx = theme_names.index(current)
        except ValueError:
            current_idx = -1
            
        next_idx = (current_idx + 1) % len(theme_names)
        next_theme = theme_names[next_idx]
        
        config.conf["audiothemes"]["active_theme"] = next_theme
        self.handler.configure()
        ui.message(_("Audio theme: {theme}").format(theme=next_theme))

    @script(description=_("Cycles through available typing sound packs."), gestures=['kb:NVDA+alt+y'])
    def script_cycleTypingSounds(self, gesture):
        from .handler import get_typing_sound_packs
        packs = get_typing_sound_packs()
        if not packs:
            ui.message(_("No typing sound packs available"))
            return
            
        current = config.conf["audiothemes"]["typing_sound_pack"]
        try:
            current_idx = packs.index(current)
        except ValueError:
            current_idx = -1
            
        next_idx = (current_idx + 1) % len(packs)
        next_pack = packs[next_idx]
        
        config.conf["audiothemes"]["typing_sound_pack"] = next_pack
        self.handler.configure()
        ui.message(_("Typing sounds: {pack}").format(pack=next_pack))

    @script(description=_("Toggles typing sounds on and off."), gestures=['kb:NVDA+alt+k'])
    def script_toggleTypingSounds(self, gesture):
        typing_enabled = not config.conf["audiothemes"]["typing_sounds"]
        config.conf["audiothemes"]["typing_sounds"] = typing_enabled
        self.handler.configure()
        if typing_enabled:
            ui.message(_("Typing sounds enabled"))
        else:
            ui.message(_("Typing sounds disabled"))

    @script(description=_("Sets an audio beacon at the current navigator object. Navigate around to hear a sonar ping relative to this beacon."), gestures=['kb:NVDA+shift+b'])
    def script_toggleAudioBeacon(self, gesture):
        if self._audio_beacon_location:
            self._audio_beacon_location = None
            self._audio_beacon_desktop = None
            ui.message(_("Audio beacon removed"))
            return
            
        obj = api.getNavigatorObject()
        if not obj or not obj.location:
            ui.message(_("Current object has no location"))
            return
            
        self._audio_beacon_location = tuple(obj.location)
        desktop = api.getDesktopObject()
        if desktop and desktop.location:
            self._audio_beacon_desktop = tuple(desktop.location)
            
        ui.message(_("Audio beacon dropped at current location"))
        from .utils import is_sound_suppressed
        if is_sound_suppressed("ui_beeps"):
            return
        try:
            from . import frenzy
            df = frenzy.get_ducking_factor("ui_beeps")
            if df < 1.0:
                tones.beep(800, 100, left=int(25*df), right=int(25*df))
                tones.beep(1200, 100, left=int(25*df), right=int(25*df))
            else:
                tones.beep(800, 100)
                tones.beep(1200, 100)
        except Exception:
            tones.beep(800, 100)
            tones.beep(1200, 100)

    @script(description=_("Audio Sonar: Sweeps the active window to create an audio map of its elements."), gestures=['kb:NVDA+Alt+r'])
    def script_audioSonar(self, gesture):
        obj = api.getForegroundObject()
        if not obj:
            return
            
        children = []
        def collect_children(root, depth=0):
            if depth > 1: return
            try:
                for child in root.children:
                    loc = child.location
                    if loc and loc[2] > 0 and loc[3] > 0:
                        children.append(child)
                    collect_children(child, depth + 1)
            except Exception as e:
                log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
        collect_children(obj)
        # sort by X coordinate
        try:
            children.sort(key=lambda c: c.location[0] if c.location else 0)
        except Exception:
            pass
        
        snapshots = []
        for child in children:
            try:
                obj_info = self._snapshot_obj(child)
                obj_info["force_3d"] = True
                # Force X pan based on screen position
                desktop = obj_info.get("desktop_location")
                if desktop and desktop[2] > 0:
                    loc = obj_info["location"]
                    c_x = loc[0] + (loc[2] / 2.0)
                    nx = (c_x / float(desktop[2])) - 0.5 # -0.5 to 0.5
                    obj_info["progress_angle"] = nx * 90.0 # -45 to 45
                snapshots.append(obj_info)
            except Exception as e:
                log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
        def sweep():
            for obj_info in snapshots:
                try:
                    self.playObject(obj_info)
                    time.sleep(0.04)
                except Exception as e:
                    log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
        utils.threadPool.add_task(sweep)

    @script(description=_("Toggles audio ducking on and off."))
    def script_toggleAudioDucking(self, gesture):
        enabled = not config.conf["audiothemes"]["audio_ducking_enabled"]
        config.conf["audiothemes"]["audio_ducking_enabled"] = enabled
        ui.message(_("Audio ducking enabled") if enabled else _("Audio ducking disabled"))

    @script(description=_("Toggles emoji enhancement sounds on and off."), gestures=['kb:NVDA+alt+e'])
    def script_toggleEmojiSounds(self, gesture):
        enabled = not config.conf["audiothemes"]["emoji_enabled"]
        config.conf["audiothemes"]["emoji_enabled"] = enabled
        ui.message(_("Emoji sounds enabled") if enabled else _("Emoji sounds disabled"))

    @script(description=_("Toggles app-specific audio profiles on and off."))
    def script_toggleAppProfiles(self, gesture):
        enabled = not config.conf["audiothemes"]["app_profiles_enabled"]
        config.conf["audiothemes"]["app_profiles_enabled"] = enabled
        ui.message(_("App profiles enabled") if enabled else _("App profiles disabled"))

    @script(description=_("Toggles 3D spatial audio mode on and off."))
    def script_toggle3DAudio(self, gesture):
        enabled = not config.conf["audiothemes"]["audio3d"]
        config.conf["audiothemes"]["audio3d"] = enabled
        self.handler.configure()
        ui.message(_("3D audio enabled") if enabled else _("3D audio disabled"))

    @script(description=_("Toggles clipboard announcement sounds on and off."), gestures=['kb:NVDA+alt+c'])
    def script_toggleClipboard(self, gesture):
        enabled = not config.conf["audiothemes"]["clipboard_enabled"]
        config.conf["audiothemes"]["clipboard_enabled"] = enabled
        ui.message(_("Clipboard announcements enabled") if enabled else _("Clipboard announcements disabled"))

    @script(description=_("Toggles system status monitoring sounds on and off."))
    def script_toggleSystemStatus(self, gesture):
        enabled = not config.conf["audiothemes"]["sys_status_enabled"]
        config.conf["audiothemes"]["sys_status_enabled"] = enabled
        ui.message(_("System status sounds enabled") if enabled else _("System status sounds disabled"))

    @script(description=_("Opens the Audio Themes Studio to create and edit themes."))
    def script_openStudio(self, gesture):
        if self._studioDialog is not None:
            try:
                self._studioDialog.Raise()
                return
            except Exception:
                self._studioDialog = None
        from .studio import AudioThemesStudioStartupDialog
        import wx
        with AudioThemesStudioStartupDialog(self, _("Audio Themes Studio")) as dlg:
            self._studioDialog = dlg
            dlg.Raise()
            dlg.ShowModal()
        self._studioDialog = None

    @script(description=_("Toggles speaking of object roles on and off."))
    def script_toggleSpeakRoles(self, gesture):
        enabled = not config.conf["audiothemes"]["speak_roles"]
        config.conf["audiothemes"]["speak_roles"] = enabled
        self.handler.configure()
        ui.message(_("Speak roles enabled") if enabled else _("Speak roles disabled"))

    @script(description=_("Opens the Audio Themes settings panel."))
    def script_openSettings(self, gesture):
        import wx
        from gui import mainFrame
        def do_open():
            try:
                if hasattr(mainFrame, "popupSettingsDialog"):
                    mainFrame.popupSettingsDialog(AudioThemesSettingsPanel)
                else:
                    mainFrame._popupSettingsDialog(AudioThemesSettingsPanel)
            except Exception as e:
                log.error(f"Failed to open Audio Themes settings: {e}", exc_info=True)
                ui.message(_("Failed to open settings. Please open through NVDA Preferences."))
        wx.CallAfter(do_open)

    @script(description=_("Cycles the audio output mode between stereo and mono."))
    def script_toggleOutputMode(self, gesture):
        current = config.conf["audiothemes"]["output_mode"]
        new_mode = "mono" if current == "stereo" else "stereo"
        config.conf["audiothemes"]["output_mode"] = new_mode
        self.handler.configure()
        ui.message(_("Output mode: {mode}").format(mode=new_mode))

    @script(description=_("Reports current system power status (battery and AC)."))
    def script_reportSystemStatus(self, gesture):
        try:
            class SYSTEM_POWER_STATUS(ctypes.Structure):
                _fields_ = [
                    ("ACLineStatus", ctypes.c_byte),
                    ("BatteryFlag", ctypes.c_byte),
                    ("BatteryLifePercent", ctypes.c_byte),
                    ("Reserved1", ctypes.c_byte),
                    ("BatteryLifeTime", ctypes.wintypes.DWORD),
                    ("BatteryFullLifeTime", ctypes.wintypes.DWORD),
                ]
            sps = SYSTEM_POWER_STATUS()
            ret = ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(sps))
            if ret:
                ac = _("Plugged in") if sps.ACLineStatus == 1 else _("On battery")
                if sps.BatteryLifePercent == 255:
                    msg = _("System status: {ac}, battery status unknown").format(ac=ac)
                else:
                    msg = _("System status: {ac}, battery {percent}%").format(ac=ac, percent=sps.BatteryLifePercent)
                ui.message(msg)
            else:
                ui.message(_("Unable to retrieve system power status"))
        except Exception:
            ui.message(_("Unable to retrieve system power status"))

    # ────────────────────────────────────────────────
    # SentenceNav scripts are inherited from SentenceNavMixin:
    #   Alt+DownArrow  → script_nextSentence
    #   Alt+UpArrow    → script_previousSentence
    #   NVDA+Alt+S     → script_currentSentence
    #   Alt+Win+Down   → script_nextPhrase
    #   Alt+Win+Up     → script_previousPhrase
    #
    # BrowserNav scripts are injected via injectBrowseModeKeystrokes():
    #   NVDA+Alt+DownArrow  → moveToNextSibling
    #   NVDA+Alt+UpArrow    → moveToPreviousSibling
    #   NVDA+Alt+LeftArrow  → moveToParent
    #   NVDA+Alt+RightArrow → moveToChild
    #   NVDA+O              → rotor
    #   J / Shift+J         → QuickJump
    #   etc.
    #
    # Plain DownArrow/UpArrow → NVDA built-in line navigation (no override!)
    # ────────────────────────────────────────────────

    # Clipboard detection is handled via keyboard hook in _new_keyDownEvent
    # to avoid breaking NVDA's built-in clipboard handling.
    # ────────────────────────────────────────────────
