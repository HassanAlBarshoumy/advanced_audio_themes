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


def _checkConflictingAddons():
	conflicting_ids = {
		"navSounds": "Navigation Sound Effects",
		"SentenceNav": "SentenceNav",
		"browserNav": "BrowserNav",
		"phoneticPunctuation": "Earcons and Speech Rules",
		"audiothemes": "Audio Themes (legacy)",
		"audio_themes_NG": "Audio Themes NG (legacy)",
	}
	found = {}
	for addon in addonHandler.getAvailableAddons():
		if addon.name in conflicting_ids and not addon.isPendingRemove:
			found[addon.name] = addon
	if not found:
		return
	gui.mainFrame.prePopup()
	dlg = wx.Dialog(gui.mainFrame, title=_("Conflicting Add-ons"))
	sizer = wx.BoxSizer(wx.VERTICAL)
	label = wx.StaticText(dlg, label=_(
		"The following add-ons are now included in Advanced Audio Themes.\n"
		"Select the ones you want to remove to prevent conflicts:"
	))
	sizer.Add(label, flag=wx.ALL | wx.EXPAND, border=10)
	names = list(found.keys())
	display_names = [conflicting_ids[n] for n in names]
	clb = wx.CheckListBox(dlg, choices=display_names)
	for i in range(len(display_names)):
		clb.Check(i)
	sizer.Add(clb, proportion=1, flag=wx.ALL | wx.EXPAND, border=10)
	btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
	ok_btn = wx.Button(dlg, wx.ID_OK, _("Remove selected"))
	cancel_btn = wx.Button(dlg, wx.ID_CANCEL, _("Skip"))
	btn_sizer.Add(ok_btn, flag=wx.ALL, border=5)
	btn_sizer.Add(cancel_btn, flag=wx.ALL, border=5)
	sizer.Add(btn_sizer, flag=wx.ALIGN_CENTER | wx.ALL, border=10)
	dlg.SetSizer(sizer)
	dlg.SetSize((500, 350))
	if dlg.ShowModal() == wx.ID_OK:
		for i, name in enumerate(names):
			if clb.IsChecked(i):
				found[name].requestRemove()
	dlg.Destroy()
	gui.mainFrame.postPopup()


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
