# coding: utf-8

import wx
import ui
import keyboardHandler
import api
import tones
import config
import threading
import winUser
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
    
    def _get_nl_cache(self):
        return getattr(getattr(self, 'handler', None), '_cached_config', None) or {}

    def _playNavTone(self, pitch, duration):
        nlConf = self._get_nl_cache()
        if nlConf.get("navLayerPlaySounds", True):
            import tones
            tones.beep(pitch, duration)

    _ALL_MODES = [
        {"id": "character", "name": _("Character") if "_" in globals() else "Character", "type": "key", "prev": "leftArrow", "next": "rightArrow"},
        {"id": "word", "name": _("Word") if "_" in globals() else "Word", "type": "key", "prev": "control+leftArrow", "next": "control+rightArrow"},
        {"id": "line", "name": _("Lines") if "_" in globals() else "Lines", "type": "key", "prev": "upArrow", "next": "downArrow"},
        {"id": "sentence", "name": _("Sentence") if "_" in globals() else "Sentence", "type": "key", "prev": "alt+upArrow", "next": "alt+downArrow"},
        {"id": "paragraph", "name": _("Paragraph") if "_" in globals() else "Paragraph", "type": "key", "prev": "control+upArrow", "next": "control+downArrow"},
        {"id": "heading", "name": _("Headings") if "_" in globals() else "Headings", "type": "vk", "vk": ord('H')},
        {"id": "link", "name": _("Links") if "_" in globals() else "Links", "type": "vk", "vk": ord('K')},
        {"id": "unvisitedLink", "name": _("Unvisited links") if "_" in globals() else "Unvisited links", "type": "vk", "vk": ord('U')},
        {"id": "visitedLink", "name": _("Visited links") if "_" in globals() else "Visited links", "type": "vk", "vk": ord('V')},
        {"id": "formField", "name": _("Form fields") if "_" in globals() else "Form fields", "type": "vk", "vk": ord('F')},
        {"id": "button", "name": _("Buttons") if "_" in globals() else "Buttons", "type": "vk", "vk": ord('B')},
        {"id": "editField", "name": _("Edit fields") if "_" in globals() else "Edit fields", "type": "vk", "vk": ord('E')},
        {"id": "checkBox", "name": _("Check boxes") if "_" in globals() else "Check boxes", "type": "vk", "vk": ord('X')},
        {"id": "comboBox", "name": _("Combo boxes") if "_" in globals() else "Combo boxes", "type": "vk", "vk": ord('C')},
        {"id": "radioButton", "name": _("Radio buttons") if "_" in globals() else "Radio buttons", "type": "vk", "vk": ord('R')},
        {"id": "graphic", "name": _("Images") if "_" in globals() else "Images", "type": "vk", "vk": ord('G')},
        {"id": "list", "name": _("Lists") if "_" in globals() else "Lists", "type": "vk", "vk": ord('L')},
        {"id": "listItem", "name": _("List items") if "_" in globals() else "List items", "type": "vk", "vk": ord('I')},
        {"id": "table", "name": _("Tables") if "_" in globals() else "Tables", "type": "vk", "vk": ord('T')},
        {"id": "frame", "name": _("Frames") if "_" in globals() else "Frames", "type": "vk", "vk": ord('M')},
        {"id": "article", "name": _("Articles") if "_" in globals() else "Articles", "type": "vk", "vk": ord('A')},
        {"id": "landmark", "name": _("Landmarks") if "_" in globals() else "Landmarks", "type": "vk", "vk": ord('D')},
        {"id": "separator", "name": _("Separators") if "_" in globals() else "Separators", "type": "vk", "vk": ord('S')},
        {"id": "quote", "name": _("Quotes") if "_" in globals() else "Quotes", "type": "vk", "vk": ord('Q')},
        {"id": "object", "name": _("Objects") if "_" in globals() else "Objects", "type": "vk", "vk": ord('O')},
        {"id": "textBlock", "name": _("text blocks") if "_" in globals() else "text blocks", "type": "vk", "vk": ord('N')},
        {"id": "search", "name": _("Searches") if "_" in globals() else "Searches", "type": "vk", "vk": 114}, # VK_F3
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._navLayerActive = False
        self._suppressAllGestures = False
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
        }

    def _loadActiveModes(self):
        nlConf = self._get_nl_cache()
        import json
        try:
            enabled_ids = json.loads(nlConf.get("navLayerEnabledModes", "[]"))
        except Exception:
            enabled_ids = []
            
        if not enabled_ids:
            enabled_ids = [m["id"] for m in self._ALL_MODES]
            
        self._activeModes = [m for m in self._ALL_MODES if m["id"] in enabled_ids]
        if not self._activeModes:
            self._activeModes = [self._ALL_MODES[2]] # Fallback to Line

    def getScript(self, gesture):
        if self._suppressAllGestures:
            return None
        if self._navLayerActive:
            script_func = super().getScript(gesture)
            nlConf = self._get_nl_cache()
            passThrough = nlConf.get("navLayerPassThrough", True)
            
            if not script_func or not getattr(script_func, "__name__", "").startswith("script_navLayer"):
                if passThrough:
                    wx.CallAfter(self._doNavLayerExit)
                    return super().getScript(gesture)
                else:
                    self._resetNavLayerTimer()
                    def dummy_script(gesture):
                        pass
                    return dummy_script
            else:
                self._resetNavLayerTimer()
                
        return super().getScript(gesture)

    def _resetNavLayerTimer(self):
        nlConf = self._get_nl_cache()
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
        
        self._navLayerModeIndex = 0
        for i, m in enumerate(self._activeModes):
            if m["id"] == "line":
                self._navLayerModeIndex = i
                break
                
        self.bindGestures(self._navLayerGestures)
        
        self._playNavTone(600, 50)
        wx.CallLater(60, lambda: self._playNavTone(800, 50))
        
        mode = self._activeModes[self._navLayerModeIndex]
        ui.message(mode["name"])
        self._resetNavLayerTimer()

    @script(description="Next navigation mode.")
    def script_navLayerNextMode(self, gesture):
        if not self._activeModes: return
        self._navLayerModeIndex = (self._navLayerModeIndex + 1) % len(self._activeModes)
        self._playNavTone(1200, 30)
        ui.message(self._activeModes[self._navLayerModeIndex]["name"])

    @script(description="Previous navigation mode.")
    def script_navLayerPreviousMode(self, gesture):
        if not self._activeModes: return
        self._navLayerModeIndex = (self._navLayerModeIndex - 1) % len(self._activeModes)
        self._playNavTone(1000, 30)
        ui.message(self._activeModes[self._navLayerModeIndex]["name"])

    @script(description="Move to previous unit in navigation layer.")
    def script_navLayerMovePrevious(self, gesture):
        self._performNavAction(direction=-1)

    @script(description="Move to next unit in navigation layer.")
    def script_navLayerMoveNext(self, gesture):
        self._performNavAction(direction=1)

    @script(description="Copy current unit.")
    def script_navLayerCopy(self, gesture):
        self._playNavTone(1500, 40)
        text = self._getCurrentUnitText()
        if text:
            import wx
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(text))
                wx.TheClipboard.Close()
            ui.message(_("Copied") if "_" in globals() else "Copied")

    def _getCurrentUnitText(self):
        try:
            if not self._activeModes:
                self._loadActiveModes()
            mode = self._activeModes[self._navLayerModeIndex]
            obj = api.getNavigatorObject()
            if not obj:
                return None
            m_id = mode["id"]
            if m_id == "sentence":
                from .sentenceNavEngine import getCaretIndexWithinParagraph, Context, getRegex, getCurrentLanguage
                focus = obj
                if hasattr(obj, "treeInterceptor") and obj.treeInterceptor is not None and hasattr(obj.treeInterceptor, "makeTextInfo"):
                    focus = obj.treeInterceptor
                caretInfo = focus.makeTextInfo(api.textInfos.POSITION_CARET)
                caretIndex, paragraphInfo = getCaretIndexWithinParagraph(caretInfo)
                context = Context(paragraphInfo, caretIndex, caretInfo)
                regex = getRegex(getCurrentLanguage())
                sentenceStr, _, _, _, _ = self.expandSentence(context, regex, 0)
                return sentenceStr
            focus = obj
            if hasattr(obj, "treeInterceptor") and obj.treeInterceptor is not None and hasattr(obj.treeInterceptor, "makeTextInfo"):
                focus = obj.treeInterceptor
            info = focus.makeTextInfo(api.textInfos.POSITION_CARET)
            if m_id == "word":
                info.expand(api.textInfos.UNIT_WORD)
            elif m_id == "line":
                info.expand(api.textInfos.UNIT_LINE)
            elif m_id == "paragraph":
                info.expand(api.textInfos.UNIT_PARAGRAPH)
            else:
                info.expand(api.textInfos.UNIT_WORD)
            return info.text
        except Exception:
            return None

    @script(description="Spell current unit.")
    def script_navLayerSpell(self, gesture):
        self._playNavTone(1500, 40)
        text = self._getCurrentUnitText()
        if text:
            import speech
            speech.speakText(text)
            speech.speakSpelling(text)

    @script(description="Exit navigation layer.")
    def script_navLayerExit(self, gesture):
        self._doNavLayerExit()

    def _doNavLayerExit(self):
        if not self._navLayerActive: return
        self._navLayerActive = False
        if self._navLayerTimer:
            self._navLayerTimer.cancel()
            self._navLayerTimer = None
            
        for ident in self._navLayerGestures:
            try:
                self.removeGestureBinding(ident)
            except (LookupError, ValueError):
                pass
        
        from speech.sayAll import SayAllHandler
        SayAllHandler.stop()
        self._playNavTone(800, 50)
        wx.CallAfter(wx.CallLater, 60, lambda: self._playNavTone(600, 50))
        ui.message(_("Exited navigation layer") if "_" in globals() else "Exited navigation layer")

    def _sendNormalKey(self, keyName):
        import inputCore
        try:
            gest = keyboardHandler.KeyboardInputGesture.fromName(keyName)
        except LookupError:
            self._playNavTone(300, 100)
            return
            
        self._navLayerActive = False
        try:
            from .browserNavEngine import originalExecuteGesture
            originalExecuteGesture(inputCore.manager, gest)
        except inputCore.NoInputGestureAction:
            self._playNavTone(300, 100)
        finally:
            from speech.sayAll import SayAllHandler
            SayAllHandler.stop()
            self._navLayerActive = True

    def _sendVKKey(self, vk, shift=False):
        import inputCore
        import winUser
        modifiers = set()
        if shift:
            modifiers.add((winUser.VK_SHIFT, False))
            
        gest = keyboardHandler.KeyboardInputGesture(modifiers, vk, 0, False)
        
        self._navLayerActive = False
        try:
            from .browserNavEngine import originalExecuteGesture
            originalExecuteGesture(inputCore.manager, gest)
        except inputCore.NoInputGestureAction:
            self._playNavTone(300, 100)
        finally:
            from speech.sayAll import SayAllHandler
            SayAllHandler.stop()
            self._navLayerActive = True

    def _performNavAction(self, direction):
        if not self._activeModes: return
        mode = self._activeModes[self._navLayerModeIndex]
        
        if mode["type"] == "key":
            self._playNavTone(400, 20)
            key = mode["prev"] if direction == -1 else mode["next"]
            self._sendNormalKey(key)
            
        elif mode["type"] == "vk":
            obj = api.getFocusObject()
            ti = getattr(obj, "treeInterceptor", None)
            
            # If we are not inside a valid treeInterceptor or passThrough is True (Browse Mode is OFF)
            if not ti or getattr(ti, "passThrough", True):
                self._playNavTone(300, 100) # Error beep
                ui.message(_("Not supported here") if "_" in globals() else "Not supported here")
                return
                
            self._playNavTone(400, 20)
            vk = mode["vk"]
            shift = (direction == -1)
            self._sendVKKey(vk, shift=shift)
