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
import _ctypes
import time
import wx
import config
import config
import globalPluginHandler
import appModuleHandler
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

from .handler import AudioThemesHandler, SpecialProps
from .settings import AudioThemesSettingsPanel
from .studio import AudioThemesStudioStartupDialog

from . import phoneticPunctuation as pp
from . import utils
from . import frenzy

# Import the SentenceNav engine (Alt+Arrow sentence/phrase navigation)
from .sentenceNavEngine import SentenceNavMixin, initSentenceNavConfiguration

# Import the BrowserNav engine (NVDA+Alt+Arrow browser navigation, QuickJump, etc.)
from .browserNavEngine import BrowserNavMixin

import api

import addonHandler
try:
    addonHandler.initTranslation()
except AttributeError:
    pass

utils.initConfiguration()
pp.reloadRules()

from . import quicknav

# Initialize SentenceNav config section
initSentenceNavConfiguration()


class GlobalPlugin(SentenceNavMixin, BrowserNavMixin, globalPluginHandler.GlobalPlugin):

    browser_apps = ["firefox", "iexplore", "chrome", "opera", "edge"]
    scriptCategory = _("Audio Themes NG")

    # -- COM-safety: extract everything on the main thread ---------------
    @staticmethod
    def _snapshot_obj(obj, extra_snd=None):
        """
        Build a plain dict from a live NVDAObject.  MUST be called on the
        NVDA main thread (i.e. inside an event handler) where COM access
        is legal.  The returned dict is safe to pass to any thread.
        """
        import config as _cfg
        info = {}
        try:
            info["role"] = obj.role
        except Exception:
            info["role"] = 0
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
        # --- getOrder data (parent / previous / next roles) ---
        # These are expensive COM traversals; only do them if audio is enabled and it's a list item.
        if _cfg.conf["audiothemes"]["enable_audio_themes"]:
            try:
                role = info.get("role", 0)
                if role in (controlTypes.Role.LISTITEM, controlTypes.Role.TREEVIEWITEM):
                    info["parent_role"] = obj.parent.role if obj.parent else None
                    info["previous_role"] = obj.previous.role if obj.previous else None
                    info["next_role"] = obj.next.role if obj.next else None
                else:
                    info["parent_role"] = None
                    info["previous_role"] = None
                    info["next_role"] = None
            except Exception:
                info["parent_role"] = None
                info["previous_role"] = None
                info["next_role"] = None
        else:
            info["parent_role"] = None
            info["previous_role"] = None
            info["next_role"] = None
        # Carry forward a custom snd override (e.g. SpecialProps.notify).
        info["snd"] = extra_snd
        # Desktop dimensions for 3D audio (avoids COM call on worker thread).
        try:
            desktop = NVDAObjects.api.getDesktopObject()
            info["desktop_location"] = tuple(desktop.location) if desktop and desktop.location else None
        except Exception:
            info["desktop_location"] = None
        # Foreground app name for disabled-apps filtering (avoids COM on worker thread).
        try:
            from . import utils
            appName, _, _ = utils.getCurrentContext()
            info["foreground_app"] = appName
        except Exception:
            info["foreground_app"] = None
        return info

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from . import utils
        utils.threadPool.restart()
        self.handler = AudioThemesHandler()
        GlobalPlugin._instance_handler = self.handler
        
        # Patch Quick Nav Interceptor
        self.quicknav_interceptor = quicknav.BrowseModeQuickNavInterceptor(self.handler)
        self.quicknav_interceptor.patch()
        
        gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(
            AudioThemesSettingsPanel
        )
        self._previous_mouse_object = None
        self._last_navigator_object = None
        self._last_play_time = 0  # debounce: monotonic timestamp of last dispatch
        self._last_focused_obj = None   # for gainFocus / becomeNavigator dedup
        self._last_focus_time = 0.0
        self._audio_beacon_location = None
        self._audio_beacon_desktop = None
        self._last_focus_is_editable = False
        # Add the menu item for the audio themes studio
        self.studioMenuItem = gui.mainFrame.sysTrayIcon.menu.Append(
            wx.ID_ANY,
            # Translators: label for the audio themes studio menu item
            _("&Audio Themes Studio"),
        )
        gui.mainFrame.sysTrayIcon.Bind(
            wx.EVT_MENU, self.on_studio_item_clicked, self.studioMenuItem
        )

        # Add checkable menu item for quickly toggling audio themes
        self.toggleMenuItem = gui.mainFrame.sysTrayIcon.menu.AppendCheckItem(
            wx.ID_ANY,
            _("Enable Audio Themes"),
        )
        import config
        self.toggleMenuItem.Check(config.conf["audiothemes"]["enable_audio_themes"])
        gui.mainFrame.sysTrayIcon.Bind(
            wx.EVT_MENU, self.on_toggle_item_clicked, self.toggleMenuItem
        )

        # Browse-mode navigation timer: polls the navigator object every 180ms.
        # This is the ONLY way to detect arrow-key movement inside a virtual
        # buffer (browse mode), because NVDA does not fire event_gainFocus or
        # event_becomeNavigatorObject during virtual-buffer caret moves.
        self._navigation_timer = wx.Timer()
        self._navigation_timer.Bind(wx.EVT_TIMER, self._onNavigationTimer)
        self._navigation_timer.Start(180)

        # Phonetic Punctuation Initialization
        self.injectMonkeyPatches()
        
        self._keyboard_hooked = False
        self._hook_keyboard()
        
        # Restore caretMovementScriptHelper hook for arrow keys
        self.orig_caretMovementScriptHelper = None
        try:
            import speech
            self.orig_caretMovementScriptHelper = speech._caretMovementScriptHelper
            speech._caretMovementScriptHelper = self._hook_caretMovementScriptHelper
        except Exception as e:
            try:
                from logHandler import log
                log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
            except:
                pass
        # ── BrowserNav initialization ──
        # Wire up all BrowserNav monkey patches, browse-mode keystrokes,
        # QuickJump system, and URL tracking.
        try:
            self.initBrowserNav()
        except Exception:
            from logHandler import log
            log.exception("Failed to initialize BrowserNav engine")

        self.toggling = False
        self._audioThemesLayerGestures = {
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
            "kb:h": "audioThemesHelp",
        }
        self._rebindInstanceGestures()

    def _hook_caretMovementScriptHelper(self, extraDetail, unit, direction, posConstant=textInfos.POSITION_CARET, *args, **kwargs):
        if self.orig_caretMovementScriptHelper:
            self.orig_caretMovementScriptHelper(extraDetail, unit, direction, posConstant, *args, **kwargs)
        try:
            import api
            import time
            current_nav = api.getNavigatorObject()
            if current_nav and getattr(current_nav, 'treeInterceptor', None) and not current_nav.treeInterceptor.passThrough:
                if current_nav != getattr(self, "_last_navigator_object", None):
                    self._last_navigator_object = current_nav
                    self._last_play_time = time.monotonic()
                    obj_info = self._snapshot_obj(current_nav)
                    from . import utils
                    utils.threadPool.add_task(self.playObject, obj_info)
                    utils.threadPool.add_task(self._play_beacon_sonar, obj_info)
        except Exception as e:
            try:
                from logHandler import log
                log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
            except:
                pass
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

    @script(description=_("Audio themes command layer. Press this then a command key (e.g. h for help)."), gestures=['kb:NVDA+shift+a'])
    def script_audioThemesLayer(self, gesture):
        if getattr(self, "toggling", False):
            self.script_error(gesture)
            return
        self.bindGestures(self._audioThemesLayerGestures)
        self.toggling = True
        import tones
        tones.beep(200, 40)

    def getScript(self, gesture):
        from keyboardHandler import KeyboardInputGesture
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
        from functools import wraps
        @wraps(func)
        def new(*args, **kwargs):
            try:
                func(*args, **kwargs)
            finally:
                final()
        return new

    def finish(self):
        self.toggling = False
        self.clearGestureBindings()
        self._rebindInstanceGestures()

    def noFinish(self):
        pass

    def script_error(self, gesture):
        import tones
        tones.beep(420, 40)

    @script(description=_("Shows audio themes commands help."))
    def script_audioThemesHelp(self, gesture):
        import wx
        from gui import mainFrame
        
        def runDialog():
            dlg = wx.SingleChoiceDialog(
                mainFrame,
                _("Select an audio themes command to execute:"),
                _("Audio Themes Commands"),
                [
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
                    "w: " + _("Speak Object 3D Coordinates") + " " + _("(Plays 3D sound even if 3D mode is disabled)")
                ]
            )
            if dlg.ShowModal() == wx.ID_OK:
                sel = dlg.GetSelection()
                if sel == 0:
                    self.script_toggleAudioThemes(None)
                elif sel == 1:
                    self.script_togglePp(None)
                elif sel == 2:
                    self.script_nextAudioTheme(None)
                elif sel == 3:
                    self.script_previousAudioTheme(None)
                elif sel == 4:
                    self.script_increaseAudioThemesVolume(None)
                elif sel == 5:
                    self.script_decreaseAudioThemesVolume(None)
                elif sel == 6:
                    self.script_toggleStateVerbosity(None)
                elif sel == 7:
                    self.script_speakHeadingLevel(None)
                elif sel == 8:
                    self.script_rotateSpeechOrder(None)
                elif sel == 9:
                    self.script_cycleAudioThemes(None)
                elif sel == 10:
                    self.script_cycleTypingSounds(None)
                elif sel == 11:
                    self.script_toggleTypingSounds(None)
                elif sel == 12:
                    self.script_toggleAudioBeacon(None)
                elif sel == 13:
                    self.script_audioSonar(None)
                elif sel == 14:
                    self.script_speakObject(None)
            dlg.Destroy()
        wx.CallAfter(runDialog)

    def terminate(self):
        with suppress(Exception):
            gui.settingsDialogs.NVDASettingsDialog.categoryClasses.remove(
                AudioThemesSettingsPanel
            )
            gui.mainFrame.sysTrayIcon.menu.RemoveItem(self.studioMenuItem)
            
            gui.mainFrame.sysTrayIcon.menu.RemoveItem(self.toggleMenuItem)
            self.restoreMonkeyPatches()
            self._unhook_keyboard()
            if self.orig_caretMovementScriptHelper:
                import speech
                speech._caretMovementScriptHelper = self.orig_caretMovementScriptHelper
                
            self.quicknav_interceptor.terminate()
            self.handler.close()
            self._navigation_timer.Stop()
            # Shut down the shared thread pool cleanly so worker threads do not
            # linger after the add-on is unloaded.
            utils.threadPool.shutdown(wait=True)
        # ── BrowserNav termination ──
        with suppress(Exception):
            self.terminateBrowserNav()
        # Ensure mixin classes (SentenceNavMixin, BrowserNavMixin) clean up properly.
        with suppress(Exception):
            super().terminate()

    def injectMonkeyPatches(self):
        pp.injectMonkeyPatches()
        frenzy.monkeyPatch()

    def restoreMonkeyPatches(self):
        pp.restoreMonkeyPatches()
        frenzy.monkeyUnpatch()

    # Browse-mode navigation: timer-based polling of navigator object.
    def _onNavigationTimer(self, event):
        """Check if the navigator object changed (e.g. arrow keys in browse mode)."""
        try:
            current_nav = api.getNavigatorObject()
            if current_nav.treeInterceptor and not current_nav.treeInterceptor.passThrough:
                if current_nav and current_nav != getattr(self, "_last_navigator_object", None):
                    self._last_navigator_object = current_nav
                    # Debounce: skip if last dispatch was < 80ms ago.
                    import time
                    now = time.monotonic()
                    if now - getattr(self, "_last_play_time", 0) < 0.08:
                        return
                    if getattr(self.handler, "last_quicknav_time", 0) and now - self.handler.last_quicknav_time < 0.3:
                        return
                    self._last_play_time = now
                    obj_info = self._snapshot_obj(current_nav)
                    from . import utils
                    utils.threadPool.add_task(self.playObject, obj_info)
                    utils.threadPool.add_task(self._play_beacon_sonar, obj_info)
        except Exception as e:
            try:
                from logHandler import log
                log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
            except:
                pass
    def on_studio_item_clicked(self, event):
        # Translators: title for the audio themes studio dialog
        with AudioThemesStudioStartupDialog(self, _("Audio Themes Studio")) as dlg:
            dlg.ShowModal()

    def on_settings_item_clicked(self, event):
        import wx
        def do_open():
            try:
                if hasattr(gui.mainFrame, "popupSettingsDialog"):
                    gui.mainFrame.popupSettingsDialog(AudioThemesSettingsPanel)
                else:
                    gui.mainFrame._popupSettingsDialog(AudioThemesSettingsPanel)
            except Exception as e:
                from logHandler import log
                log.error(f"Failed to open Audio Themes settings: {e}", exc_info=True)
                import ui
                ui.message(_("Failed to open settings. Please open through NVDA Preferences."))
        wx.CallAfter(do_open)

    def on_toggle_item_clicked(self, event):
        import config
        enabled = not config.conf["audiothemes"]["enable_audio_themes"]
        config.conf["audiothemes"]["enable_audio_themes"] = enabled
        self.toggleMenuItem.Check(enabled)
        # Notify handler
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
            self.handler._current_app_name = obj.appModule.appName
        except Exception:
            self.handler._current_app_name = None
        
        try:
            nextHandler()
        except Exception as e:
            try:
                from logHandler import log
                log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
            except:
                pass
        obj_info = self._snapshot_obj(obj)
        utils.threadPool.add_task(self.playObject, obj_info)
        utils.threadPool.add_task(self._play_beacon_sonar, obj_info)

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
            if desktop:
                nx = dx / float(desktop[2])
                ny = dy / float(desktop[3])
                obj_info["progress_angle"] = nx * 90.0
                self.handler.play_theme_sound("beacon", angle_x=nx * 90.0, angle_y=ny * 50.0)
        except Exception as e:
            try:
                from logHandler import log
                log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
            except:
                pass
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
            from .utils import getCurrentURLSafe
            self.handler._current_url = getCurrentURLSafe()
        except Exception:
            self.handler._current_app_name = None
            self.handler._current_window_title = None
            self.handler._current_url = None
        if isFocus:
            try:
                nextHandler()
            except Exception as e:
                try:
                    from logHandler import log
                    log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
                except:
                    pass
            return
        # Dedup: skip if gainFocus just fired for this very object
        if obj is self._last_focused_obj and (time.monotonic() - self._last_focus_time) < 0.3:
            try:
                nextHandler()
            except Exception as e:
                try:
                    from logHandler import log
                    log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
                except:
                    pass
            return
        try:
            nextHandler()
        except Exception as e:
            try:
                from logHandler import log
                log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
            except:
                pass
        self._last_play_time = time.monotonic()
        try:
            self._last_navigator_object = api.getNavigatorObject()
        except Exception:
            self._last_navigator_object = obj
        obj_info = self._snapshot_obj(obj)
        utils.threadPool.add_task(self.playObject, obj_info)
        utils.threadPool.add_task(self._play_beacon_sonar, obj_info)

    def event_valueChange(self, obj, nextHandler):
        try:
            if obj.role == controlTypes.Role.PROGRESSBAR:
                import config
                if config.conf["audiothemes"]["enable_audio_themes"] and self.handler.active_theme:
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
                            # Calculate custom X angle from -45 to 45 degrees based on progress
                            angle_x = -45.0 + (percent * 90.0)
                            
                            # Play progress bar earcon if exists
                            obj_info = self._snapshot_obj(obj)
                            obj_info['progress_angle'] = angle_x
                            obj_info['progress_percent'] = percent
                            utils.threadPool.add_task(self.playObject, obj_info)
                        except Exception as e:
                            try:
                                from logHandler import log
                                log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
                            except:
                                pass
        except Exception as e:
            try:
                from logHandler import log
                log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
            except:
                pass
        try:
            nextHandler()
        except Exception as e:
            try:
                from logHandler import log
                log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
            except:
                pass
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
        from logHandler import log
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
        from logHandler import log
        keyboardHandler.internal_keyDownEvent = self._original_keyDownEvent
        try:
            winInputHook.setCallbacks(keyDown=keyboardHandler.internal_keyDownEvent, keyUp=keyboardHandler.internal_keyUpEvent)
            log.info("AUDIO_THEMES: keyboard hook restored")
        except Exception as e:
            log.error(f"AUDIO_THEMES: Failed to restore winInputHook callbacks: {e}", exc_info=True)
        self._keyboard_hooked = False

    def _new_keyDownEvent(self, vkCode, scanCode, extended, injected):
        from logHandler import log
        # Only record last vkCode/extended if it is not injected, and not a modifier key
        if not injected and vkCode not in (16, 17, 18, 20, 91, 92, 144, 160, 161, 162, 163, 164, 165):
            self._last_vkCode = vkCode
            self._last_extended = extended
        import config
        # Play advanced typing sounds for non-characters
        try:
            if not injected and config.conf["audiothemes"]["typing_sounds"]:
                # Check edit only
                play = True
                if config.conf["audiothemes"]["typing_sounds_edit_only"]:
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
            try:
                from logHandler import log
                log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
            except:
                pass
        if self._original_keyDownEvent:
            return self._original_keyDownEvent(vkCode, scanCode, extended, injected)
        return True

    def event_typedCharacter(self, obj, nextHandler, ch):
        import config
        from logHandler import log
        try:
            if config.conf["audiothemes"]["typing_sounds"]:
                vk = getattr(self, "_last_vkCode", None)
                ext = getattr(self, "_last_extended", None)
                if config.conf["audiothemes"]["typing_sounds_edit_only"]:
                    if getattr(self, "_last_focus_is_editable", True):
                        self.handler.play_typing_sound(ch=ch, vkCode=vk, extended=ext)
                else:
                    self.handler.play_typing_sound(ch=ch, vkCode=vk, extended=ext)
        except Exception as e:
            try:
                from logHandler import log
                log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
            except:
                pass
        try:
            nextHandler()
        except Exception as e:
            try:
                from logHandler import log
                log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
            except:
                pass
    @script(description=_("Switches to the next audio theme."))
    def script_nextAudioTheme(self, gesture):
        import config
        themes = self.handler.get_installed_themes()
        if not themes: return
        current_folder = config.conf["audiothemes"].get("active_theme", "Default")
        idx = next((i for i, t in enumerate(themes) if t.folder == current_folder), -1)
        next_idx = (idx + 1) % len(themes)
        new_theme = themes[next_idx]
        config.conf["audiothemes"]["active_theme"] = new_theme.folder
        self.handler.configure()
        ui.message(new_theme.name)

    @script(description=_("Switches to the previous audio theme."))
    def script_previousAudioTheme(self, gesture):
        import config
        themes = self.handler.get_installed_themes()
        if not themes: return
        current_folder = config.conf["audiothemes"].get("active_theme", "Default")
        idx = next((i for i, t in enumerate(themes) if t.folder == current_folder), -1)
        prev_idx = (idx - 1) % len(themes)
        new_theme = themes[prev_idx]
        config.conf["audiothemes"]["active_theme"] = new_theme.folder
        self.handler.configure()
        ui.message(new_theme.name)

    @script(description=_("Increases the audio themes volume by 5 percent."))
    def script_increaseAudioThemesVolume(self, gesture):
        import config
        vol = config.conf["audiothemes"]["volume"]
        new_vol = min(100, vol + 5)
        config.conf["audiothemes"]["volume"] = new_vol
        self.handler.configure()
        ui.message(_("Volume {vol}").format(vol=new_vol))

    @script(description=_("Decreases the audio themes volume by 5 percent."))
    def script_decreaseAudioThemesVolume(self, gesture):
        import config
        vol = config.conf["audiothemes"]["volume"]
        new_vol = max(0, vol - 5)
        config.conf["audiothemes"]["volume"] = new_vol
        self.handler.configure()
        ui.message(_("Volume {vol}").format(vol=new_vol))

    @script(gesture="kb:NVDA+alt+n")
    def script_toggleAudioThemes(self, gesture):
        import config
        from scriptHandler import getLastScriptRepeatCount
        import ui
        isSameScript = getLastScriptRepeatCount()
        if isSameScript == 0:
            enabled = not config.conf["audiothemes"]["enable_audio_themes"]
            config.conf["audiothemes"]["enable_audio_themes"] = enabled
            self.toggleMenuItem.Check(enabled)
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
            obj_info = self._snapshot_obj(obj)
            utils.threadPool.add_task(self.playObject, obj_info)
        try:
            nextHandler()
        except Exception as e:
            try:
                from logHandler import log
                log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
            except:
                pass
    def event_show(self, obj, nextHandler):
        try:
            if obj.role == controlTypes.Role.HELPBALLOON:
                obj_info = self._snapshot_obj(obj, extra_snd=SpecialProps.notify)
                self.playObject(obj_info)
        except Exception as e:
            try:
                from logHandler import log
                log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
            except:
                pass
        try:
            nextHandler()
        except Exception as e:
            try:
                from logHandler import log
                log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
            except:
                pass
    def event_documentLoadComplete(self, obj, nextHandler):
        # Cache app name on handler
        try:
            self.handler._current_app_name = obj.appModule.appName if obj.appModule else None
        except Exception:
            self.handler._current_app_name = None
        try:
            if appModuleHandler.getAppNameFromProcessID(obj.processID) in self.browser_apps:
                obj_info = self._snapshot_obj(obj)
                utils.threadPool.add_task(self.playObject, obj_info)
        except Exception as e:
            try:
                from logHandler import log
                log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
            except:
                pass
        try:
            nextHandler()
        except Exception as e:
            try:
                from logHandler import log
                log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
            except:
                pass
    def playObject(self, obj_info):
        """
        Resolve the sound for an object and play it.

        obj_info is a plain dict produced by _snapshot_obj() on the main
        thread.  It contains: role, states, name, location, windowClassName,
        parent_role, previous_role, next_role, snd.

        NO COM access occurs here -- everything was pre-extracted.
        """
        try:
            from .handler import STATE_OFFSET

            foreground_app = obj_info.get("foreground_app")
            theme = self.handler.get_theme_for_app(foreground_app)
            
            played_state = False

            current_states = obj_info.get("states", frozenset())

            # --- State-based sound ------------------------------------------
            if theme and current_states:
                for state in current_states:
                    state_snd = state + STATE_OFFSET
                    with theme._lock:
                        has_state_snd = state_snd in theme.sounds
                    if has_state_snd:
                        self.handler.play(obj_info, state_snd)
                        played_state = True
                        break  # Prevent sound duplication if object has multiple states

            # --- Role-based sound -------------------------------------------
            if not played_state:
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
                        if not snd:
                            return

                self.handler.play(obj_info, snd)

        except Exception:
            return

    def getOrder(self, obj_info, parrole=None, chrole=None):
        """Determine first/last item in a list from pre-extracted dict."""
        if parrole is None:
            parrole = controlTypes.Role.LIST.value
        if chrole is None:
            chrole = controlTypes.Role.LISTITEM.value
        if obj_info.get("role") != chrole:
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

    @script(description=_("Rotates the global speech order format."))
    def script_rotateSpeechOrder(self, gesture):
        import config
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
        if focus.treeInterceptor is not None:
            if not focus.treeInterceptor.passThrough:
                focus = focus.treeInterceptor
        info = focus.makeTextInfo(textInfos.POSITION_CARET)
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
        import tones
        tones.beep(800, 100)
        tones.beep(1200, 100)

    @script(description=_("Audio Sonar: Sweeps the active window to create an audio map of its elements."), gestures=['kb:NVDA+Alt+r'])
    def script_audioSonar(self, gesture):
        obj = api.getForegroundObject()
        if not obj:
            return
            
        children = []
        def collect_children(root, depth=0):
            if depth > 3: return
            try:
                for child in root.children:
                    loc = child.location
                    if loc and loc[2] > 0 and loc[3] > 0:
                        children.append(child)
                    collect_children(child, depth + 1)
            except Exception as e:
                try:
                    from logHandler import log
                    log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
                except:
                    pass
        collect_children(obj)
        # sort by X coordinate
        children.sort(key=lambda c: c.location[0] if c.location else 0)
        
        snapshots = []
        for child in children:
            try:
                obj_info = self._snapshot_obj(child)
                # Force X pan based on screen position
                desktop = obj_info.get("desktop_location")
                if desktop and desktop[2] > 0:
                    loc = obj_info["location"]
                    c_x = loc[0] + (loc[2] / 2.0)
                    nx = (c_x / float(desktop[2])) - 0.5 # -0.5 to 0.5
                    obj_info["progress_angle"] = nx * 90.0 # -45 to 45
                snapshots.append(obj_info)
            except Exception as e:
                try:
                    from logHandler import log
                    log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
                except:
                    pass
        def sweep():
            import time
            for obj_info in snapshots:
                try:
                    self.playObject(obj_info)
                    time.sleep(0.04)
                except Exception as e:
                    try:
                        from logHandler import log
                        log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
                    except:
                        pass
        utils.threadPool.add_task(sweep)

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

    # Plain DownArrow/UpArrow → NVDA built-in line navigation (no override!)
    # ────────────────────────────────────────────────
