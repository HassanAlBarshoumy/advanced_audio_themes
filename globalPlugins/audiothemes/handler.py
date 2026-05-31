# coding: utf-8


# This file is covered by the GNU General Public License.

from enum import IntEnum
from collections import OrderedDict
from dataclasses import dataclass, field, asdict
from zipfile import ZipFile, ZIP_DEFLATED
from uuid import uuid4
import os
import ctypes
import shutil
import copy
import json
import threading
import config
import controlTypes
import extensionPoints
from config import post_configSave, post_configReset, post_configProfileSwitch
from .unspoken import UnspokenPlayer
import globalVars

import NVDAObjects

import speech
from speech.sayAll import SayAllHandler

import addonHandler
from logHandler import log
try:
    addonHandler.initTranslation()
except AttributeError:
    pass

THEMES_DIR = os.path.join(globalVars.appArgs.configPath, "audio-themes")
INFO_FILE_NAME = "info.json"
SUPPORTED_FILE_TYPES = OrderedDict()
# Translators: The file type to be shown in a dialog used to browse for audio files.
SUPPORTED_FILE_TYPES["ogg"] = _("Ogg audio files")
# Translators: The file type to be shown in a dialog used to browse for audio files.
SUPPORTED_FILE_TYPES["wav"] = _("Wave audio files")
# Translators: The file type to be shown in a dialog used to browse for audio files.
SUPPORTED_FILE_TYPES["mp3"] = _("MPEG audio files")
# Translators: The file type to be shown in a dialog used to browse for audio files.
SUPPORTED_FILE_TYPES["flac"] = _("FLAC audio files")
# Translators: The file type to be shown in a dialog used to browse for audio files.
SUPPORTED_FILE_TYPES["m4a"] = _("AAC/M4A audio files")
# Translators: The file type to be shown in a dialog used to browse for audio files.
SUPPORTED_FILE_TYPES["aac"] = _("AAC audio files")
# Translators: The file type to be shown in a dialog used to browse for audio files.
SUPPORTED_FILE_TYPES["opus"] = _("Opus audio files")
# Translators: The file type to be shown in a dialog used to browse for audio files.
SUPPORTED_FILE_TYPES["wma"] = _("WMA audio files")
# Translators: The file type to be shown in a dialog used to browse for audio files.
SUPPORTED_FILE_TYPES["mp2"] = _("MP2 audio files")
# Translators: The file type to be shown in a dialog used to browse for audio files.
SUPPORTED_FILE_TYPES["ac3"] = _("AC3 audio files")

# Additional formats supported natively (without FFmpeg)
NATIVE_FORMATS = {"ogg", "wav", "mp3", "flac"}
# Formats that require FFmpeg
FFMPEG_ONLY_FORMATS = {"m4a", "aac", "opus", "wma", "mp2", "ac3"}

def get_active_file_types():
    try:
        from config import conf
        if conf.get("audiothemes", {}).get("enable_ffmpeg", False):
            return SUPPORTED_FILE_TYPES
    except Exception:
        pass
    return OrderedDict((k, v) for k, v in SUPPORTED_FILE_TYPES.items() if k in NATIVE_FORMATS)
# When the active audio theme is being changed
audiotheme_changed = extensionPoints.Action()

# Configuration spec
audiothemes_config_defaults = {
    "enable_audio_themes": "boolean(default=    True)",
    "active_theme": 'string(default="Default")',
    "audio3d": "boolean(default=False)",
    "use_in_say_all": "boolean(default=True)",
    "speak_roles": "boolean(default=True)",
    "use_synth_volume": "boolean(default=False)",
    "volume": "integer(default=20)",
    "migrated_to_named_files": "boolean(default=False)",
    "disabled_apps": "string(default='')",
    "default_theme_deleted": "boolean(default=False)",
    "blacklisted_roles": "string(default='[19]')",
    "typing_sounds": "boolean(default=True)",
    "typing_sounds_edit_only": "boolean(default=True)",
    "typing_sounds_volume": "integer(default=10)",
    "typing_sound_pack": "string(default='1blueSwitch')",
    "typing_sounds_spatial": "boolean(default=True)",
    "typing_sounds_spatial_smart": "boolean(default=True)",
    "announceFormat": "string(default='0')",
    "roleAnnounceFormats": "string(default='{\"5\": \"sc\"}')",
    "app_profiles": "string(default='{}')",
    "audio_ducking_enabled": "boolean(default=False)",
    "audio_ducking_volume": "integer(default=6)",
    "output_mode": "string(default='stereo')",
    "ffmpeg_path": "string(default='')",
    "enable_ffmpeg": "boolean(default=False)",
    "dont_show_conflicts": "boolean(default=False)",
    "ducking_categories": "string(default='{\"theme_sounds\":true,\"typing_sounds\":true,\"earcons\":true,\"browsernav\":true,\"sentencenav\":true,\"textnav\":true,\"ui_beeps\":true}')",
    "disabled_apps_suppress_categories": "string(default='{\"theme_sounds\":true,\"typing_sounds\":true,\"earcons\":true,\"browsernav\":true,\"sentencenav\":true,\"textnav\":true,\"ui_beeps\":true}')",
    "check_for_updates_auto": "boolean(default=True)",
    "check_for_updates_prerelease": "boolean(default=False)",
}


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


