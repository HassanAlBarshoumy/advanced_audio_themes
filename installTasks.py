import os
import shutil
import globalVars
import addonHandler
import gui
import wx
import config
import json

try:
    addonHandler.initTranslation()
except AttributeError:
    pass


CONFLICT_PENDING_FILE = os.path.join(
	globalVars.appArgs.configPath, "audio-themes", ".pending_conflict.json"
)


def _isPendingRemove(addon):
	"""Return True only when the add-on is definitely marked for removal.

	``addonHandler.Addon`` has no ``isPendingRemove`` attribute (only
	``isPendingInstall``); ``isPendingRemove`` lives on the Add-on Store models
	in ``addonStore``. Reading it unconditionally raises ``AttributeError``,
	which NVDA treats as an ``onInstall`` failure and rolls the add-on back.
	Probe both the real NVDA API and the store-style flag, defaulting to False.
	"""
	try:
		if getattr(addon, "isPendingInstall", False):
			return True
		return bool(getattr(addon, "isPendingRemove", False))
	except Exception:
		return False


def _writeConflictFile(found):
	"""Persist the conflicting add-on ids so the plugin can offer removal later.

	Best-effort: never raises, so a read-only config directory can never turn
	into an ``onInstall`` failure (which would make NVDA roll the add-on back).
	"""
	try:
		os.makedirs(os.path.dirname(CONFLICT_PENDING_FILE), exist_ok=True)
		with open(CONFLICT_PENDING_FILE, "w") as f:
			json.dump(found, f)
	except Exception:
		pass


def _checkConflictingAddons():
	try:
		conflicting_ids = (
			"navSounds", "SentenceNav", "browserNav",
			"phoneticPunctuation", "audiothemes", "audio_themes_NG",
		)
		found = [
			addon.name for addon in addonHandler.getAvailableAddons()
			if addon.name in conflicting_ids and not _isPendingRemove(addon)
		]
	except Exception:
		# A failure while enumerating add-ons must never abort the install.
		return
	if not found:
		return
	_writeConflictFile(found)





def onInstall():
	# NVDA treats ANY exception raised here as a failed installation and
	# rolls the add-on back (addonHandler.installAddonBundle calls
	# completeRemove on failure). Migrating themes is best-effort, so every
	# filesystem operation is guarded and the conflict check always runs.
	try:
		old_paths = [
			os.path.join(globalVars.appArgs.configPath, "addons", "audiothemes", "globalPlugins", "audiothemes", "Themes"),
			os.path.join(globalVars.appArgs.configPath, "addons", "audio_themes_NG", "globalPlugins", "audiothemes", "Themes")
		]
		new_path = os.path.join(globalVars.appArgs.configPath, "audio-themes")

		if not os.path.exists(new_path):
			os.makedirs(new_path)

		for path in old_paths:
			if os.path.exists(path):
				try:
					theme_names = os.listdir(path)
				except OSError:
					continue
				for theme in theme_names:
					src_theme_path = os.path.join(path, theme)
					dest_theme_path = os.path.join(new_path, theme)
					try:
						if os.path.isdir(src_theme_path):
							if not os.path.exists(dest_theme_path):
								shutil.copytree(src_theme_path, dest_theme_path)
							else:
								for item in os.listdir(src_theme_path):
									# removed skip of .ogg
									s_item = os.path.join(src_theme_path, item)
									d_item = os.path.join(dest_theme_path, item)
									if os.path.isdir(s_item):
										if not os.path.exists(d_item):
											shutil.copytree(s_item, d_item)
									else:
										shutil.copy2(s_item, d_item)
					except (OSError, shutil.Error):
						# A single unreadable theme must not abort the migration.
						continue

		# Copy Default theme from addon to the new location.
		addon_themes_path = os.path.join(os.path.dirname(__file__), "globalPlugins", "audiothemes", "Themes")
		addon_default_theme_path = os.path.join(addon_themes_path, "Default")
		dest_default_theme_path = os.path.join(new_path, "Default")
		if os.path.exists(addon_default_theme_path):
			if not os.path.exists(dest_default_theme_path):
				try:
					shutil.copytree(addon_default_theme_path, dest_default_theme_path)
				except (OSError, shutil.Error):
					pass

		# If the active theme in config doesn't exist, reset to Default
		active = config.conf.get("audiothemes", {}).get("active_theme", "Default")
		if active and not os.path.exists(os.path.join(new_path, active)):
			config.conf["audiothemes"]["active_theme"] = "Default"
	except Exception:
		pass

	try:
		_checkConflictingAddons()
	except Exception:
		pass
