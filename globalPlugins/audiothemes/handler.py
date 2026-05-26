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
    "blacklisted_roles": "int_list(default=[19])",
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
}


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



_typing_dir_cache = {}

class AudioThemesHandler:
    """Query and manage audio themes."""

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
            
            blacklisted_roles = config.conf["audiothemes"].get("blacklisted_roles", [])
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
        except Exception:
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
        self.disabled_apps = user_config["disabled_apps"].split(',') if user_config["disabled_apps"] else []

    def play(self, obj_info, sound):
        """
        Play a themed sound.  obj_info is a plain dict (no COM object).
        """
        force_3d = obj_info.get("force_3d", False) if isinstance(obj_info, dict) else False
        if not force_3d and (not self.enabled or (self.active_theme is None)):
            return

        # Use pre-extracted foreground app name from snapshot (no COM call here).
        foreground_app = obj_info.get("foreground_app") if isinstance(obj_info, dict) else None
        if foreground_app and not force_3d:
            import fnmatch
            app_l = foreground_app.lower()
            if any(fnmatch.fnmatch(app_l, p.lower()) for p in self.disabled_apps):
                return

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
            import fnmatch
            app_l = foreground_app.lower()
            if any(fnmatch.fnmatch(app_l, p.lower()) for p in self.disabled_apps):
                return False
            
        theme = self.get_theme_for_app(foreground_app)
            
        if not sound_name.endswith('.wav'):
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
            import fnmatch
            app_l = foreground_app.lower()
            if any(fnmatch.fnmatch(app_l, p.lower()) for p in self.disabled_apps):
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
                    files = [f for f in os.listdir(typing_dir) if f.lower().endswith(('.wav', '.ogg'))]
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
        info_file = os.path.join(expected, INFO_FILE_NAME)
        if os.path.isfile(info_file):
            info = cls.load_info_file(info_file)
            return AudioTheme(directory=expected, **info)

    @classmethod
    def get_installed_themes(cls):
        for folder in os.listdir(THEMES_DIR):
            theme = cls.get_theme_from_folder(folder)
            if theme is None:
                continue
            yield theme

    @classmethod
    def install_audio_themePackage(cls, theme_pack):
        identified_path = os.path.join(THEMES_DIR, uuid4().hex).lower()
        with ZipFile(theme_pack, "r") as pack:
            if pack.infolist()[0].is_dir():
                # Legacy theme package
                cls._install_legacy(pack, identified_path)
            else:
                pack.extractall(path=identified_path)
        info_file = os.path.join(identified_path, INFO_FILE_NAME)
        if not os.path.exists(info_file):
            return
        theme_info = cls.load_info_file(info_file)
        if theme_info.get("name", "").lower() == "default":
            default_theme_path = os.path.join(THEMES_DIR, "Default")
            if os.path.isdir(default_theme_path):
                shutil.rmtree(default_theme_path)
            os.rename(identified_path, default_theme_path)

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