class SpecialProps(IntEnum):
    """Represents sounds defined by this addon."""

    protected = 2500
    first = 2501
    last = 2502
    notify = 2503
    loaded = 2504


theme_roles = copy.copy(controlTypes.roleLabels)
theme_roles.update(
    {
        # Translators: The label of the sound which will be played when focusing a protected edit control.
        SpecialProps.protected: _("Protected Edit Field"),
        # Translators: The label of the sound which will be played when focusing the first item in a list.
        SpecialProps.first: _("First Item"),
        # Translators: The label of the sound which will be played when focusing the last item in a list.
        SpecialProps.last: _("Last Item"),
        # Translators: The label of the sound which will be played when a help balloon or a toast is shown.
        SpecialProps.notify: _("New Notification Sound"),
        # Translators: The label of the sound which will be played when a web page is loaded.
        SpecialProps.loaded: _("Web Page Loaded"),
    }
)

role_int_to_name = {}
if hasattr(controlTypes, "Role"):
    for member in controlTypes.Role:
        role_int_to_name[member.value] = member.name.lower()
else:
    for name, value in vars(controlTypes).items():
        if name.startswith("ROLE_"):
            role_int_to_name[value] = name.replace("ROLE_", "").lower()

role_name_to_int = {v: k for k, v in role_int_to_name.items()}

STATE_OFFSET = 10000
state_int_to_name = {}
if hasattr(controlTypes, "State"):
    for member in controlTypes.State:
        state_int_to_name[member.value] = member.name.lower()
else:
    for name, value in vars(controlTypes).items():
        if name.startswith("STATE_"):
            state_int_to_name[value] = name.replace("STATE_", "").lower()
state_name_to_int = {v: k for k, v in state_int_to_name.items()}

for state_val, state_label in getattr(controlTypes, "stateLabels", {}).items():
    theme_roles[state_val + STATE_OFFSET] = state_label

# Ensure ALL roles are in theme_roles, even if missing from roleLabels
for val, name in role_int_to_name.items():
    if val not in theme_roles:
        theme_roles[val] = name.replace("_", " ").title()

# Ensure ALL states are in theme_roles, even if missing from stateLabels
for val, name in state_int_to_name.items():
    if (val + STATE_OFFSET) not in theme_roles:
        theme_roles[val + STATE_OFFSET] = f"State: {name.replace('_', ' ').title()}"

for member in SpecialProps:
    role_int_to_name[member.value] = member.name

role_name_to_int = {v: k for k, v in role_int_to_name.items()}


