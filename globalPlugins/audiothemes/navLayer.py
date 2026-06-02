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
    Mixin to provide a navigation layer for cycling through various modes.
    """
    
    _ALL_MODES = [
        {"id": "character", "name": _("Character") if "_" in globals() else "Character", "type": "key", "prev": "leftArrow", "next": "rightArrow"},
        {"id": "word", "name": _("Word") if "_" in globals() else "Word", "type": "key", "prev": "control+leftArrow", "next": "control+rightArrow"},
        {"id": "line", "name": _("Lines") if "_" in globals() else "Lines", "type": "key", "prev": "upArrow", "next": "downArrow"},
        {"id": "sentence", "name": _("Sentence") if "_" in globals() else "Sentence", "type": "key", "prev": "alt+upArrow", "next": "alt+downArrow"},
        {"id": "paragraph", "name": _("Paragraph") if "_" in globals() else "Paragraph", "type": "key", "prev": "control+upArrow", "next": "control+downArrow"},
        {"id": "heading", "name": _("Headings") if "_" in globals() else "Headings", "type": "script", "prev": "script_previousHeading", "next": "script_nextHeading"},
        {"id": "link", "name": _("Links") if "_" in globals() else "Links", "type": "script", "prev": "script_previousLink", "next": "script_nextLink"},
        {"id": "unvisitedLink", "name": _("Unvisited links") if "_" in globals() else "Unvisited links", "type": "script", "prev": "script_previousUnvisitedLink", "next": "script_nextUnvisitedLink"},
        {"id": "visitedLink", "name": _("Visited links") if "_" in globals() else "Visited links", "type": "script", "prev": "script_previousVisitedLink", "next": "script_nextVisitedLink"},
        {"id": "formField", "name": _("Form fields") if "_" in globals() else "Form fields", "type": "script", "prev": "script_previousFormField", "next": "script_nextFormField"},
        {"id": "button", "name": _("Buttons") if "_" in globals() else "Buttons", "type": "script", "prev": "script_previousButton", "next": "script_nextButton"},
        {"id": "editField", "name": _("Edit fields") if "_" in globals() else "Edit fields", "type": "script", "prev": "script_previousEdit", "next": "script_nextEdit"},
        {"id": "checkBox", "name": _("Check boxes") if "_" in globals() else "Check boxes", "type": "script", "prev": "script_previousCheckBox", "next": "script_nextCheckBox"},
        {"id": "comboBox", "name": _("Combo boxes") if "_" in globals() else "Combo boxes", "type": "script", "prev": "script_previousComboBox", "next": "script_nextComboBox"},
        {"id": "radioButton", "name": _("Radio buttons") if "_" in globals() else "Radio buttons", "type": "script", "prev": "script_previousRadioButton", "next": "script_nextRadioButton"},
        {"id": "graphic", "name": _("Images") if "_" in globals() else "Images", "type": "script", "prev": "script_previousGraphic", "next": "script_nextGraphic"},
        {"id": "list", "name": _("Lists") if "_" in globals() else "Lists", "type": "script", "prev": "script_previousList", "next": "script_nextList"},
        {"id": "listItem", "name": _("List items") if "_" in globals() else "List items", "type": "script", "prev": "script_previousListItem", "next": "script_nextListItem"},
        {"id": "table", "name": _("Tables") if "_" in globals() else "Tables", "type": "script", "prev": "script_previousTable", "next": "script_nextTable"},
        {"id": "frame", "name": _("Frames") if "_" in globals() else "Frames", "type": "script", "prev": "script_previousFrame", "next": "script_nextFrame"},
        {"id": "article", "name": _("Articles") if "_" in globals() else "Articles", "type": "script", "prev": "script_previousArticle", "next": "script_nextArticle"},
        {"id": "landmark", "name": _("Landmarks") if "_" in globals() else "Landmarks", "type": "script", "prev": "script_previousLandmark", "next": "script_nextLandmark"},
        {"id": "separator", "name": _("Separators") if "_" in globals() else "Separators", "type": "script", "prev": "script_previousSeparator", "next": "script_nextSeparator"},
        {"id": "quote", "name": _("Quotes") if "_" in globals() else "Quotes", "type": "script", "prev": "script_previousBlockQuote", "next": "script_nextBlockQuote"},
        {"id": "object", "name": _("Objects") if "_" in globals() else "Objects", "type": "script", "prev": "script_previousEmbeddedObject", "next": "script_nextEmbeddedObject"},
        {"id": "textBlock", "name": _("text blocks") if "_" in globals() else "text blocks", "type": "script", "prev": "script_previousNotLinkBlock", "next": "script_nextNotLinkBlock"},
        {"id": "search", "name": _("Searches") if "_" in globals() else "Searches", "type": "script", "prev": "script_findPrevious", "next": "script_findNext"},
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._navLayerActive = False
        self._navLayerModeIndex = 0
        self._navLayerTimer = None
        self._activeModes = []
        
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

    def _loadActiveModes(self):
        nlConf = config.conf.get("audiothemes", {})
        import json
        try:
            enabled_ids = json.loads(nlConf.get("navLayerEnabledModes", "[]"))
        except Exception:
            enabled_ids = []
            
        if not enabled_ids:
            # Default fallback if nothing saved
            enabled_ids = [m["id"] for m in self._ALL_MODES]
            
        self._activeModes = [m for m in self._ALL_MODES if m["id"] in enabled_ids]
        if not self._activeModes:
            self._activeModes = [self._ALL_MODES[2]] # Fallback to Line

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

        self._loadActiveModes()
        self._navLayerActive = True
        
        # Try to default to Line or first mode
        self._navLayerModeIndex = 0
        for i, m in enumerate(self._activeModes):
            if m["id"] == "line":
                self._navLayerModeIndex = i
                break
                
        self.bindGestures(self._navLayerGestures)
        
        # Play enter sound
        tones.beep(600, 50)
        wx.CallLater(60, lambda: tones.beep(800, 50))
        
        mode = self._activeModes[self._navLayerModeIndex]
        ui.message(mode["name"])
        self._resetNavLayerTimer()

    @script(description="Next navigation mode.")
    def script_navLayerNextMode(self, gesture):
        if not self._activeModes: return
        self._navLayerModeIndex = (self._navLayerModeIndex + 1) % len(self._activeModes)
        tones.beep(1200, 30)
        ui.message(self._activeModes[self._navLayerModeIndex]["name"])

    @script(description="Previous navigation mode.")
    def script_navLayerPreviousMode(self, gesture):
        if not self._activeModes: return
        self._navLayerModeIndex = (self._navLayerModeIndex - 1) % len(self._activeModes)
        tones.beep(1000, 30)
        ui.message(self._activeModes[self._navLayerModeIndex]["name"])

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
        mode = self._activeModes[self._navLayerModeIndex]
        obj = api.getNavigatorObject()
        if not obj:
            return
        try:
            info = obj.makeTextInfo(api.textInfos.POSITION_CARET)
            m_id = mode["id"]
            if m_id == "word":
                info.expand(api.textInfos.UNIT_WORD)
            elif m_id == "line":
                info.expand(api.textInfos.UNIT_LINE)
            elif m_id == "sentence":
                info.expand(api.textInfos.UNIT_SENTENCE)
            elif m_id == "paragraph":
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
        if not self._activeModes: return
        mode = self._activeModes[self._navLayerModeIndex]
        
        if mode["type"] == "key":
            tones.beep(400, 20)
            key = mode["prev"] if direction == -1 else mode["next"]
            self._sendNormalKey(key)
            
        elif mode["type"] == "script":
            obj = api.getFocusObject()
            if not obj or not getattr(obj, "treeInterceptor", None):
                tones.beep(300, 100) # Error beep
                ui.message(_("Not supported here") if "_" in globals() else "Not supported here")
                return
            
            scriptName = mode["prev"] if direction == -1 else mode["next"]
            try:
                func = getattr(obj.treeInterceptor, scriptName)
                import scriptHandler
                tones.beep(400, 20)
                # Temporarily unbind to allow script to work properly
                self.clearGestureBindings()
                if hasattr(self, '_rebindInstanceGestures'):
                    self._rebindInstanceGestures()
                try:
                    scriptHandler.executeScript(func, None)
                finally:
                    if self._navLayerActive:
                        wx.CallLater(50, self.bindGestures, self._navLayerGestures)
            except AttributeError:
                tones.beep(300, 100) # Error beep
                ui.message(_("Not supported here") if "_" in globals() else "Not supported here")
