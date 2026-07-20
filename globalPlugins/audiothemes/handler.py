# coding: utf-8


# This file is covered by the GNU General Public License.

from enum import IntEnum
from collections import OrderedDict
from dataclasses import dataclass, field, asdict
from zipfile import ZipFile, ZIP_DEFLATED
from uuid import uuid4
import api
import os
import ctypes
import random
import shutil
import copy
import json
import threading
import time
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
    "app_profiles_enabled": "boolean(default=True)",
    "navLayerPassThrough": "boolean(default=True)",
    "navLayerTimeout": "boolean(default=True)",
    "navLayerPlaySounds": "boolean(default=True)",
    "navLayerEnabledModes": "string(default='')",
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
    "firstlast_fallback": "string(default='role')",
    "first_fallback_role_name": "string(default='listitem')",
    "last_fallback_role_name": "string(default='listitem')",
    "general_fallback": "string(default='role')",
    "general_fallback_role_name": "string(default='listitem')",
    "state_sounds_suppress_role": "boolean(default=False)",
    "universal_fl_enabled": "boolean(default=True)",
    "fl_enabled_roles": "string(default='[\"listitem\",\"treeviewitem\",\"menuitem\",\"tab\"]')",
    "fl_solo_behavior": "string(default='first')",
    "fl_detection_mode": "string(default='smart')",
    "progress_pan_mode": "string(default='progress')",
    "progress_pan_range": "integer(default=180, min=45, max=180)",
    "progress_pitch_shift": "boolean(default=True)",
    "sys_status_enabled": "boolean(default=True)",
    "sys_status_volume": "integer(default=20)",
    "sys_ac_enabled": "boolean(default=True)",
    "sys_battery_enabled": "boolean(default=True)",
    "sys_battery_low_threshold": "integer(default=20, min=0, max=100)",
    "sys_battery_critical_threshold": "integer(default=10, min=0, max=100)",
    "sys_usb_enabled": "boolean(default=True)",
    "sys_volume_enabled": "boolean(default=True)",
    "sys_network_enabled": "boolean(default=True)",
    "sys_wake_enabled": "boolean(default=True)",
    "sys_network_check_interval": "integer(default=15, min=5, max=300)",
    "sys_battery_check_interval": "integer(default=30, min=5, max=300)",
    "sys_all_usb": "boolean(default=True)",
    "emoji_enabled": "boolean(default=True)",
    "emoji_sound": "boolean(default=True)",
    "emoji_prefix": "boolean(default=True)",
    "emoji_prefix_text": "string(default='emoji')",
    "emoji_suffix_text": "string(default='emoji')",
    "emoji_volume": "integer(default=20)",
    "emoji_position": "string(default='before')",
    "emoji_sound_position": "string(default='before')",
    "emoji_repeat": "string(default='per_emoji')",
    "emoji_cat_smileys": "boolean(default=True)",
    "emoji_cat_people": "boolean(default=True)",
    "emoji_cat_animals": "boolean(default=True)",
    "emoji_cat_food": "boolean(default=True)",
    "emoji_cat_travel": "boolean(default=True)",
    "emoji_cat_activities": "boolean(default=True)",
    "emoji_cat_objects": "boolean(default=True)",
    "emoji_cat_symbols": "boolean(default=True)",
    "emoji_cat_flags": "boolean(default=True)",
    # Per-category sound toggles (independent from prefix toggles)
    "emoji_sound_cat_smileys": "boolean(default=True)",
    "emoji_sound_cat_people": "boolean(default=True)",
    "emoji_sound_cat_animals": "boolean(default=True)",
    "emoji_sound_cat_food": "boolean(default=True)",
    "emoji_sound_cat_travel": "boolean(default=True)",
    "emoji_sound_cat_activities": "boolean(default=True)",
    "emoji_sound_cat_objects": "boolean(default=True)",
    "emoji_sound_cat_symbols": "boolean(default=True)",
    "emoji_sound_cat_flags": "boolean(default=True)",
    # Separate repeat modes for sound and prefix
    "emoji_sound_repeat": "string(default='per_emoji')",
    "emoji_prefix_repeat": "string(default='per_emoji')",
    # Per-category prefix/suffix text (JSON)
    "emoji_prefix_text_per_category": "string(default='{}')",
    "emoji_suffix_text_per_category": "string(default='{}')",
    # Per-category volume override (JSON)
    "emoji_volume_per_category": "string(default='{}')",
    # Delay before/after emoji sound (ms)
    "emoji_delay_before": "integer(default=0, min=0, max=5000)",
    "emoji_delay_after": "integer(default=0, min=0, max=5000)",
    # Suppress role sound when emoji is present
    "emoji_suppress_role_sound": "boolean(default=False)",
    # Emoji blacklist (string of emoji characters)
    "emoji_blacklist": "string(default='')",
    # Per-emoji custom descriptions (JSON map)
    "emoji_custom_descriptions": "string(default='{}')",
    # Per-category sound position (JSON map)
    "emoji_sound_position_per_category": "string(default='{}')",
    # Clipboard Announcements
    "clipboard_enabled": "boolean(default=False)",
    "clipboard_announce_mode": "string(default='both')",
    "clipboard_volume": "integer(default=20, min=0, max=100)",
    "clipboard_delay": "integer(default=50, min=0, max=500)",
    "clipboard_copy": "boolean(default=True)",
    "clipboard_cut": "boolean(default=True)",
    "clipboard_paste": "boolean(default=True)",
    "clipboard_selectall": "boolean(default=True)",
    "clipboard_undo": "boolean(default=True)",
    "clipboard_redo": "boolean(default=True)",
    "clipboard_pasteplain": "boolean(default=True)",
    "clipboard_redo2": "boolean(default=True)",
    "clipboard_copy_sound": "boolean(default=True)",
    "clipboard_cut_sound": "boolean(default=True)",
    "clipboard_paste_sound": "boolean(default=True)",
    "clipboard_selectall_sound": "boolean(default=True)",
    "clipboard_undo_sound": "boolean(default=True)",
    "clipboard_redo_sound": "boolean(default=True)",
    "clipboard_pasteplain_sound": "boolean(default=True)",
    "clipboard_redo2_sound": "boolean(default=True)",
    "clipboard_copy_speech": "boolean(default=True)",
    "clipboard_cut_speech": "boolean(default=True)",
    "clipboard_paste_speech": "boolean(default=True)",
    "clipboard_selectall_speech": "boolean(default=True)",
    "clipboard_undo_speech": "boolean(default=True)",
    "clipboard_redo_speech": "boolean(default=True)",
    "clipboard_pasteplain_speech": "boolean(default=True)",
    "clipboard_redo2_speech": "boolean(default=True)",
    "clipboard_custom_texts": "string(default='{}')",
    "config_version": "integer(default=1)",
}