@dataclass(order=True)
class AudioTheme:
    name: str
    directory: str
    author: str
    summary: str
    is_active: bool = False
    sounds: dict = field(default_factory=dict)
    available_files: set = field(default_factory=set)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    @property
    def info_file_path(self):
        return os.path.join(self.directory, INFO_FILE_NAME)

    @property
    def folder(self):
        return os.path.split(self.directory)[-1]

    def exists(self):
        return os.path.isdir(self.directory)

    def todict(self):
        return {
            "name": self.name,
            "author": self.author,
            "summary": self.summary
        }

    _STAPLE_ROLES = (
        controlTypes.Role.LISTITEM,
        controlTypes.Role.BUTTON,
        controlTypes.Role.CHECKBOX,
        controlTypes.Role.RADIOBUTTON,
        controlTypes.Role.TREEVIEWITEM,
        controlTypes.Role.EDITABLETEXT,
        controlTypes.Role.COMBOBOX,
        controlTypes.Role.TAB,
        controlTypes.Role.SLIDER,
        SpecialProps.first,
        SpecialProps.last,
    )

    def _auto_create_missing_sounds(self, new_sounds, available, player):
        created = 0
        for target_role in self._STAPLE_ROLES:
            if target_role in new_sounds:
                continue
            if not new_sounds:
                return created
            src_role = next(iter(new_sounds))
            src_obj = new_sounds[src_role]
            src_path = src_obj.get("path") if isinstance(src_obj, dict) else getattr(src_obj, 'path', None)
            if not src_path or not os.path.isfile(src_path):
                continue
            _, ext = os.path.splitext(src_path)
            name = role_int_to_name.get(target_role, str(target_role.value if hasattr(target_role, 'value') else target_role))
            dst = os.path.join(self.directory, f"{name}{ext}")
            try:
                import shutil
                shutil.copy2(src_path, dst)
            except Exception:
                continue
            available.add(f"{name}{ext}".lower())
            new_sounds[target_role] = player.make_sound_object(dst)
            created += 1
        return created

    def load(self, player):
        with self._lock:
            if self.sounds:
                self.sounds.clear()
            if hasattr(self, 'available_files'):
                self.available_files.clear()
            else:
                self.available_files = set()
        if not os.path.isdir(self.directory):
            return
        new_sounds = {}
        available = set()
        for filename in os.listdir(self.directory):
            available.add(filename.lower())
            path = os.path.join(self.directory, filename)
            rep_role = self.is_valid_audio_file(path)
            if rep_role is not None:
                new_sounds[rep_role] = player.make_sound_object(path)
        self._auto_create_missing_sounds(new_sounds, available, player)
        with self._lock:
            self.sounds = new_sounds
            self.available_files = available

    def unload(self):
        with self._lock:
            self.sounds.clear()

    def deactivate(self):
        """Deactivate this theme"""
        self.unload()
        self.is_active = False

    @staticmethod
    def is_valid_audio_file(filepath):
        """Return the role that this file represent (if any) else None."""
        filename = os.path.split(filepath)[-1]
        fnrole, ext = os.path.splitext(filename)
        if os.path.isfile(filepath) and ext[1:] in SUPPORTED_FILE_TYPES.keys():
            try:
                key = int(fnrole)
                return key
            except ValueError:
                pass
            key = role_name_to_int.get(fnrole.lower())
            if key is not None:
                return key
            # Check if it's a state name
            state_key = state_name_to_int.get(fnrole.lower())
            if state_key is not None:
                return state_key + STATE_OFFSET


def migrate_theme_to_named_files(theme_directory):
    for filename in os.listdir(theme_directory):
        filepath = os.path.join(theme_directory, filename)
        fnrole, ext = os.path.splitext(filename)
        if not os.path.isfile(filepath) or ext[1:] not in SUPPORTED_FILE_TYPES:
            continue
        try:
            role_int = int(fnrole)
            if role_int >= STATE_OFFSET:
                state_name = state_int_to_name.get(role_int - STATE_OFFSET)
                if state_name:
                    new_filename = f"{state_name}{ext}"
                    new_filepath = os.path.join(theme_directory, new_filename)
                    os.rename(filepath, new_filepath)
            else:
                role_name = role_int_to_name.get(role_int)
                if role_name:
                    new_filename = f"{role_name}{ext}"
                    new_filepath = os.path.join(theme_directory, new_filename)
                    os.rename(filepath, new_filepath)
        except (ValueError, OSError):
            continue



CONFLICT_PENDING_FILE = os.path.join(THEMES_DIR, ".pending_conflict.json")


