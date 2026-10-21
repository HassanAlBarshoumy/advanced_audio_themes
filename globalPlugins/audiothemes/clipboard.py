# coding: utf-8

# This file is covered by the GNU General Public License.

import json
import wx
import ui

from .handler import SpecialProps

import addonHandler
from logHandler import log
try:
    addonHandler.initTranslation()
except AttributeError:
    log.debug("AudioThemes: swallowed AttributeError in clipboard")
try:
    _(u"")
except NameError:
    def _(s):
        return s


# action_id -> (SpecialProps member, config_key, default_speech_source)
ACTION_MAP = {
    "copy": (SpecialProps.clipboard_copy, "clipboard_copy", "Copied to clipboard"),
    "cut": (SpecialProps.clipboard_cut, "clipboard_cut", "Cut to clipboard"),
    "paste": (SpecialProps.clipboard_paste, "clipboard_paste", "Pasted from clipboard"),
    "selectall": (SpecialProps.clipboard_selectall, "clipboard_selectall", "All selected"),
    "undo": (SpecialProps.clipboard_undo, "clipboard_undo", "Undone"),
    "redo": (SpecialProps.clipboard_redo, "clipboard_redo", "Redone"),
    "pasteplain": (SpecialProps.clipboard_pasteplain, "clipboard_pasteplain", "Pasted as plain text"),
    "redo2": (SpecialProps.clipboard_redo2, "clipboard_redo2", "Redone"),
}


class ClipboardManager:
    def __init__(self, handler):
        self._handler = handler
        self._cached_custom_texts = {}
        self._cached_custom_texts_raw = None
        self._announce_timer = None

    def _clip_conf(self):
        return getattr(self._handler, '_cached_config', None) or {}

    def terminate(self):
        """Cancel a pending delayed announcement (called on plugin unload)."""
        if self._announce_timer is not None:
            try:
                self._announce_timer.Stop()
            except Exception:
                log.debug("AudioThemes: swallowed Exception in clipboard.terminate")
            self._announce_timer = None

    def announce(self, action_id):
        conf = self._clip_conf()
        if not conf.get("clipboard_enabled", True):
            return
        entry = ACTION_MAP.get(action_id)
        if entry is None:
            return
        special_prop, config_key, default_speech = entry
        if not conf.get(config_key, True):
            return
        delay = conf.get("clipboard_delay", 50)
        if delay > 0:
            self.terminate()
            self._announce_timer = wx.CallLater(
                delay, self._do_announce, action_id, special_prop, config_key, default_speech
            )
        else:
            self._do_announce(action_id, special_prop, config_key, default_speech)

    def _do_announce(self, action_id, special_prop, config_key, default_speech):
        self._announce_timer = None
        if getattr(self._handler, "_closed", False):
            return
        conf = self._clip_conf()
        mode = conf.get("clipboard_announce_mode", "both")
        play_sound = mode in ("sound", "both") and conf.get(config_key + "_sound", True)
        speak = mode in ("speech", "both") and conf.get(config_key + "_speech", True)
        if play_sound:
            self._handler.play_clipboard_sound(special_prop)
        if speak:
            raw = conf.get("clipboard_custom_texts", "{}")
            if raw != self._cached_custom_texts_raw:
                self._cached_custom_texts_raw = raw
                try:
                    self._cached_custom_texts = json.loads(raw) if isinstance(raw, str) else raw
                except Exception:
                    self._cached_custom_texts = {}
            text = self._cached_custom_texts.get(action_id, _(default_speech))
            ui.message(text)