# Current config schema version.  Increment when making backward-incompatible
# changes (e.g. renaming or removing a key, changing a default that existing
# users should not inherit without migration).
CONFIG_VERSION = 1


_blacklisted_roles_cache = None
_blacklisted_roles_cache_raw = None

def _get_blacklisted_roles():
    global _blacklisted_roles_cache, _blacklisted_roles_cache_raw
    raw = config.conf["audiothemes"].get("blacklisted_roles", "[19]")
    if raw == _blacklisted_roles_cache_raw:
        return _blacklisted_roles_cache
    if isinstance(raw, list):
        result = raw if all(isinstance(r, int) for r in raw) else [19]
    elif isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            result = parsed if isinstance(parsed, list) and all(isinstance(r, int) for r in parsed) else [19]
            return result
        except Exception:
            result = [19]
    else:
        result = [19]
    _blacklisted_roles_cache = result
    _blacklisted_roles_cache_raw = raw
    return result


class SpecialProps(IntEnum):
    """Represents sounds defined by this addon."""

    protected = 2500
    first = 2501
    last = 2502
    notify = 2503
    loaded = 2504
    heading7 = 2505
    heading8 = 2506
    heading9 = 2507

    # System Status Sounds (2510+)
    sys_ac_plug = 2510
    sys_ac_unplug = 2511
    sys_battery_low = 2512
    sys_battery_critical = 2513
    sys_battery_full = 2514
    sys_usb_plug = 2515
    sys_usb_unplug = 2516
    sys_volume_plug = 2517
    sys_volume_unplug = 2518
    sys_network_connect = 2519
    sys_network_disconnect = 2520
    sys_wake = 2521
    sys_sleep = 2522

    emoji = 2523
    emoji_before = 2524
    emoji_after = 2525

    # Per-category emoji sounds (2526-2534)
    emoji_smileys = 2526
    emoji_people = 2527
    emoji_animals = 2528
    emoji_food = 2529
    emoji_travel = 2530
    emoji_activities = 2531
    emoji_objects = 2532
    emoji_symbols = 2533
    emoji_flags = 2534

    # Clipboard Announcements (2535-2542)
    clipboard_copy = 2535
    clipboard_cut = 2536
    clipboard_paste = 2537
    clipboard_selectall = 2538
    clipboard_undo = 2539
    clipboard_redo = 2540
    clipboard_pasteplain = 2541
    clipboard_redo2 = 2542


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
        # Translators: The label of the sound for heading level 7.
        SpecialProps.heading7: _("Heading Level 7"),
        # Translators: The label of the sound for heading level 8.
        SpecialProps.heading8: _("Heading Level 8"),
        # Translators: The label of the sound for heading level 9.
        SpecialProps.heading9: _("Heading Level 9"),
        # Translators: The label of the sound played when AC power is connected.
        SpecialProps.sys_ac_plug: _("AC Power Connected"),
        # Translators: The label of the sound played when AC power is disconnected.
        SpecialProps.sys_ac_unplug: _("AC Power Disconnected"),
        # Translators: The label of the sound played when battery level is low.
        SpecialProps.sys_battery_low: _("Battery Low"),
        # Translators: The label of the sound played when battery level is critical.
        SpecialProps.sys_battery_critical: _("Battery Critical"),
        # Translators: The label of the sound played when battery is fully charged.
        SpecialProps.sys_battery_full: _("Battery Fully Charged"),
        # Translators: The label of the sound played when a USB device is plugged in.
        SpecialProps.sys_usb_plug: _("USB Device Plugged"),
        # Translators: The label of the sound played when a USB device is unplugged.
        SpecialProps.sys_usb_unplug: _("USB Device Unplugged"),
        # Translators: The label of the sound played when a storage volume is mounted.
        SpecialProps.sys_volume_plug: _("Storage Volume Mounted"),
        # Translators: The label of the sound played when a storage volume is unmounted.
        SpecialProps.sys_volume_unplug: _("Storage Volume Unmounted"),
        # Translators: The label of the sound played when network connectivity is established.
        SpecialProps.sys_network_connect: _("Network Connected"),
        # Translators: The label of the sound played when network connectivity is lost.
        SpecialProps.sys_network_disconnect: _("Network Disconnected"),
        # Translators: The label of the sound played when the system wakes from sleep.
        SpecialProps.sys_wake: _("System Wake"),
        # Translators: The label of the sound played when the system is going to sleep.
        SpecialProps.sys_sleep: _("System Sleep"),
        # Translators: The label of the sound played when an emoji character is encountered.
        SpecialProps.emoji: _("Emoji Sound"),
        # Translators: The label of the sound played before an emoji character.
        SpecialProps.emoji_before: _("Emoji Before Sound"),
        # Translators: The label of the sound played after an emoji character.
        SpecialProps.emoji_after: _("Emoji After Sound"),
        # Translators: The label of the sound for emoji category smileys.
        SpecialProps.emoji_smileys: _("Emoji Smileys Sound"),
        # Translators: The label of the sound for emoji category people.
        SpecialProps.emoji_people: _("Emoji People Sound"),
        # Translators: The label of the sound for emoji category animals.
        SpecialProps.emoji_animals: _("Emoji Animals Sound"),
        # Translators: The label of the sound for emoji category food.
        SpecialProps.emoji_food: _("Emoji Food Sound"),
        # Translators: The label of the sound for emoji category travel.
        SpecialProps.emoji_travel: _("Emoji Travel Sound"),
        # Translators: The label of the sound for emoji category activities.
        SpecialProps.emoji_activities: _("Emoji Activities Sound"),
        # Translators: The label of the sound for emoji category objects.
        SpecialProps.emoji_objects: _("Emoji Objects Sound"),
        # Translators: The label of the sound for emoji category symbols.
        SpecialProps.emoji_symbols: _("Emoji Symbols Sound"),
        # Translators: The label of the sound for emoji category flags.
        SpecialProps.emoji_flags: _("Emoji Flags Sound"),
        # Translators: The label of the sound for clipboard copy.
        SpecialProps.clipboard_copy: _("Clipboard Copy"),
        # Translators: The label of the sound for clipboard cut.
        SpecialProps.clipboard_cut: _("Clipboard Cut"),
        # Translators: The label of the sound for clipboard paste.
        SpecialProps.clipboard_paste: _("Clipboard Paste"),
        # Translators: The label of the sound for clipboard select all.
        SpecialProps.clipboard_selectall: _("Clipboard Select All"),
        # Translators: The label of the sound for clipboard undo.
        SpecialProps.clipboard_undo: _("Clipboard Undo"),
        # Translators: The label of the sound for clipboard redo.
        SpecialProps.clipboard_redo: _("Clipboard Redo"),
        # Translators: The label of the sound for clipboard paste plain text.
        SpecialProps.clipboard_pasteplain: _("Clipboard Paste Plain Text"),
        # Translators: The label of the sound for clipboard alternate redo.
        SpecialProps.clipboard_redo2: _("Clipboard Alternate Redo"),
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
                shutil.copy2(src_path, dst)
            except Exception:
                continue
            available.add(f"{name}{ext}".lower())
            new_sounds[target_role] = player.make_sound_object(dst)
            created += 1
        return created

    def load(self, player):
        with self._lock:
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
            self.sounds = {}

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
_typing_dir_cache_lock = threading.Lock()

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
        # Initialize debounce state to avoid hasattr in hot paths
        self._last_typing_time = 0.0
        self._last_typing_vk = 0
        self._cached_config = {}  # populated by configure()
        self._system_monitor = None
        self.ensure_themes_dir()
        self.migrate_all_themes_to_named_files()
        self.configure()
        self._registered_actions = (
            post_configSave,
            post_configReset,
            post_configProfileSwitch,
            audiotheme_changed,
        )
        for action in self._registered_actions:
            action.register(self.configure)
        self._NVDA_getPropertiesSpeech = speech.speech.getPropertiesSpeech
        speech.speech.getPropertiesSpeech = self._hook_getSpeechTextForProperties
        # System status monitor
        self._system_monitor = None
        self._start_system_status_monitoring()

    def _hook_getSpeechTextForProperties(
        self, reason=NVDAObjects.controlTypes.OutputReason.QUERY, *args, **kwargs
    ):
        role = kwargs.get("role", None)
        states = kwargs.get("states", None)
        
        if role is not None:
            suppress = False
            
            if not self.player.speak_roles:
                suppress = True
            
            blacklisted_roles = self._cached_config.get("blacklisted_roles", [19])
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
                    log.error(f"AudioThemes Error: {e}", exc_info=True)
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
        if self._system_monitor is not None:
            self._system_monitor.stop()
            self._system_monitor = None
        speech.speech.getPropertiesSpeech = self._NVDA_getPropertiesSpeech
        speech.getPropertiesSpeech = self._NVDA_getPropertiesSpeech
        for action in self._registered_actions:
            try:
                action.unregister(self.configure)
            except (ValueError, AttributeError):
                pass
        with self._config_lock:
            self._theme_cache.clear()
        with _typing_dir_cache_lock:
            _typing_dir_cache.clear()

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
            log.debug("get_active_theme: themes disabled")
            return
        theme = self.get_theme_from_folder(config.conf["audiothemes"]["active_theme"])
        if not theme:
            config.conf["audiothemes"]["active_theme"] = "Default"
            theme = self.get_theme_from_folder("Default")
        if not theme:
            log.debug("get_active_theme: no theme found")
            return
        if theme.exists():
            theme.load(self.player)
            theme.is_active = True
            return theme

    def _migrate_config(self):
        try:
            saved = config.conf["audiothemes"].get("config_version", 0)
        except Exception:
            saved = 0
        if saved >= CONFIG_VERSION:
            return
        if saved < 1:
            pass  # Placeholder for future migrations.
        config.conf["audiothemes"]["config_version"] = CONFIG_VERSION

    def configure(self, *args, **kwargs):
        self._migrate_config()
        with self._config_lock:
            user_config = config.conf["audiothemes"]
            new_enabled = user_config["enable_audio_themes"]
            new_theme_folder = user_config["active_theme"] if new_enabled else None
            old_theme_folder = self.active_theme.folder if self.active_theme else None
            theme_changed = (
                new_enabled != self.enabled or
                new_theme_folder != old_theme_folder
            )
            if theme_changed:
                if self.active_theme is not None:
                    self.active_theme.deactivate()
                self.enabled = new_enabled
                self.active_theme = self.get_active_theme()
                with _typing_dir_cache_lock:
                    _typing_dir_cache.clear()
                self._theme_cache = {}
                log.debug(f"configure: enabled={self.enabled} active_theme={'present' if self.active_theme else 'None'}")
            else:
                self.enabled = new_enabled

        # Always re-parse app profiles (they may have changed independently)
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
        # Cache processing config on the player to avoid config.conf reads in _ensure_processed
        self.player._trim_silence = unspoken_config.get("TrimSilence", True)
        self.player._trim_silence_threshold = float(unspoken_config.get("TrimSilenceThreshold", 0.01))
        self.player._smart_volume = unspoken_config.get("SmartVolume", True)
        self.player._smooth_envelope = unspoken_config.get("SmoothEnvelope", False)
        self.player._noise_gate = unspoken_config.get("NoiseGate", False)
        self.player._noise_gate_threshold = float(unspoken_config.get("NoiseGateThreshold", 0.02))
        self.player._noise_gate_attack = int(unspoken_config.get("NoiseGateAttack", 5))
        self.player._noise_gate_release = int(unspoken_config.get("NoiseGateRelease", 50))
        self.player._bass_boost = unspoken_config.get("BassBoost", False)
        self.player._bass_boost_gain = float(unspoken_config.get("BassBoostGain", 3))
        self.player._bass_boost_cutoff = float(unspoken_config.get("BassBoostCutoff", 200))
        self.disabled_apps = []
        raw_disabled = user_config["disabled_apps"]
        if raw_disabled:
            for p in raw_disabled.split(','):
                p = p.strip().lower().removesuffix('.exe')
                if p:
                    self.disabled_apps.append(p)
        # Cache ALL hot-path config values to avoid ~15-20 config.conf lookups per event cycle.
        # Refreshed on every configure() call (post_configSave, post_configProfileSwitch, etc.).
        fl_roles_raw = user_config.get("fl_enabled_roles")
        fl_enabled_roles_set = None
        if fl_roles_raw and fl_roles_raw != "all":
            try:
                fl_enabled_roles_set = set(json.loads(fl_roles_raw))
            except Exception:
                fl_enabled_roles_set = None
        blr = user_config.get("blacklisted_roles", "[19]")
        if isinstance(blr, list):
            blr_parsed = blr if all(isinstance(r, int) for r in blr) else [19]
        elif isinstance(blr, str):
            try:
                blr_parsed_tmp = json.loads(blr)
                blr_parsed = blr_parsed_tmp if isinstance(blr_parsed_tmp, list) and all(isinstance(r, int) for r in blr_parsed_tmp) else [19]
            except Exception:
                blr_parsed = [19]
        else:
            blr_parsed = [19]
        unspoken_cfg = config.conf["unspoken"]
        self._cached_config = {
            # First/Last detection
            "universal_fl_enabled": user_config.get("universal_fl_enabled", True),
            "fl_enabled_roles": fl_roles_raw,
            "fl_enabled_roles_set": fl_enabled_roles_set,
            "fl_detection_mode": user_config.get("fl_detection_mode", "smart"),
            "fl_solo_behavior": user_config.get("fl_solo_behavior", "first"),
            "state_sounds_suppress_role": user_config.get("state_sounds_suppress_role", False),
            "emoji_suppress_role_sound": user_config.get("emoji_suppress_role_sound", False),
            "firstlast_fallback": user_config.get("firstlast_fallback", "role"),
            "first_fallback_role_name": user_config.get("first_fallback_role_name", "listitem"),
            "last_fallback_role_name": user_config.get("last_fallback_role_name", "listitem"),
            "general_fallback": user_config.get("general_fallback", "role"),
            "general_fallback_role_name": user_config.get("general_fallback_role_name", "listitem"),
            "blacklisted_roles": blr_parsed,
            # Theme/app hot-path config
            "volume": user_config["volume"],
            "typing_sounds": user_config.get("typing_sounds", True),
            "typing_sounds_edit_only": user_config.get("typing_sounds_edit_only", False),
            "typing_sounds_volume": user_config.get("typing_sounds_volume", 10),
            "typing_sound_pack": user_config.get("typing_sound_pack", "1blueSwitch"),
            "app_profiles_enabled": user_config.get("app_profiles_enabled", False),
            "disabled_apps_suppress_categories": user_config.get("disabled_apps_suppress_categories", "{}"),
            "clipboard_volume": user_config.get("clipboard_volume", 20),
            "clipboard_enabled": user_config.get("clipboard_enabled", True),
            # System sounds
            "sys_status_enabled": user_config.get("sys_status_enabled", True),
            "sys_ac_enabled": user_config.get("sys_ac_enabled", True),
            "sys_battery_enabled": user_config.get("sys_battery_enabled", True),
            "sys_usb_enabled": user_config.get("sys_usb_enabled", True),
            "sys_volume_enabled": user_config.get("sys_volume_enabled", True),
            "sys_network_enabled": user_config.get("sys_network_enabled", True),
            "sys_wake_enabled": user_config.get("sys_wake_enabled", True),
            "sys_status_volume": user_config.get("sys_status_volume", 20),
            "enable_audio_themes": user_config.get("enable_audio_themes", True),
            "progress_pan_mode": user_config.get("progress_pan_mode", "progress"),
            "progress_pan_range": user_config.get("progress_pan_range", 180),
            "progress_pitch_shift": user_config.get("progress_pitch_shift", True),
            # Audio ducking config
            "audio_ducking_enabled": user_config.get("audio_ducking_enabled", True),
            "audio_ducking_volume": user_config.get("audio_ducking_volume", 30),
            "ducking_categories": user_config.get("ducking_categories", ""),
            # unspoken player config (rarely changes mid-session)
            "output_mode": user_config.get("output_mode", "stereo"),
            "typing_sounds_spatial": user_config.get("typing_sounds_spatial", True),
            "typing_sounds_spatial_smart": user_config.get("typing_sounds_spatial_smart", True),
            "UnspokenReverb": unspoken_cfg.get("Reverb", False),
            "SmoothPanning": unspoken_cfg.get("SmoothPanning", True),
            "noSounds": unspoken_cfg.get("noSounds", False),
            "TrimSilence": unspoken_cfg.get("TrimSilence", False),
            "TrimSilenceThreshold": unspoken_cfg.get("TrimSilenceThreshold", -50),
            "SmartVolume": unspoken_cfg.get("SmartVolume", False),
            "SmartVolumePeak": unspoken_cfg.get("SmartVolumePeak", 0.8),
            "SmoothEnvelope": unspoken_cfg.get("SmoothEnvelope", False),
            "SmoothEnvelopeAttack": unspoken_cfg.get("SmoothEnvelopeAttack", 5),
            "SmoothEnvelopeRelease": unspoken_cfg.get("SmoothEnvelopeRelease", 50),
            "NoiseGate": unspoken_cfg.get("NoiseGate", False),
            "NoiseGateThreshold": unspoken_cfg.get("NoiseGateThreshold", -60),
            "NoiseGateAttack": unspoken_cfg.get("NoiseGateAttack", 0.01),
            "NoiseGateRelease": unspoken_cfg.get("NoiseGateRelease", 0.1),
            "BassBoost": unspoken_cfg.get("BassBoost", False),
            "BassBoostGain": unspoken_cfg.get("BassBoostGain", 6),
            "BassBoostCutoff": unspoken_cfg.get("BassBoostCutoff", 150),
            "HRTF": unspoken_cfg.get("HRTF", False),
            "AudioCache": unspoken_cfg.get("AudioCache", True),
            "enable_ffmpeg": user_config.get("enable_ffmpeg", False),
        }
        self.player._cached_config = self._cached_config
        if self._system_monitor is not None:
            self._system_monitor._cached_config = self._cached_config
        from .emoji_handler import refreshCachedConfig as _refreshEmojiConfig
        _refreshEmojiConfig()
        from .phoneticPunctuation import refreshCachedConfig as _refreshPpConfig
        _refreshPpConfig()
        from .frenzy import refreshFrenzyCachedConfig
        refreshFrenzyCachedConfig()
        from .commands import refreshCommandsCachedConfig
        refreshCommandsCachedConfig()
        from . import utils
        utils._set_cached_output_mode(self._cached_config.get("output_mode", "stereo"))
        utils.refreshPpConfigCache()
        from . import sentenceNavEngine
        sentenceNavEngine._refresh_doc_formatting()
        from .browserNavEngine import _bne_refresh_doc_formatting
        _bne_refresh_doc_formatting()
        from .browserNavEngine.addonConfig import refreshBNEConfigCache
        refreshBNEConfigCache()

    def _start_system_status_monitoring(self):
        try:
            from .systemStatus import SystemStatusMonitor
            self._system_monitor = SystemStatusMonitor(self._play_system_sound, self._cached_config)
            self._system_monitor.start()
        except Exception as e:
            log.debugWarning(f"Failed to start system status monitor: {e}")

    def _is_app_disabled_for_category(self, category):
        app_name = getattr(self, '_current_app_name', None)
        if not app_name or not self.disabled_apps:
            return False
        if not any(p in app_name.lower() for p in self.disabled_apps):
            return False
        from .utils import is_sound_suppressed
        return is_sound_suppressed(category)

    def _play_system_sound(self, sound_key):
        if not self._cached_config.get("sys_status_enabled", True):
            return
        if not self.enabled or self.active_theme is None:
            return
        cfg = self._cached_config
        if sound_key == SpecialProps.sys_ac_plug or sound_key == SpecialProps.sys_ac_unplug:
            if not cfg.get("sys_ac_enabled", True):
                return
        elif sound_key in (SpecialProps.sys_battery_low, SpecialProps.sys_battery_critical, SpecialProps.sys_battery_full):
            if not cfg.get("sys_battery_enabled", True):
                return
        elif sound_key in (SpecialProps.sys_usb_plug, SpecialProps.sys_usb_unplug):
            if not cfg.get("sys_usb_enabled", True):
                return
        elif sound_key in (SpecialProps.sys_volume_plug, SpecialProps.sys_volume_unplug):
            if not cfg.get("sys_volume_enabled", True):
                return
        elif sound_key in (SpecialProps.sys_network_connect, SpecialProps.sys_network_disconnect):
            if not cfg.get("sys_network_enabled", True):
                return
        elif sound_key in (SpecialProps.sys_wake, SpecialProps.sys_sleep):
            if not cfg.get("sys_wake_enabled", True):
                return
        if self._is_app_disabled_for_category("theme_sounds"):
            return
        theme = self.get_theme_for_app(getattr(self, '_current_app_name', None))
        if not theme:
            return
        sounds = theme.sounds
        sound_obj = sounds.get(sound_key)
        if sound_obj is None:
            return
        self.player.play({"name": str(sound_key.value), "role": 0, "system_sound": True, "volume_override": cfg.get("sys_status_volume", 20) / 100.0}, sound_obj)

    def play(self, obj_info, sound, _pre_resolved_theme=None):
        """
        Play a themed sound.  obj_info is a plain dict (no COM object).
        _pre_resolved_theme may be passed from playObject() to skip a redundant lookup.
        """
        force_3d = obj_info.get("force_3d", False) if isinstance(obj_info, dict) else False
        if not force_3d and (not self.enabled or (self.active_theme is None)):
            return

        if not force_3d and self._is_app_disabled_for_category("theme_sounds"):
            return

        if _pre_resolved_theme is not None:
            theme = _pre_resolved_theme
        else:
            app = obj_info.get("foreground_app") if isinstance(obj_info, dict) else getattr(self, '_current_app_name', None)
            theme = self.get_theme_for_app(app)
            if not theme:
                theme = self.active_theme

        if not theme:
            return

        sounds = theme.sounds
        sound_obj = sounds.get(sound)
        # System sounds must not fall back to any other sound
        if sound_obj is None and isinstance(obj_info, dict) and obj_info.get("system_sound"):
            return
        fl_cfg = self._cached_config
        if sound_obj is None and isinstance(obj_info, dict):
            role = obj_info.get("role", 0)
            if role and sound in (SpecialProps.first, SpecialProps.last):
                fb = fl_cfg["firstlast_fallback"]
                if fb == "role":
                    sound_obj = sounds.get(role)
                elif fb == "first_available" and sounds:
                    sound_obj = next(iter(sounds.values()))
                elif fb == "custom_role":
                    name = fl_cfg["first_fallback_role_name" if sound == SpecialProps.first else "last_fallback_role_name"]
                    target = role_name_to_int.get(name)
                    if target is not None:
                        sound_obj = sounds.get(target)
        if sound_obj is None and force_3d:
            sound_obj = sounds.get(controlTypes.Role.BUTTON)
            if sound_obj is None and sounds:
                sound_obj = next(iter(sounds.values()))
        if sound_obj is None and sounds:
            fb = fl_cfg["general_fallback"]
            if fb == "role":
                snd_role = obj_info.get("role", 0) if isinstance(obj_info, dict) else 0
                if snd_role:
                    sound_obj = sounds.get(snd_role)
            if sound_obj is None and fb in ("role", "first_available"):
                sound_obj = next(iter(sounds.values()))
            elif fb == "custom_role":
                name = fl_cfg["general_fallback_role_name"]
                target = role_name_to_int.get(name)
                if target is not None:
                    sound_obj = sounds.get(target)
        if sound_obj is None:
            return
        self.player.play(obj_info, sound_obj)

    def get_theme_for_app(self, app_name):
        with self._config_lock:
            if not app_name or not self._cached_config.get("app_profiles_enabled", False):
                return self.active_theme
            app_name = app_name.lower()
            profile = self._app_profiles_cache.get(app_name)
            target_folder = profile.get("theme") if isinstance(profile, dict) else profile
            if target_folder and self.active_theme is not None:
                if target_folder == self.active_theme.folder:
                    return self.active_theme
                if target_folder in self._theme_cache:
                    return self._theme_cache[target_folder]
            else:
                return self.active_theme
        # Lock released before disk I/O / theme.load
        theme = self.get_theme_from_folder(target_folder)
        if theme and theme.exists():
            theme.load(self.player)
            with self._config_lock:
                # Re-check cache (another thread may have loaded it)
                if target_folder not in self._theme_cache:
                    if len(self._theme_cache) >= 64:
                        self._theme_cache.pop(next(iter(self._theme_cache)))
                    self._theme_cache[target_folder] = theme
            return theme
        return self.active_theme

    def play_theme_sound(self, sound_name, angle_x=0, angle_y=0):
        if not self.enabled or (self.active_theme is None):
            return False
            
        if self._is_app_disabled_for_category("theme_sounds"):
            return False

        theme = self.get_theme_for_app(getattr(self, '_current_app_name', None))
        if not theme:
            return False

        if not any(sound_name.endswith('.' + ext) for ext in SUPPORTED_FILE_TYPES):
            sound_name += '.wav'

        sound_path = os.path.join(theme.directory, sound_name)

        # Check pre-indexed files in memory to eliminate Disk I/O
        if sound_name.lower() in getattr(theme, 'available_files', set()):
            self.player.play_file(
                sound_path,
                volume=self._cached_config.get("volume", 50),
                audio3d=bool(angle_x or angle_y),
                angle_x=angle_x,
                angle_y=angle_y
            )
            return True
        return False

    def get_earcon_angles(self):
        try:
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

    def play_clipboard_sound(self, special_prop, volume=None):
        if not self.enabled or self.active_theme is None:
            return False
        theme = self.active_theme
        sound_obj = theme.sounds.get(special_prop)
        if sound_obj is None:
            return False
        vol = (volume if volume is not None
               else self._cached_config.get("clipboard_volume", 20))
        self.player.play(
            {"name": str(special_prop.value), "role": 0, "system_sound": True,
             "volume_override": vol / 100.0},
            sound_obj
        )
        return True

    def get_typing_pack_for_app(self, app_name):
        with self._config_lock:
            global_pack = self._cached_config.get("typing_sound_pack", "1blueSwitch")
            if not app_name or not self._cached_config.get("app_profiles_enabled", False):
                return global_pack
            app_name = app_name.lower()
            profile = self._app_profiles_cache.get(app_name)
            if isinstance(profile, dict):
                pack = profile.get("typing_pack")
                if pack:
                    return pack
            return global_pack

    def play_typing_sound(self, ch=None, vkCode=None, extended=None):
        if not self._cached_config.get("typing_sounds", True):
            return
        if not self.enabled or (self.active_theme is None):
            return
            
        # Debounce: prevent same key sound from playing twice rapidly (keyDown + typedCharacter overlap)
        now = time.monotonic()
        if (now - self._last_typing_time) < 0.05 and self._last_typing_vk == vkCode:
            return
        self._last_typing_time = now
        self._last_typing_vk = vkCode
            
        foreground_app = getattr(self, '_current_app_name', None)
        if self._is_app_disabled_for_category("typing_sounds"):
            return

        theme = self.get_theme_for_app(foreground_app)

        # 1. Check if the active theme has its own typingSounds folder (cached)
        theme_typing_dir = os.path.join(theme.directory, "typingSounds") if theme else None
        typing_dir = None
        
        if theme_typing_dir:
            _tc_key = ("isdir", theme_typing_dir)
            with _typing_dir_cache_lock:
                _tcached = _typing_dir_cache.get(_tc_key)
            if _tcached is None:
                _tcached = os.path.isdir(theme_typing_dir)
                with _typing_dir_cache_lock:
                    if len(_typing_dir_cache) > 32:
                        _typing_dir_cache.pop(next(iter(_typing_dir_cache)))
                    _typing_dir_cache[_tc_key] = _tcached
            if _tcached:
                typing_dir = theme_typing_dir
        
        if typing_dir is None:
            # 2. Fall back to the globally selected typing pack or app-specific pack
            typing_pack = self.get_typing_pack_for_app(foreground_app)
            typing_dir = os.path.join(os.path.dirname(__file__), "typingSounds", typing_pack)
        
        sound_path = None
        if typing_dir:
            with _typing_dir_cache_lock:
                cache = _typing_dir_cache.get(typing_dir)
            if cache is None:
                if os.path.isdir(typing_dir):
                    files = [f for f in os.listdir(typing_dir) if f.lower().endswith(('.wav', '.ogg', '.mp3'))]
                    cache = {'files': files}
                else:
                    cache = {'files': []}
                with _typing_dir_cache_lock:
                    if len(_typing_dir_cache) > 32:
                        _typing_dir_cache.pop(next(iter(_typing_dir_cache)))
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
                volume=self._cached_config.get("typing_sounds_volume", 10),
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
            folder_name = os.path.basename(os.path.normpath(theme_pack))
            if folder_name.lower().endswith(".zip"):
                folder_name = folder_name[:-4]
            safe_name = cls._sanitize_folder_name(folder_name)
            target_path = os.path.join(THEMES_DIR, safe_name)
            if os.path.isdir(target_path):
                shutil.rmtree(target_path)
            if safe_name != os.path.basename(identified_path):
                os.rename(identified_path, target_path)
            info = {"name": folder_name, "author": "Unknown", "summary": folder_name}
            cls.write_info_file(os.path.join(target_path, INFO_FILE_NAME), info)
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
    typingSoundsDir = os.path.join(os.path.dirname(__file__), "typingSounds")
    if os.path.isdir(typingSoundsDir):
        packs = [d for d in os.listdir(typingSoundsDir) if os.path.isdir(os.path.join(typingSoundsDir, d))]
        if packs:
            return packs
    return ["1blueSwitch"]
