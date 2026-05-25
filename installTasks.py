import os
import shutil
import globalVars
import addonHandler

addonHandler.initTranslation()

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
