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

def _checkConflictingAddons():
	conflicting_ids = (
		"navSounds", "SentenceNav", "browserNav",
		"phoneticPunctuation", "audiothemes", "audio_themes_NG",
	)
	found = [
		addon.name for addon in addonHandler.getAvailableAddons()
		if addon.name in conflicting_ids and not addon.isPendingRemove
	]
	if not found:
		return
	try:
		with open(CONFLICT_PENDING_FILE, "w") as f:
			json.dump(found, f)
	except Exception:
		pass





def onInstall():
	old_paths = [
		os.path.join(globalVars.appArgs.configPath, "addons", "audiothemes", "globalPlugins", "audiothemes", "Themes"),
		os.path.join(globalVars.appArgs.configPath, "addons", "audio_themes_NG", "globalPlugins", "audiothemes", "Themes")
	]
	new_path = os.path.join(globalVars.appArgs.configPath, "audio-themes")

	if not os.path.exists(new_path):
		os.makedirs(new_path)

	for path in old_paths:
		if os.path.exists(path):
			for theme in os.listdir(path):
				src_theme_path = os.path.join(path, theme)
				dest_theme_path = os.path.join(new_path, theme)
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

	# Copy Default theme from addon to the new location.
	addon_themes_path = os.path.join(os.path.dirname(__file__), "globalPlugins", "audiothemes", "Themes")
	addon_default_theme_path = os.path.join(addon_themes_path, "Default")
	dest_default_theme_path = os.path.join(new_path, "Default")
	if os.path.exists(addon_default_theme_path):
		if not os.path.exists(dest_default_theme_path):
			shutil.copytree(addon_default_theme_path, dest_default_theme_path)

	# If the active theme in config doesn't exist, reset to Default
	active = config.conf.get("audiothemes", {}).get("active_theme", "Default")
	if active and not os.path.exists(os.path.join(new_path, active)):
		config.conf["audiothemes"]["active_theme"] = "Default"

	_checkConflictingAddons()