def showPendingConflicts():
	if config.conf["audiothemes"].get("dont_show_conflicts", False):
		return
	conflicting_ids = {
		"navSounds": "Navigation Sound Effects",
		"SentenceNav": "SentenceNav",
		"browserNav": "BrowserNav",
		"phoneticPunctuation": "Earcons and Speech Rules",
		"audiothemes": "Audio Themes (legacy)",
		"audio_themes_NG": "Audio Themes NG (legacy)",
	}
	try:
		found = [
			addon.name for addon in addonHandler.getAvailableAddons()
			if addon.name in conflicting_ids and not addon.isPendingRemove
		]
		if found:
			with open(CONFLICT_PENDING_FILE, "w") as f:
				json.dump(found, f)
	except Exception:
		log.exception("Failed to check for conflicting add-ons")
	try:
		with open(CONFLICT_PENDING_FILE, "r") as f:
			found_ids = json.load(f)
		os.remove(CONFLICT_PENDING_FILE)
	except FileNotFoundError:
		return
	except Exception:
		log.exception("Failed to read pending conflicts file")
		return
	display_names = [conflicting_ids.get(n, n) for n in found_ids]
	import gui
	import wx
	try:
		addonHandler.initTranslation()
	except Exception:
		pass
	gui.mainFrame.prePopup()
	try:
		dlg = wx.Dialog(gui.mainFrame, title=_("Conflicting Add-ons"))
		dlg.Name = _("Conflicting Add-ons")
		sizer = wx.BoxSizer(wx.VERTICAL)
		label = wx.StaticText(dlg, label=_(
			"The following add-ons are now included in Advanced Audio Themes.\n"
			"Select the ones you want to remove to prevent conflicts:"
		))
		label.Name = _("The following add-ons are now included in Advanced Audio Themes. Select the ones you want to remove to prevent conflicts:")
		sizer.Add(label, flag=wx.ALL | wx.EXPAND, border=10)
		conflict_list = wx.ListView(dlg, style=wx.LC_REPORT | wx.LC_NO_HEADER, name=_("Conflicting add-ons"))
		conflict_list.EnableCheckBoxes(True)
		conflict_list.InsertColumn(0, _("Conflicting add-ons"), width=460)
		for display in display_names:
			idx = conflict_list.GetItemCount()
			conflict_list.InsertItem(idx, display)
		sizer.Add(conflict_list, proportion=1, flag=wx.ALL | wx.EXPAND, border=10)
		dont_show = wx.CheckBox(dlg, label=_("Don't show this dialog again"))
		dont_show.Name = _("Don't show this dialog again")
		sizer.Add(dont_show, flag=wx.ALL | wx.EXPAND, border=10)
		btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
		ok_btn = wx.Button(dlg, wx.ID_OK, _("Remove selected"))
		ok_btn.Name = _("Remove selected")
		cancel_btn = wx.Button(dlg, wx.ID_CANCEL, _("Skip"))
		cancel_btn.Name = _("Skip")
		btn_sizer.Add(ok_btn, flag=wx.ALL, border=5)
		btn_sizer.Add(cancel_btn, flag=wx.ALL, border=5)
		sizer.Add(btn_sizer, flag=wx.ALIGN_CENTER | wx.ALL, border=10)
		dlg.SetSizer(sizer)
		dlg.SetSize((500, 400))
		dlg.CenterOnScreen()
		dlg.Raise()
		if dlg.ShowModal() == wx.ID_OK:
			if dont_show.IsChecked():
				config.conf["audiothemes"]["dont_show_conflicts"] = True
			removed = 0
			for i, name in enumerate(found_ids):
				if conflict_list.IsItemChecked(i):
					for addon in addonHandler.getAvailableAddons():
						if addon.name == name and not addon.isPendingRemove:
							addon.requestRemove()
							removed += 1
			if removed:
				wx.MessageBox(
					_("The selected conflicting add-ons will be removed after you restart NVDA."),
					_("Restart Required"),
					wx.OK | wx.ICON_INFORMATION
				)
		dlg.Destroy()
	except Exception:
		log.exception("Failed to process conflicting add-ons dialog")
	finally:
		gui.mainFrame.postPopup()


_typing_dir_cache = {}

