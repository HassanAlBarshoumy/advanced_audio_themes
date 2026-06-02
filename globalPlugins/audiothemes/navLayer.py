# coding: utf-8

import ui
import keyboardHandler
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
    Line, Paragraph, Sentence, Word.
    """
    
    _navLayerModes = [
        _("Line") if "_" in globals() else "Line",
        _("Paragraph") if "_" in globals() else "Paragraph",
        _("Sentence") if "_" in globals() else "Sentence",
        _("Word") if "_" in globals() else "Word"
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._navLayerActive = False
        self._navLayerModeIndex = 0
        
        self._navLayerGestures = {
            "kb:leftArrow": "navLayerPreviousMode",
            "kb:rightArrow": "navLayerNextMode",
            "kb:upArrow": "navLayerMovePrevious",
            "kb:downArrow": "navLayerMoveNext",
            "kb:escape": "navLayerExit"
        }

    @script(description=_("Enters the navigation layer to move by line, paragraph, sentence, or word.") if "_" in globals() else "Enters the navigation layer.", gestures=["kb:NVDA+windows+n"])
    def script_navigationLayer(self, gesture):
        if self._navLayerActive:
            self.script_navLayerExit(gesture)
            return

        self._navLayerActive = True
        self._navLayerModeIndex = 0  # Default to Line
        self.bindGestures(self._navLayerGestures)
        
        mode_name = self._navLayerModes[self._navLayerModeIndex]
        # In Arabic: "وضع التنقل: سطر"
        ui.message(f"Navigation mode: {mode_name}")

    @script(description="Next navigation mode.")
    def script_navLayerNextMode(self, gesture):
        self._navLayerModeIndex = (self._navLayerModeIndex + 1) % len(self._navLayerModes)
        ui.message(self._navLayerModes[self._navLayerModeIndex])

    @script(description="Previous navigation mode.")
    def script_navLayerPreviousMode(self, gesture):
        self._navLayerModeIndex = (self._navLayerModeIndex - 1) % len(self._navLayerModes)
        ui.message(self._navLayerModes[self._navLayerModeIndex])

    @script(description="Move to previous unit in navigation layer.")
    def script_navLayerMovePrevious(self, gesture):
        self._performNavAction(direction=-1)

    @script(description="Move to next unit in navigation layer.")
    def script_navLayerMoveNext(self, gesture):
        self._performNavAction(direction=1)

    @script(description="Exit navigation layer.")
    def script_navLayerExit(self, gesture):
        self._navLayerActive = False
        self.clearGestureBindings()
        # Restore standard instance gestures (like sentenceNav etc)
        if hasattr(self, '_rebindInstanceGestures'):
            self._rebindInstanceGestures()
        
        ui.message(_("Exited navigation layer") if "_" in globals() else "Exited navigation layer")

    def _performNavAction(self, direction):
        """
        Simulates standard NVDA shortcut keys depending on the current mode.
        direction: -1 for previous/up, 1 for next/down
        """
        mode = self._navLayerModeIndex
        
        # 0: Line
        if mode == 0:
            key = "upArrow" if direction == -1 else "downArrow"
        # 1: Paragraph
        elif mode == 1:
            key = "control+upArrow" if direction == -1 else "control+downArrow"
        # 2: Sentence (using SentenceNav shortcuts, which are alt+up/alt+down)
        elif mode == 2:
            key = "alt+upArrow" if direction == -1 else "alt+downArrow"
        # 3: Word
        elif mode == 3:
            key = "control+leftArrow" if direction == -1 else "control+rightArrow"
        else:
            return

        import inputCore
        gest = keyboardHandler.KeyboardInputGesture.fromName(key)

        # Temporarily clear layer bindings to avoid infinite loop when sending up/down arrows
        self.clearGestureBindings()
        if hasattr(self, '_rebindInstanceGestures'):
            self._rebindInstanceGestures()
            
        try:
            # Execute through NVDA so that the normal script is triggered
            inputCore.manager.executeGesture(gest)
        finally:
            # Rebind after a short delay to allow any queued asynchronous gesture execution 
            # (e.g. from NVDAExtensionGlobalPlugin) to process first.
            import wx
            wx.CallLater(50, self.bindGestures, self._navLayerGestures)
