# coding: utf-8

import wx
import ui
import keyboardHandler
import api
import tones
import config
import threading
from scriptHandler import script
from globalCommands import commands
import addonHandler

try:
    addonHandler.initTranslation()
except AttributeError:
    pass

class NavLayerMixin:
    """
    Mixin to provide a navigation layer for cycling through modes:
    Character, Word, Line, Sentence, Paragraph, Heading, Link, Form Field.
    """
    
    _navLayerModes = [
        _("Character") if "_" in globals() else "Character",
        _("Word") if "_" in globals() else "Word",
        _("Line") if "_" in globals() else "Line",
        _("Sentence") if "_" in globals() else "Sentence",
        _("Paragraph") if "_" in globals() else "Paragraph",
        _("Heading") if "_" in globals() else "Heading",
        _("Link") if "_" in globals() else "Link",
        _("Form Field") if "_" in globals() else "Form Field"
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._navLayerActive = False
        self._navLayerModeIndex = 0
        self._navLayerTimer = None
        
        self._navLayerGestures = {
            "kb:leftArrow": "navLayerPreviousMode",
            "kb:rightArrow": "navLayerNextMode",
            "kb:upArrow": "navLayerMovePrevious",
            "kb:downArrow": "navLayerMoveNext",
            "kb:escape": "navLayerExit",
            "kb:c": "navLayerCopy",
            "kb:s": "navLayerSpell",
            "kb:r": "navLayerReadAll"
        }

    def getScript(self, gesture):
        if self._navLayerActive:
            script_func = super().getScript(gesture)
            # If the script isn't one of our layer scripts and pass-through is enabled, auto-exit
            nlConf = config.conf.get("audiothemes", {})
            passThrough = nlConf.get("navLayerPassThrough", True)
            
            if not script_func or not getattr(script_func, "__name__", "").startswith("script_navLayer"):
                if passThrough:
                    self._doNavLayerExit()
                    # Return the normal script for this gesture (since layer is now inactive)
                    return super().getScript(gesture)
                else:
                    # If pass-through is disabled, we block all other keys by returning a dummy script
                    def dummy_script(gesture):
                        pass
                    return dummy_script
            else:
                self._resetNavLayerTimer()
                
        return super().getScript(gesture)

    def _resetNavLayerTimer(self):
        nlConf = config.conf.get("audiothemes", {})
        timeoutEnabled = nlConf.get("navLayerTimeout", True)
        
        if self._navLayerTimer:
            self._navLayerTimer.cancel()
            self._navLayerTimer = None
            
        if timeoutEnabled:
            self._navLayerTimer = threading.Timer(10.0, self._onNavLayerTimeoutThread)
            self._navLayerTimer.start()

    def _onNavLayerTimeoutThread(self):
        wx.CallAfter(self._onNavLayerTimeout)

    def _onNavLayerTimeout(self):
        if self._navLayerActive:
            self._doNavLayerExit()

    @script(description=_("Enters the navigation layer to move by various text and web units.") if "_" in globals() else "Enters the navigation layer.", gestures=["kb:NVDA+windows+n"])
    def script_navigationLayer(self, gesture):
        if self._navLayerActive:
            self._doNavLayerExit()
            return

        self._navLayerActive = True
        self._navLayerModeIndex = 2  # Default to Line
        self.bindGestures(self._navLayerGestures)
        
        # Play enter sound
        tones.beep(600, 50)
        wx.CallLater(60, lambda: tones.beep(800, 50))
        
        mode_name = self._navLayerModes[self._navLayerModeIndex]
        ui.message(f"{mode_name}")
        self._resetNavLayerTimer()

    @script(description="Next navigation mode.")
    def script_navLayerNextMode(self, gesture):
        self._navLayerModeIndex = (self._navLayerModeIndex + 1) % len(self._navLayerModes)
        tones.beep(1200, 30)
        ui.message(self._navLayerModes[self._navLayerModeIndex])

    @script(description="Previous navigation mode.")
    def script_navLayerPreviousMode(self, gesture):
        self._navLayerModeIndex = (self._navLayerModeIndex - 1) % len(self._navLayerModes)
        tones.beep(1000, 30)
        ui.message(self._navLayerModes[self._navLayerModeIndex])

    @script(description="Move to previous unit in navigation layer.")
    def script_navLayerMovePrevious(self, gesture):
        self._performNavAction(direction=-1)

    @script(description="Move to next unit in navigation layer.")
    def script_navLayerMoveNext(self, gesture):
        self._performNavAction(direction=1)

    @script(description="Copy current unit.")
    def script_navLayerCopy(self, gesture):
        tones.beep(1500, 40)
        self._sendNormalKey("control+c")

    @script(description="Spell current unit.")
    def script_navLayerSpell(self, gesture):
        tones.beep(1500, 40)
        mode = self._navLayerModeIndex
        obj = api.getNavigatorObject()
        if not obj:
            return
        try:
            info = obj.makeTextInfo(api.textInfos.POSITION_CARET)
            if mode == 1:
                info.expand(api.textInfos.UNIT_WORD)
            elif mode == 2:
                info.expand(api.textInfos.UNIT_LINE)
            elif mode == 3:
                info.expand(api.textInfos.UNIT_SENTENCE)
            elif mode == 4:
                info.expand(api.textInfos.UNIT_PARAGRAPH)
            else:
                info.expand(api.textInfos.UNIT_WORD) # default fallback
                
            text = info.text
            import speech
            speech.speakText(text, symbolLevel=speech.symbolLevel.ALL)
            import speech.spelling
            for char in text:
                speech.spelling.spellCharacter(char)
        except Exception:
            pass

    @script(description="Read All.")
    def script_navLayerReadAll(self, gesture):
        self._doNavLayerExit()
        # NVDA Read All
        self._sendNormalKey("NVDA+downArrow")

    @script(description="Exit navigation layer.")
    def script_navLayerExit(self, gesture):
        self._doNavLayerExit()

    def _doNavLayerExit(self):
        if not self._navLayerActive: return
        self._navLayerActive = False
        if self._navLayerTimer:
            self._navLayerTimer.cancel()
            self._navLayerTimer = None
            
        self.clearGestureBindings()
        if hasattr(self, '_rebindInstanceGestures'):
            self._rebindInstanceGestures()
        
        tones.beep(800, 50)
        wx.CallLater(60, lambda: tones.beep(600, 50))
        ui.message(_("Exited navigation layer") if "_" in globals() else "Exited navigation layer")

    def _sendNormalKey(self, keyName):
        import inputCore
        gest = keyboardHandler.KeyboardInputGesture.fromName(keyName)
        self.clearGestureBindings()
        if hasattr(self, '_rebindInstanceGestures'):
            self._rebindInstanceGestures()
        try:
            inputCore.manager.executeGesture(gest)
        finally:
            if self._navLayerActive:
                wx.CallLater(50, self.bindGestures, self._navLayerGestures)

    def _performNavAction(self, direction):
        tones.beep(400, 20)
        mode = self._navLayerModeIndex
        
        # 0: Character
        if mode == 0:
            key = "leftArrow" if direction == -1 else "rightArrow"
        # 1: Word
        elif mode == 1:
            key = "control+leftArrow" if direction == -1 else "control+rightArrow"
        # 2: Line
        elif mode == 2:
            key = "upArrow" if direction == -1 else "downArrow"
        # 3: Sentence
        elif mode == 3:
            key = "alt+upArrow" if direction == -1 else "alt+downArrow"
        # 4: Paragraph
        elif mode == 4:
            key = "control+upArrow" if direction == -1 else "control+downArrow"
        # 5: Heading
        elif mode == 5:
            key = "shift+h" if direction == -1 else "h"
        # 6: Link
        elif mode == 6:
            key = "shift+k" if direction == -1 else "k"
        # 7: Form Field
        elif mode == 7:
            key = "shift+f" if direction == -1 else "f"
        else:
            return

        self._sendNormalKey(key)