class AudioThemesHandler:
    """Query and manage audio themes."""
    _installed_themes_cache = None

    def __init__(self):
        config.conf.spec["audiothemes"] = audiothemes_config_defaults
        self.enabled = True
        self.player = UnspokenPlayer()
        self.active_theme = None
        self._config_lock = threading.RLock()
        # Cache updated on main thread by GlobalPlugin events (avoids COM in hook)
        self._current_app_name = None
        self._current_url = None
        self.ensure_themes_dir()
        self.migrate_all_themes_to_named_files()
        self.configure()
        for action in (
            post_configSave,
            post_configReset,
            post_configProfileSwitch,
            audiotheme_changed,
        ):
            action.register(self.configure)
        self._NVDA_getPropertiesSpeech = speech.speech.getPropertiesSpeech
        speech.speech.getPropertiesSpeech = self._hook_getSpeechTextForProperties

    def _hook_getSpeechTextForProperties(
        self, reason=NVDAObjects.controlTypes.OutputReason.QUERY, *args, **kwargs
    ):
        role = kwargs.get("role", None)
        states = kwargs.get("states", None)
        
        if role is not None:
            suppress = False
            
            if not self.player.speak_roles:
                suppress = True
            
            blacklisted_roles = _get_blacklisted_roles()
            if role in blacklisted_roles:
                suppress = True
                
            if role == controlTypes.Role.HEADING and role not in blacklisted_roles:
                suppress = False
                
            if suppress:
                try:
                    from . import frenzy
                    from . import utils
                    appName, windowTitle, url = utils.getCurrentContext()
                    if hasattr(frenzy, "roleRules") and role in frenzy.roleRules:
                        rule = frenzy.getActiveRuleContext(frenzy.roleRules[role], appName, windowTitle, url)
                        if rule is not None and getattr(rule, 'speechBehavior', 2) == 0:
                            suppress = False
                except Exception as e:
                    import logging
                    logging.getLogger("audiothemes").error(f"AudioThemes Error: {e}", exc_info=True)
            if self.player.use_in_say_all and SayAllHandler.isRunning():
                suppress = False
                
            if suppress:
                kwargs["_role"] = kwargs["role"]
                del kwargs["role"]
                if "level" in kwargs:
                    kwargs["_level"] = kwargs["level"]
                    del kwargs["level"]
                
        return self._NVDA_getPropertiesSpeech(reason, *args, **kwargs)

    def ensure_themes_dir(self):
        if not os.path.isdir(THEMES_DIR):
            os.makedirs(THEMES_DIR)
            
        user_config = config.conf["audiothemes"]
        bundled_themes_dir = os.path.join(os.path.dirname(__file__), "Themes")
        
        # Copy ALL bundled themes to the user's THEMES_DIR if they don't exist
        if os.path.isdir(bundled_themes_dir):
            for theme_name in os.listdir(bundled_themes_dir):
                if theme_name == "Default" and user_config.get("default_theme_deleted"):
                    continue
                bundled_theme_path = os.path.join(bundled_themes_dir, theme_name)
                if not os.path.isdir(bundled_theme_path):
                    continue
                    
                target_theme_path = os.path.join(THEMES_DIR, theme_name)
                if not os.path.exists(target_theme_path):
                    try:
                        shutil.copytree(bundled_theme_path, target_theme_path)
                    except Exception as e:
                        pass
                        
        default_theme_path = os.path.join(THEMES_DIR, "Default")
        if os.path.isdir(default_theme_path):
            if user_config.get("default_theme_deleted"):
                user_config["default_theme_deleted"] = False
            return
        if user_config.get("default_theme_deleted"):
            return
            
        # Fallback: create empty directory with info.json if Default was completely missing.
        os.makedirs(default_theme_path)
        info_path = os.path.join(default_theme_path, INFO_FILE_NAME)
        if not os.path.exists(info_path):
            with open(info_path, "w") as f:
                json.dump(
                    {"name": "Default", "author": "NVDA Contributers", "summary": "Default theme"}, f
                )

    def close(self):
        if self.active_theme is not None:
            self.active_theme.deactivate()
        speech.speech.getPropertiesSpeech = self._NVDA_getPropertiesSpeech
        speech.getPropertiesSpeech = self._NVDA_getPropertiesSpeech

    def shouldNukeRoleSpeech(self):
        if self.player.use_in_say_all and SayAllHandler.isRunning():
            return False
        if self.player.speak_roles:
            return False
        return True

    def migrate_all_themes_to_named_files(self):
        if config.conf["audiothemes"].get("migrated_to_named_files"):
            return
        for theme in self.get_installed_themes():
            migrate_theme_to_named_files(theme.directory)
        config.conf["audiothemes"]["migrated_to_named_files"] = True

    def get_active_theme(self):
        if not config.conf["audiothemes"]["enable_audio_themes"]:
            return
        theme = self.get_theme_from_folder(config.conf["audiothemes"]["active_theme"])
        if not theme:
            config.conf["audiothemes"]["active_theme"] = "Default"
            theme = self.get_theme_from_folder("Default")
        if not theme:
            return
        if theme.exists():
            theme.load(self.player)
            theme.is_active = True
            return theme

    def configure(self, *args, **kwargs):
        with self._config_lock:
            user_config = config.conf["audiothemes"]
            if self.active_theme is not None:
                self.active_theme.deactivate()
            self.enabled = user_config["enable_audio_themes"]
            self.active_theme = self.get_active_theme()
        
        # global _typing_dir_cache
        _typing_dir_cache.clear()
        # _theme_sound_existence_cache removed completely for performance
        self._theme_cache = {}
        try:
            raw_profiles = json.loads(user_config.get("app_profiles", "{}"))
            self._app_profiles_cache = {}
            for k, v in raw_profiles.items():
                if isinstance(v, str):
                    self._app_profiles_cache[k] = {"theme": v, "typing_pack": ""}
                else:
                    self._app_profiles_cache[k] = v
        except Exception as e:
            log.debugWarning(f"Malformed app_profiles JSON: {e}")
            self._app_profiles_cache = {}

        if self.active_theme is None:
            return
        self.player.audio3d = user_config["audio3d"]
        self.player.use_in_say_all = user_config["use_in_say_all"]
        self.player.speak_roles = user_config["speak_roles"]
        self.player.use_synth_volume = user_config["use_synth_volume"]
        self.player.volume = user_config["volume"]
        unspoken_config = config.conf["unspoken"]
        self.player.reverb = unspoken_config["Reverb"]
        self.player.room_size = unspoken_config["RoomSize"]
        self.player.damping = unspoken_config["Damping"]
        self.player.wet_level = unspoken_config["WetLevel"]
        self.player.dry_level = unspoken_config["DryLevel"]
        self.player.width = unspoken_config["Width"]
        self.disabled_apps = []
        raw_disabled = user_config["disabled_apps"]
        if raw_disabled:
            for p in raw_disabled.split(','):
                p = p.strip().lower().removesuffix('.exe')
                if p:
                    self.disabled_apps.append(p)

    def play(self, obj_info, sound):
        """
        Play a themed sound.  obj_info is a plain dict (no COM object).
        """
        force_3d = obj_info.get("force_3d", False) if isinstance(obj_info, dict) else False
        if not force_3d and (not self.enabled or (self.active_theme is None)):
            return

        # Check suppression via _current_app_name (always up to date,
        # unlike the snapshot's foreground_app which may be stale from the queue).
        if not force_3d:
            cur_app = getattr(self, '_current_app_name', None)
            if cur_app:
                app_l = cur_app.lower()
                if any(p in app_l for p in self.disabled_apps):
                    from .utils import is_sound_suppressed
                    if is_sound_suppressed("theme_sounds"):
                        return

        foreground_app = obj_info.get("foreground_app") if isinstance(obj_info, dict) else None
        theme = self.get_theme_for_app(foreground_app)
        if not theme and force_3d:
            theme = self.active_theme

        if not theme:
            return

        with theme._lock:
            sound_obj = theme.sounds.get(sound)
            if sound_obj is None and force_3d:
                import controlTypes
                sound_obj = theme.sounds.get(controlTypes.Role.BUTTON)
                if sound_obj is None and theme.sounds:
                    sound_obj = next(iter(theme.sounds.values()))
                    
        if sound_obj is None:
            return
        self.player.play(obj_info, sound_obj)

    def get_theme_for_app(self, app_name):
        with self._config_lock:
            if not app_name:
                return self.active_theme
            app_name = app_name.lower()
            profile = self._app_profiles_cache.get(app_name)
            target_folder = profile.get("theme") if isinstance(profile, dict) else profile
            if target_folder:
                if target_folder == self.active_theme.folder:
                    return self.active_theme
                if target_folder in self._theme_cache:
                    return self._theme_cache[target_folder]
                theme = self.get_theme_from_folder(target_folder)
                if theme and theme.exists():
                    theme.load(self.player)
                    self._theme_cache[target_folder] = theme
                    return theme
            return self.active_theme

    def play_theme_sound(self, sound_name, angle_x=0, angle_y=0):
        if not self.enabled or (self.active_theme is None):
            return False
            
        foreground_app = getattr(self, '_current_app_name', None)
        if foreground_app:
            app_l = foreground_app.lower()
            if any(p in app_l for p in self.disabled_apps):
                from .utils import is_sound_suppressed
                if is_sound_suppressed("theme_sounds"):
                    return False

        theme = self.get_theme_for_app(foreground_app)

        if not any(sound_name.endswith('.' + ext) for ext in SUPPORTED_FILE_TYPES):
            sound_name += '.wav'

        sound_path = os.path.join(theme.directory, sound_name)

        # Check pre-indexed files in memory to eliminate Disk I/O
        if sound_name.lower() in getattr(theme, 'available_files', set()):
            self.player.play_file(
                sound_path,
                volume=config.conf["audiothemes"]["volume"],
                audio3d=bool(angle_x or angle_y),
                angle_x=angle_x,
                angle_y=angle_y
            )
            return True
        return False

    def get_earcon_angles(self):
        try:
            import api
            focus = api.getFocusObject()
            obj = focus
            location = getattr(obj, 'location', None)
            if not location:
                return 0.0, 0.0
            desk_location = api.getDesktopObject().location
            desktop_max_x = desk_location[2] if desk_location else 1920
            desktop_max_y = desk_location[3] if desk_location else 1080
            obj_x = location[0] + (location[2] / 2.0)
            obj_y = location[1] + (location[3] / 2.0)
            angle_x = ((obj_x - desktop_max_x / 2.0) / desktop_max_x) * 180.0
            percent = (desktop_max_y - obj_y) / desktop_max_y
            angle_y = 50.0 * percent + (-40.0)
            angle_x = max(-90.0, min(90.0, angle_x))
            angle_y = max(-90.0, min(90.0, angle_y))
            return angle_x, angle_y
        except Exception:
            return 0.0, 0.0

    def get_typing_pack_for_app(self, app_name):
        with self._config_lock:
            global_pack = config.conf["audiothemes"].get("typing_sound_pack", "1blueSwitch")
            if not app_name:
                return global_pack
            app_name = app_name.lower()
            profile = self._app_profiles_cache.get(app_name)
            if isinstance(profile, dict):
                pack = profile.get("typing_pack")
                if pack:
                    return pack
            return global_pack

    def play_typing_sound(self, ch=None, vkCode=None, extended=None):
        if not config.conf["audiothemes"]["typing_sounds"]:
            return
        if not self.enabled or (self.active_theme is None):
            return
            
        # Debounce: prevent same key sound from playing twice rapidly (keyDown + typedCharacter overlap)
        import time
        now = time.monotonic()
        if hasattr(self, "_last_typing_time") and (now - self._last_typing_time) < 0.05:
            if getattr(self, "_last_typing_vk", None) == vkCode:
                return
        self._last_typing_time = now
        self._last_typing_vk = vkCode
            
        foreground_app = getattr(self, '_current_app_name', None)
        if foreground_app:
            app_l = foreground_app.lower()
            if any(p in app_l for p in self.disabled_apps):
                from .utils import is_sound_suppressed
                if is_sound_suppressed("typing_sounds"):
                    return

        theme = self.get_theme_for_app(foreground_app)

        import random
        # 1. Check if the active theme has its own typingSounds folder
        theme_typing_dir = os.path.join(theme.directory, "typingSounds")
        typing_dir = None
        
        if os.path.isdir(theme_typing_dir):
            typing_dir = theme_typing_dir
        else:
            # 2. Fall back to the globally selected typing pack or app-specific pack
            typing_pack = self.get_typing_pack_for_app(foreground_app)
            typing_dir = os.path.join(os.path.dirname(__file__), "typingSounds", typing_pack)
        
        sound_path = None
        if typing_dir:
            # global _typing_dir_cache
            cache = _typing_dir_cache.get(typing_dir)
            if cache is None:
                if os.path.isdir(typing_dir):
                    files = [f for f in os.listdir(typing_dir) if f.lower().endswith(('.wav', '.ogg', '.mp3'))]  # typing packs are bundled as WAV/OGG/MP3 only
                    cache = {'files': files}
                else:
                    cache = {'files': []}
                _typing_dir_cache[typing_dir] = cache
            
            if cache['files']:
                if vkCode is not None:
                    # Check for dedicated sound files based on vkCode
                    vk_file_map = {
                        0x0D: "enter.wav", 0x08: "backspace.wav", 0x20: "space.wav",
                        0x10: "shift.wav", 0x11: "ctrl.wav", 0x12: "alt.wav",
                        0x5B: "win.wav", 0x5C: "win.wav"
                    }
                    expected_file = vk_file_map.get(vkCode)
                    if expected_file and expected_file in cache['files']:
                        sound_path = os.path.join(typing_dir, expected_file)
                
                if not sound_path:
                    special_files = {"enter.wav", "backspace.wav", "space.wav", "shift.wav", "ctrl.wav", "alt.wav", "win.wav"}
                    valid_choices = [f for f in cache['files'] if f not in special_files]
                    if valid_choices:
                        sound_path = os.path.join(typing_dir, random.choice(valid_choices))
                    else:
                        sound_path = os.path.join(typing_dir, random.choice(cache['files']))
        if sound_path:
            self.player.play_file(
                sound_path,
                volume=config.conf["audiothemes"]["typing_sounds_volume"],
                audio3d=False,
                ch=ch,
                vkCode=vkCode,
                extended=extended
            )

    @classmethod
    def get_theme_from_folder(cls, folderpath):
        expected = os.path.join(THEMES_DIR, folderpath)
        if not os.path.isdir(expected):
            return None
        info_file = os.path.join(expected, INFO_FILE_NAME)
        if os.path.isfile(info_file):
            info = cls.load_info_file(info_file)
            return AudioTheme(directory=expected, **info)
        name = os.path.basename(expected)
        info = {"name": name, "author": "Unknown", "summary": name}
        cls.write_info_file(info_file, info)
        return AudioTheme(directory=expected, **info)

    @classmethod
    def get_installed_themes(cls):
        if cls._installed_themes_cache is not None:
            return cls._installed_themes_cache
        result = []
        for folder in os.listdir(THEMES_DIR):
            theme = cls.get_theme_from_folder(folder)
            if theme is None:
                continue
            result.append(theme)
        cls._installed_themes_cache = result
        return result

    @classmethod
    def _invalidate_themes_cache(cls):
        cls._installed_themes_cache = None

    @staticmethod
    def _sanitize_folder_name(name):
        name = name.strip().replace(" ", "_")
        keep = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.")
        return "".join(c if c in keep else "_" for c in name).strip("_") or "Theme"

    @classmethod
    def install_audio_themePackage(cls, theme_pack):
        cls._invalidate_themes_cache()
        identified_path = os.path.join(THEMES_DIR, uuid4().hex).lower()
        with ZipFile(theme_pack, "r") as pack:
            if pack.infolist()[0].is_dir():
                cls._install_legacy(pack, identified_path)
            else:
                pack.extractall(path=identified_path)
        info_file = os.path.join(identified_path, INFO_FILE_NAME)
        if not os.path.exists(info_file):
            return
        theme_info = cls.load_info_file(info_file)
        theme_name = theme_info.get("name", "").strip()
        if theme_name:
            safe_name = cls._sanitize_folder_name(theme_name)
            if theme_name.lower() == "default":
                safe_name = "Default"
            target_path = os.path.join(THEMES_DIR, safe_name)
            if os.path.isdir(target_path):
                shutil.rmtree(target_path)
            if safe_name != os.path.basename(identified_path):
                os.rename(identified_path, target_path)

    @classmethod
    def install_audio_themeFolder(cls, source_path):
        cls._invalidate_themes_cache()
        folder_name = os.path.basename(os.path.normpath(source_path))
        safe_name = cls._sanitize_folder_name(folder_name)
        target_path = os.path.join(THEMES_DIR, safe_name)
        if os.path.isdir(target_path):
            shutil.rmtree(target_path)
        shutil.copytree(source_path, target_path)
        info_file = os.path.join(target_path, INFO_FILE_NAME)
        if not os.path.isfile(info_file):
            info = {"name": folder_name, "author": "Unknown", "summary": folder_name}
            cls.write_info_file(info_file, info)

    @classmethod
    def install_typing_soundPackage(cls, pack_path):
        import json
        pack_name = "Imported_" + uuid4().hex[:8]
        with ZipFile(pack_path, "r") as pack:
            if "info.json" in pack.namelist():
                try:
                    info_data = json.loads(pack.read("info.json").decode("utf-8"))
                    pack_name = info_data.get("name", pack_name)
                except Exception:
                    pass
            elif len(pack.infolist()) > 0 and pack.infolist()[0].is_dir():
                pack_name = pack.infolist()[0].orig_filename.strip("/")
            
            addon_dir = os.path.dirname(__file__)
            typing_dir = os.path.join(addon_dir, "typingSounds", pack_name)
            
            if os.path.exists(typing_dir):
                shutil.rmtree(typing_dir)
            os.makedirs(typing_dir)
            pack.extractall(path=typing_dir)
            
            contents = os.listdir(typing_dir)
            if len(contents) == 1:
                inner_path = os.path.join(typing_dir, contents[0])
                if os.path.isdir(inner_path):
                    for item in os.listdir(inner_path):
                        shutil.move(os.path.join(inner_path, item), typing_dir)
                    os.rmdir(inner_path)

    @classmethod
    def _install_legacy(cls, pack, final_dst):
        pack_infolist = pack.infolist()
        theme_name = pack_infolist[0].orig_filename.strip("/")
        os.mkdir(final_dst)
        for zinfo in pack_infolist[1:]:
            filename = os.path.split(zinfo.filename)[1]
            with open(os.path.join(final_dst, filename), "wb") as soundfile:
                soundfile.write(pack.read(zinfo))
        info_file = os.path.join(final_dst, INFO_FILE_NAME)
        theme_info = cls.load_info_file(info_file)
        if "name" not in theme_info:
            theme_info["name"] = theme_name
            cls.write_info_file(info_file, theme_info)

    @staticmethod
    def remove_audio_theme(theme):
        AudioThemesHandler._invalidate_themes_cache()
        if theme.name == "Default":
            config.conf["audiothemes"]["default_theme_deleted"] = True
        theme.deactivate()
        if theme.directory:
            shutil.rmtree(theme.directory)

    @staticmethod
    def load_info_file(info_file):
        with open(info_file, "r", encoding="utf8") as f:
            return json.load(f)

    @staticmethod
    def write_info_file(file_path, data):
        with open(file_path, "w", encoding="utf8") as f:
            json.dump(data, f)

    @staticmethod
    def make_zip_file(output_filename, source_dir):
        with ZipFile(output_filename, "w", ZIP_DEFLATED) as zip:
            for filename in os.listdir(source_dir):
                file = os.path.join(source_dir, filename)
                if os.path.isfile(file):
                    zip.write(file, filename)


def get_typing_sound_packs():
    import os
    typingSoundsDir = os.path.join(os.path.dirname(__file__), "typingSounds")
    if os.path.isdir(typingSoundsDir):
        packs = [d for d in os.listdir(typingSoundsDir) if os.path.isdir(os.path.join(typingSoundsDir, d))]
        if packs:
            return packs
    return ["1blueSwitch"]
