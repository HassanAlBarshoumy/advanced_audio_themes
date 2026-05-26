# coding: utf-8


# This file is covered by the GNU General Public License.

import wx
import os
import json
import random
import threading
import zipfile
import shutil
import logging
import time as _time

import controlTypes
import config
import gui
import nvwave

from .handler import AudioThemesHandler, audiotheme_changed, THEMES_DIR
from .update_checker import check_for_updates
log = logging.getLogger(__name__)

import addonHandler
try:
    addonHandler.initTranslation()
except AttributeError:
    pass


from gui.settingsDialogs import SettingsPanel

class DummyEvent:
    def __init__(self, is_checked):
        self._is_checked = is_checked

    def IsChecked(self):
        return self._is_checked

class RoleSelectionDialog(wx.Dialog):
    def __init__(self, parent):
        super(RoleSelectionDialog, self).__init__(parent, title=_("Select Spoken Roles"))
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        
        # Translators: label for the list of roles to select which ones are spoken
        label = wx.StaticText(self, label=_("Select the roles you want NVDA to speak (if the global speak roles setting is enabled):"))
        mainSizer.Add(label, 0, wx.ALL | wx.EXPAND, 10)
        
        self.rolesListBox = wx.ListView(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_NO_HEADER)
        self.rolesListBox.EnableCheckBoxes(True)
        self.rolesListBox.InsertColumn(0, _("Roles"), width=360)
        mainSizer.Add(self.rolesListBox, 1, wx.ALL | wx.EXPAND, 10)
        
        self.role_ids = []
        blacklisted = getattr(parent, 'blacklisted_roles', config.conf["audiothemes"].get("blacklisted_roles", []))
        
        idx = 0
        for role_id, role_label in controlTypes.roleLabels.items():
            if role_id >= 10000:  # Skip states (STATE_OFFSET in handler)
                continue
            self.role_ids.append(role_id)
            self.rolesListBox.InsertItem(idx, role_label)
            if role_id not in blacklisted:
                self.rolesListBox.CheckItem(idx, True)
            idx += 1
                
        # Select All / Deselect All buttons
        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        selectAllBtn = wx.Button(self, label=_("Select All"))
        selectAllBtn.Bind(wx.EVT_BUTTON, lambda e: self.toggleAll(True))
        deselectAllBtn = wx.Button(self, label=_("Deselect All"))
        deselectAllBtn.Bind(wx.EVT_BUTTON, lambda e: self.toggleAll(False))
        btnSizer.Add(selectAllBtn, 0, wx.RIGHT, 5)
        btnSizer.Add(deselectAllBtn, 0)
        mainSizer.Add(btnSizer, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        
        # Standard buttons
        stdBtns = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        mainSizer.Add(stdBtns, 0, wx.ALL | wx.ALIGN_RIGHT, 10)
        
        self.SetSizer(mainSizer)
        self.SetMinSize((400, 500))
        self.Fit()
        
    def toggleAll(self, state):
        for i in range(self.rolesListBox.GetItemCount()):
            self.rolesListBox.CheckItem(i, state)
            
    def getBlacklistedRoles(self):
        blacklisted = []
        for i in range(self.rolesListBox.GetItemCount()):
            if not self.rolesListBox.IsItemChecked(i):
                blacklisted.append(self.role_ids[i])
        return blacklisted

class AudioThemesSettingsPanel(SettingsPanel):
    # Translators: Title for the settings panel in NVDA's multi-category settings
    title = _("Advanced Audio Themes")

    def makeSettings(self, settingsSizer):
        self.notebook = wx.Notebook(self)

        # Tab 1: General Settings
        self.generalPage = wx.Panel(self.notebook)
        self.setupGeneralPage(self.generalPage)
        self.notebook.AddPage(self.generalPage, _("General"))

        # Tab 1.5: Audio Engine Settings
        self.audioEnginePage = wx.Panel(self.notebook)
        self.setupAudioEnginePage(self.audioEnginePage)
        self.notebook.AddPage(self.audioEnginePage, _("Audio Engine"))

        # Tab 2: Reverb Settings
        self.reverbPage = wx.Panel(self.notebook)
        self.setupReverbPage(self.reverbPage)
        self.notebook.AddPage(self.reverbPage, _("Reverb"))

        # Tab 3: Earcons and Speech Rules
        from .phoneticPunctuationGui import RulesDialog
        self.rulesPage = RulesDialog(self.notebook)
        self.notebook.AddPage(self.rulesPage, _("Earcons & Speech Rules"))

        # Tab 4: Miscellaneous
        self.miscPage = wx.Panel(self.notebook)
        self.setupMiscPage(self.miscPage)
        self.notebook.AddPage(self.miscPage, _("Miscellaneous"))

        # Tab 5: Speech Order (Control Type Before Label)
        self.speechOrderPage = wx.Panel(self.notebook)
        self.setupSpeechOrderPage(self.speechOrderPage)
        self.notebook.AddPage(self.speechOrderPage, _("Speech Order"))

        # Tab 6: App Profiles
        self.appProfilesPage = wx.Panel(self.notebook)
        self.setupAppProfilesPage(self.appProfilesPage)
        self.notebook.AddPage(self.appProfilesPage, _("App Profiles"))

        # Tab 7: QuickSearch Websites & Bookmarks
        from .browserNavEngine.quickJump import SettingsDialog as QuickJumpSettingsDialog
        self.quickJumpPage = QuickJumpSettingsDialog(self.notebook)
        self.notebook.AddPage(self.quickJumpPage, _("QuickSearch & Bookmarks"))

        settingsSizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 5)

        self._initialize_at_state()
        self._maintain_state()

    def setupGeneralPage(self, page):
        # Translators: label for the checkbox to enable or disable audio themes
        self.enableThemesCheckbox = wx.CheckBox(page, -1, _("Enable audio themes"))
        self.innerPanel = innerPanel = wx.Panel(page)
        # Translators: label for a combobox containing a list of installed audio themes
        installedThemesLabel = wx.StaticText(innerPanel, -1, _("Select theme:"))
        self.installedThemesChoice = wx.Choice(innerPanel, -1)
        # Translators: label for a button to show info about an audio theme
        self.aboutThemeButton = wx.Button(innerPanel, -1, _("&About"))
        # Translators: label for a button to remove an audio theme
        self.removeThemeButton = wx.Button(innerPanel, -1, _("&Remove"))
        # Translators: label for a button to add a new audio theme
        self.addThemeButton = wx.Button(innerPanel, -1, _("Add &New..."))
        # Translators: label for a button to open the themes store
        self.storeThemeButton = wx.Button(innerPanel, -1, _("Themes Store"))
        # Translators: label for a button to open the Theme Studio
        self.blenderThemeButton = wx.Button(innerPanel, -1, _("Theme Studio"))
        # Translators: label for a button to preview the selected theme
        self.previewThemeButton = wx.Button(innerPanel, -1, _("P&review"))
        # Translators: label for a checkbox to toggle the 3D mode
        self.play3dCheckbox = wx.CheckBox(innerPanel, -1, _("Play sounds in 3D mode"))
        # Translators: label for a checkbox to toggle the speaking of object role
        self.speakRoleCheckbox = wx.CheckBox(
            innerPanel, -1, _("Speak roles such as button, edit box , link etc. ")
        )
        # Translators: label for a checkbox to toggle the use of audio themes during say all
        self.useInSayAllCheckbox = wx.CheckBox(
            innerPanel, -1, _("Speak roles during say all")
        )
        # Translators: label for a checkbox to toggle whether the volume of this add-on should follow the synthesizer volume
        self.useSynthVolumeCheckbox = wx.CheckBox(
            innerPanel, -1, _("Use speech synthesizer volume")
        )
        # Translators: label for a slider to set the volume of this add-on
        volumeLabel = wx.StaticText(innerPanel, -1, _("Audio themes volume:"))
        self.volumeSlider = wx.Slider(
            innerPanel, -1, minValue=0, maxValue=100, name=_("Audio themes volume")
        )
        innerSizer = wx.BoxSizer(wx.VERTICAL)
        themesListSizer = wx.BoxSizer(wx.HORIZONTAL)
        themesListSizer.AddMany(
            [
                (installedThemesLabel, 1, wx.LEFT | wx.TOP | wx.BOTTOM, 10),
                (self.installedThemesChoice, 2, wx.EXPAND | wx.ALL, 10),
            ]
        )
        actionSizer = wx.BoxSizer(wx.HORIZONTAL)
        actionSizer.AddMany(
            [
                (self.aboutThemeButton, 1, wx.ALL, 5),
                (self.removeThemeButton, 1, wx.ALL, 5),
                (self.addThemeButton, 1, wx.ALL, 5),
                (self.previewThemeButton, 1, wx.ALL, 5),
                (self.storeThemeButton, 1, wx.ALL, 5),
                (self.blenderThemeButton, 1, wx.ALL, 5),
            ]
        )
        innerSizer.AddMany(
            [(themesListSizer, 1, wx.EXPAND, 10), (actionSizer, 1, wx.ALIGN_CENTER, 10)]
        )
        innerSizer.AddSpacer(10)
        # Audio Ducking
        self.audioDuckingCheckbox = wx.CheckBox(innerPanel, -1, _("Audio Ducking (lower volume when NVDA speaks)"))
        duckingVolLabel = wx.StaticText(innerPanel, -1, _("Ducked Volume (%):"))
        self.audioDuckingVolumeSlider = wx.Slider(innerPanel, -1, minValue=1, maxValue=100)
        
        # Speak Roles Checkbox (alone)
        # Say All Roles Sizer
        sayAllRolesSizer = wx.BoxSizer(wx.HORIZONTAL)
        sayAllRolesSizer.Add(self.useInSayAllCheckbox, 0, wx.ALIGN_CENTER_VERTICAL)
        self.selectRolesButton = wx.Button(innerPanel, -1, _("Select Roles..."))
        self.selectRolesButton.Bind(wx.EVT_BUTTON, self.onSelectRoles)
        sayAllRolesSizer.Add(self.selectRolesButton, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        
        innerSizer.AddMany(
            [
                (self.play3dCheckbox, 0, wx.ALL, 5),
                (self.speakRoleCheckbox, 0, wx.ALL, 5),
                (sayAllRolesSizer, 0, wx.ALL, 5),
                (self.useSynthVolumeCheckbox, 0, wx.ALL, 5),
                (volumeLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 10),
                (self.volumeSlider, 0, wx.BOTTOM | wx.LEFT | wx.RIGHT, 5),
                (self.audioDuckingCheckbox, 0, wx.ALL, 5),
                (duckingVolLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 10),
                (self.audioDuckingVolumeSlider, 0, wx.BOTTOM | wx.LEFT | wx.RIGHT, 5),
            ]
        )
        
        innerSizer.Fit(innerPanel)
        
        # Application Blacklist
        disabledAppsLabel = wx.StaticText(innerPanel, -1, _("Disable Audio Themes in these applications (comma separated):"))
        self.disabledAppsEdit = wx.TextCtrl(innerPanel, -1, value="")
        innerSizer.AddMany([
            (disabledAppsLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 10),
            (self.disabledAppsEdit, 0, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)
        ])
        
        # Typing Sounds Group
        self.typingSoundsCheckbox = wx.CheckBox(innerPanel, -1, _("Enable typing sounds"))
        self.typingSoundsEditOnlyCheckbox = wx.CheckBox(innerPanel, -1, _("Play typing sounds only in edit boxes"))
        typingVolumeLabel = wx.StaticText(innerPanel, -1, _("Typing sounds volume:"))
        self.typingSoundsVolumeSlider = wx.Slider(innerPanel, -1, minValue=0, maxValue=100)
        
        typingPackLabel = wx.StaticText(innerPanel, -1, _("Typing sound pack:"))
        self.typingPackChoices = []
        typingSoundsDir = os.path.join(os.path.dirname(__file__), "typingSounds")
        if os.path.isdir(typingSoundsDir):
            self.typingPackChoices = [d for d in os.listdir(typingSoundsDir) if os.path.isdir(os.path.join(typingSoundsDir, d))]
        if not self.typingPackChoices:
            self.typingPackChoices = ["1blueSwitch"]

        typingPackSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.typingPackCombobox = wx.Choice(innerPanel, -1, choices=self.typingPackChoices)
        self.aboutTypingSoundsButton = wx.Button(innerPanel, -1, _("&About"))
        typingPackSizer.Add(self.typingPackCombobox, 1, wx.EXPAND | wx.RIGHT, 5)
        typingPackSizer.Add(self.aboutTypingSoundsButton, 0, wx.ALL, 0)
        self.typingSoundsSpatialCheckbox = wx.CheckBox(innerPanel, -1, _("Enable spatial typing sounds (simulates a physical keyboard)"))
        self.typingSoundsSmartSpatialCheckbox = wx.CheckBox(innerPanel, -1, _("Smart spatial positioning (maps characters to their exact physical keys)"))

        typingSizer = wx.StaticBoxSizer(wx.VERTICAL, innerPanel, _("Typing Sounds"))
        typingSizer.AddMany([
            (self.typingSoundsCheckbox, 1, wx.ALL, 5),
            (self.typingSoundsEditOnlyCheckbox, 1, wx.ALL, 5),
            (self.typingSoundsSpatialCheckbox, 1, wx.ALL, 5),
            (self.typingSoundsSmartSpatialCheckbox, 1, wx.ALL, 5),
            (typingPackLabel, 1, wx.TOP | wx.LEFT | wx.RIGHT, 10),
            (typingPackSizer, 0, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 5),
            (typingVolumeLabel, 1, wx.TOP | wx.LEFT | wx.RIGHT, 10),
            (self.typingSoundsVolumeSlider, 1, wx.BOTTOM | wx.LEFT | wx.RIGHT, 5),
        ])
        innerSizer.Add(typingSizer, 0, wx.EXPAND | wx.ALL, 10)
        
        configActionSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.exportConfigButton = wx.Button(innerPanel, -1, _("E&xport Configuration..."))
        self.importConfigButton = wx.Button(innerPanel, -1, _("I&mport Configuration..."))
        self.checkUpdatesButton = wx.Button(innerPanel, -1, _("Check for &Updates..."))
        # Translators: label for a button to contact the author on Telegram
        self.telegramButton = wx.Button(innerPanel, -1, _("Contact on Telegram"))
        configActionSizer.AddMany(
            [
                (self.exportConfigButton, 1, wx.ALL, 5),
                (self.importConfigButton, 1, wx.ALL, 5),
                (self.checkUpdatesButton, 1, wx.ALL, 5),
                (self.telegramButton, 1, wx.ALL, 5),
            ]
        )
        innerSizer.Add(configActionSizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        innerPanel.SetSizer(innerSizer)
        innerSizer.Fit(innerPanel)
        
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(self.enableThemesCheckbox, 0, wx.ALL, 10)
        mainSizer.Add(innerPanel, 1, wx.EXPAND | wx.ALL, 10)
        page.SetSizer(mainSizer)

        # Bind events
        self.Bind(wx.EVT_BUTTON, self.onAbout, self.aboutThemeButton)
        self.Bind(wx.EVT_BUTTON, self.onRemove, self.removeThemeButton)
        self.Bind(wx.EVT_BUTTON, self.onAdd, self.addThemeButton)
        self.Bind(wx.EVT_BUTTON, self.onStoreClicked, self.storeThemeButton)
        self.Bind(wx.EVT_BUTTON, self.onBlenderTheme, self.blenderThemeButton)
        self.Bind(wx.EVT_BUTTON, self.onPreviewTheme, self.previewThemeButton)
        self.Bind(wx.EVT_BUTTON, self.onTelegram, self.telegramButton)
        self.Bind(wx.EVT_BUTTON, self.onAboutTypingSounds, self.aboutTypingSoundsButton)
        self.Bind(
            wx.EVT_CHECKBOX,
            lambda e: self.innerPanel.Enable(e.IsChecked()),
            self.enableThemesCheckbox,
        )
        self.Bind(
            wx.EVT_CHECKBOX,
            lambda e: self.volumeSlider.Enable(not e.IsChecked()),
            self.useSynthVolumeCheckbox,
        )
        self.Bind(
            wx.EVT_CHECKBOX,
            lambda e: self.audioDuckingVolumeSlider.Enable(e.IsChecked()),
            self.audioDuckingCheckbox,
        )
        self.Bind(
            wx.EVT_CHOICE, self.onThemeSelectionChanged, self.installedThemesChoice
        )
        self.Bind(
            wx.EVT_CHOICE, self.onTypingPackSelectionChanged, self.typingPackCombobox
        )
        self.Bind(
            wx.EVT_CHECKBOX,
            lambda e: self._update_typing_controls(),
            self.typingSoundsCheckbox,
        )
        self.Bind(wx.EVT_BUTTON, self.onExportConfig, self.exportConfigButton)
        self.Bind(wx.EVT_BUTTON, self.onImportConfig, self.importConfigButton)
        self.Bind(wx.EVT_BUTTON, self.onCheckUpdates, self.checkUpdatesButton)

    def onTypingPackSelectionChanged(self, event):
        pack = self.typingPackCombobox.GetStringSelection()
        if not pack: return
        typingSoundsDir = os.path.join(os.path.dirname(__file__), "typingSounds", pack)
        if not os.path.isdir(typingSoundsDir): return
        files = [f for f in os.listdir(typingSoundsDir) if f.lower().endswith(('.wav', '.ogg'))]
        if not files: return

        # Play a sequence of 3 rapid random keystrokes to simulate typing
        def play_preview():
            try:
                for _ in range(3):
                    f = random.choice(files)
                    nvwave.playWaveFile(os.path.join(typingSoundsDir, f), asynchronous=True)
                    _time.sleep(0.12)
            except Exception:
                log.debug("Preview playback interrupted")
        threading.Thread(target=play_preview).start()

    def onTelegram(self, event):
        import webbrowser
        webbrowser.open("https://t.me/HassanAlBarshoumy")

    def onAboutTypingSounds(self, event):
        pack = self.typingPackCombobox.GetStringSelection()
        if not pack:
            return
        typingSoundsDir = os.path.join(os.path.dirname(__file__), "typingSounds", pack)
        
        # Count sounds
        try:
            files = [f for f in os.listdir(typingSoundsDir) if f.lower().endswith(('.wav', '.ogg'))]
            count = len(files)
        except Exception:
            count = 0

        # Read info.json
        author = _("Unknown")
        description = ""
        info_path = os.path.join(typingSoundsDir, "info.json")
        if os.path.isfile(info_path):
            try:
                import json
                with open(info_path, "r", encoding="utf-8") as f:
                    info = json.load(f)
                author_val = info.get("author", "Unknown")
                # Translate Unknown if it's the literal string "Unknown"
                author = _("Unknown") if author_val == "Unknown" else author_val
                description = info.get("description", "")
            except Exception:
                pass
            
        msg = _("Name: {name}\nAuthor: {author}\nNumber of sounds: {count}\nLocation: {path}").format(
            name=pack, author=author, count=count, path=typingSoundsDir
        )
        if description:
            msg += f"\n\n{description}"
            
        wx.MessageBox(
            msg,
            _("About Typing Sound Pack"),
            style=wx.ICON_INFORMATION
        )

    def onBlenderTheme(self, event):
        from .studio.themes_blender import ThemeBlenderDialog
        themes = list(AudioThemesHandler().get_installed_themes())
        if not themes: return
        dlg = wx.SingleChoiceDialog(self, _("Select a theme to edit or remix:"), _("Theme Studio"), [t.name for t in themes])
        if dlg.ShowModal() == wx.ID_OK:
            sel = dlg.GetSelection()
            theme = themes[sel]
            blender_dlg = ThemeBlenderDialog(_("Theme Studio - ") + theme.name, theme)
            blender_dlg.ShowModal()
            blender_dlg.Destroy()
        dlg.Destroy()

    def _update_typing_controls(self, event=None):
        enabled = self.typingSoundsCheckbox.GetValue()
        self.typingSoundsEditOnlyCheckbox.Enable(enabled)
        self.typingSoundsSpatialCheckbox.Enable(enabled)
        spatial_enabled = self.typingSoundsSpatialCheckbox.GetValue()
        self.typingSoundsSmartSpatialCheckbox.Enable(enabled and spatial_enabled)
        self.typingPackCombobox.Enable(enabled)
        self.typingSoundsVolumeSlider.Enable(enabled)

    def setupAudioEnginePage(self, page):
        """Tab 1.5: Audio Engine Advanced Configuration"""
        engineSizer = wx.BoxSizer(wx.VERTICAL)

        # Smart Volume Normalization
        self.smartVolumeCheckbox = wx.CheckBox(page, -1, _("Smart Volume Normalization"))
        engineSizer.Add(self.smartVolumeCheckbox, 0, wx.ALL, 5)

        # Smooth Envelope
        self.smoothEnvelopeCheckbox = wx.CheckBox(page, -1, _("Smooth Envelope (Fade In/Out to prevent popping)"))
        engineSizer.Add(self.smoothEnvelopeCheckbox, 0, wx.ALL, 5)

        # Smooth Panning
        self.smoothPanningCheckbox = wx.CheckBox(page, -1, _("Smooth 3D Panning (Glide effect for moving objects)"))
        engineSizer.Add(self.smoothPanningCheckbox, 0, wx.ALL, 5)

        # RAM Caching
        self.audioCacheCheckbox = wx.CheckBox(page, -1, _("Enable RAM Caching (Improves performance and latency)"))
        engineSizer.Add(self.audioCacheCheckbox, 0, wx.ALL, 5)

        # Trim Silence
        self.trimSilenceCheckbox = wx.CheckBox(page, -1, _("Trim silence from beginning and end of sounds"))
        engineSizer.Add(self.trimSilenceCheckbox, 0, wx.ALL, 5)

        # Output Mode
        modeSizer = wx.BoxSizer(wx.HORIZONTAL)
        modeLabel = wx.StaticText(page, -1, _("Audio Output Mode:"))
        self.outputModeChoice = wx.Choice(page, -1, choices=[_("3D Spatial (Stereo)"), _("Centered (Mono)")])
        modeSizer.Add(modeLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        modeSizer.Add(self.outputModeChoice, 1, wx.EXPAND | wx.ALL, 0)
        engineSizer.Add(modeSizer, 0, wx.EXPAND | wx.ALL, 5)

        page.SetSizer(engineSizer)

    def setupReverbPage(self, page):
        reverbSizer = wx.BoxSizer(wx.VERTICAL)

        self.enableReverbCheckbox = wx.CheckBox(page, -1, _("Enable Reverb"))
        reverbSizer.Add(self.enableReverbCheckbox, 0, wx.ALL, 5)

        self.roomSizeLabel = wx.StaticText(page, -1, _("Room Size:"))
        self.roomSizeSlider = wx.Slider(page, -1, minValue=0, maxValue=100, name=_("Room Size"))
        reverbSizer.AddMany([
            (self.roomSizeLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5),
            (self.roomSizeSlider, 0, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)
        ])

        self.dampingLabel = wx.StaticText(page, -1, _("Damping:"))
        self.dampingSlider = wx.Slider(page, -1, minValue=0, maxValue=100, name=_("Damping"))
        reverbSizer.AddMany([
            (self.dampingLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5),
            (self.dampingSlider, 0, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)
        ])

        self.wetLevelLabel = wx.StaticText(page, -1, _("Wet Level:"))
        self.wetLevelSlider = wx.Slider(page, -1, minValue=0, maxValue=100, name=_("Wet Level"))
        reverbSizer.AddMany([
            (self.wetLevelLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5),
            (self.wetLevelSlider, 0, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)
        ])

        self.dryLevelLabel = wx.StaticText(page, -1, _("Dry Level:"))
        self.dryLevelSlider = wx.Slider(page, -1, minValue=0, maxValue=100, name=_("Dry Level"))
        reverbSizer.AddMany([
            (self.dryLevelLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5),
            (self.dryLevelSlider, 0, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)
        ])

        self.widthLabel = wx.StaticText(page, -1, _("Width:"))
        self.widthSlider = wx.Slider(page, -1, minValue=0, maxValue=100, name=_("Width"))
        reverbSizer.AddMany([
            (self.widthLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5),
            (self.widthSlider, 0, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)
        ])

        page.SetSizer(reverbSizer)

        self.Bind(
            wx.EVT_CHECKBOX,
            self.onEnableReverbCheckboxChanged,
            self.enableReverbCheckbox,
        )

    def onEnableReverbCheckboxChanged(self, event):
        enabled = self.enableReverbCheckbox.GetValue()
        
        self.roomSizeSlider.Enable(enabled)
        self.wetLevelSlider.Enable(enabled)
        self.dampingSlider.Enable(enabled)
        self.dryLevelSlider.Enable(enabled)
        self.widthSlider.Enable(enabled)

    def setupSpeechOrderPage(self, page):
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Translators: label for global announcement format
        helpLabel = wx.StaticText(page, -1, _("Global announcement format for all elements:"))
        sizer.Add(helpLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        
        self.ANNOUNCE_FORMATS = (
            ("0", _("Default (name, role then state)")),
            ("rsc", _("Role and state, then name (Role State Label)")),
            ("sc", _("State, then name (State Label)")),
        )
        
        announceFormatChoices = [name for fmt_code, name in self.ANNOUNCE_FORMATS]
        self.announceFormatChoice = wx.Choice(page, -1, choices=announceFormatChoices)
        sizer.Add(self.announceFormatChoice, 0, wx.EXPAND | wx.ALL, 5)
        
        # --- Per-role customization ---
        separator = wx.StaticLine(page)
        sizer.Add(separator, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 8)
        
        # Translators: label for per-role customization
        perRoleLabel = wx.StaticText(page, -1, _("Customize announcement format per role:"))
        sizer.Add(perRoleLabel, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        
        # Build role list
        self._role_list = []
        try:
            for role in controlTypes.Role:
                try:
                    label = role.displayString
                except Exception:
                    try:
                        label = controlTypes.role._roleLabels.get(role, None)
                    except Exception:
                        label = None
                if label:
                    self._role_list.append((role, label))
        except Exception as e:
            log.error(f"Error building role list: {e}")
        self._role_list.sort(key=lambda x: x[1])
        
        # Per-role format choices
        self._PER_ROLE_FORMATS = (
            ("global", _("Use global setting")),
            ("0", _("Default (name, role then state)")),
            ("rsc", _("Role and state, then name")),
            ("sc", _("State, then name")),
        )
        perRoleFormatNames = [name for code, name in self._PER_ROLE_FORMATS]
        
        # Search box for filtering roles
        searchSizer = wx.BoxSizer(wx.HORIZONTAL)
        searchLabel = wx.StaticText(page, -1, _("Search for a role:"))
        self.roleSearchEdit = wx.TextCtrl(page, -1, value="")
        searchSizer.Add(searchLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        searchSizer.Add(self.roleSearchEdit, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(searchSizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        
        # Scrolled panel for the per-role list
        self.scrolled = wx.ScrolledWindow(page, style=wx.VSCROLL | wx.BORDER_SIMPLE)
        self.scrolled.SetScrollRate(0, 20)
        self.scrolled.SetMinSize((-1, 200))
        self.scrollSizer = wx.FlexGridSizer(cols=2, vgap=4, hgap=8)
        self.scrollSizer.AddGrowableCol(1, 1)
        
        self._roleFormatChoices = {}
        self._roleRowControls = []  # To keep track of (label_ctrl, choice_ctrl, role_label_text)
        
        for role, label in self._role_list:
            roleLbl = wx.StaticText(self.scrolled, -1, label)
            ch = wx.Choice(self.scrolled, -1, choices=perRoleFormatNames)
            ch.SetSelection(0)  # default: use global
            self.scrollSizer.Add(roleLbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 4)
            self.scrollSizer.Add(ch, 1, wx.EXPAND | wx.RIGHT, 4)
            self._roleFormatChoices[role] = ch
            self._roleRowControls.append((roleLbl, ch, label.lower()))
        
        self.scrolled.SetSizer(self.scrollSizer)
        self.scrollSizer.Fit(self.scrolled)
        self.scrolled.FitInside()
        sizer.Add(self.scrolled, 1, wx.EXPAND | wx.ALL, 5)
        
        page.SetSizer(sizer)
        
        self.roleSearchEdit.Bind(wx.EVT_TEXT, self.onRoleSearch)

    def onRoleSearch(self, event):
        query = self.roleSearchEdit.GetValue().lower()
        
        # Detach all elements temporarily to avoid destroying them
        while self.scrollSizer.GetItemCount() > 0:
            self.scrollSizer.Detach(0)
        
        visible_count = 0
        for roleLbl, ch, label_text in self._roleRowControls:
            if query in label_text:
                roleLbl.Show()
                ch.Show()
                self.scrollSizer.Add(roleLbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 4)
                self.scrollSizer.Add(ch, 1, wx.EXPAND | wx.RIGHT, 4)
                visible_count += 1
            else:
                roleLbl.Hide()
                ch.Hide()
        
        self.scrolled.Layout()
        self.scrolled.FitInside()

    @property
    def selected_theme(self):
        selection = self.installedThemesChoice.GetSelection()
        if selection != wx.NOT_FOUND:
            return self.installedThemesChoice.GetClientData(selection)

    def setupAppProfilesPage(self, page):
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Translators: Help text for app profiles
        helpText = wx.StaticText(page, -1, _("Configure specific audio themes to automatically activate when certain applications are focused."))
        sizer.Add(helpText, 0, wx.TOP | wx.LEFT | wx.RIGHT, 10)
        
        # List of mappings
        self.appProfilesList = wx.ListCtrl(page, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.appProfilesList.InsertColumn(0, _("Application (e.g. chrome.exe)"), width=200)
        self.appProfilesList.InsertColumn(1, _("Audio Theme"), width=150)
        self.appProfilesList.InsertColumn(2, _("Typing Sound Pack"), width=150)
        sizer.Add(self.appProfilesList, 1, wx.EXPAND | wx.ALL, 10)
        
        # Add/Remove buttons
        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.addAppProfileBtn = wx.Button(page, -1, _("&Add Profile"))
        self.removeAppProfileBtn = wx.Button(page, -1, _("&Remove Profile"))
        btnSizer.Add(self.addAppProfileBtn, 0, wx.RIGHT, 5)
        btnSizer.Add(self.removeAppProfileBtn, 0, wx.LEFT, 5)
        sizer.Add(btnSizer, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
        
        page.SetSizer(sizer)
        
        self.addAppProfileBtn.Bind(wx.EVT_BUTTON, self.onAddAppProfile)
        self.removeAppProfileBtn.Bind(wx.EVT_BUTTON, self.onRemoveAppProfile)

    def onAddAppProfile(self, event):
        # Dialog to add profile
        dlg = wx.Dialog(self, title=_("Add App Profile"))
        dlgSizer = wx.BoxSizer(wx.VERTICAL)
        
        appLabel = wx.StaticText(dlg, -1, _("Application executable name (e.g. notepad.exe):"))
        dlgSizer.Add(appLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 10)
        appEdit = wx.TextCtrl(dlg, -1)
        dlgSizer.Add(appEdit, 0, wx.EXPAND | wx.ALL, 10)
        
        themeLabel = wx.StaticText(dlg, -1, _("Audio Theme:"))
        dlgSizer.Add(themeLabel, 0, wx.LEFT | wx.RIGHT, 10)
        themes = AudioThemesHandler().get_installed_themes()
        themeChoices = [t.name for t in themes]
        themeChoice = wx.Choice(dlg, -1, choices=themeChoices)
        if themeChoices:
            themeChoice.SetSelection(0)
        dlgSizer.Add(themeChoice, 0, wx.EXPAND | wx.ALL, 10)
        
        typingPackLabel = wx.StaticText(dlg, -1, _("Typing Sound Pack (optional):"))
        dlgSizer.Add(typingPackLabel, 0, wx.LEFT | wx.RIGHT, 10)
        typingPackChoices = [""] + self.typingPackChoices
        typingPackChoice = wx.Choice(dlg, -1, choices=typingPackChoices)
        typingPackChoice.SetSelection(0)
        dlgSizer.Add(typingPackChoice, 0, wx.EXPAND | wx.ALL, 10)
        
        btnSizer = dlg.CreateButtonSizer(wx.OK | wx.CANCEL)
        dlgSizer.Add(btnSizer, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
        dlg.SetSizerAndFit(dlgSizer)
        
        if dlg.ShowModal() == wx.ID_OK:
            app_name = appEdit.GetValue().strip().lower()
            if app_name and themeChoice.GetSelection() != wx.NOT_FOUND:
                selected_theme = themes[themeChoice.GetSelection()].folder
                selected_typing_pack = typingPackChoice.GetStringSelection()
                self._app_profiles_cache[app_name] = {"theme": selected_theme, "typing_pack": selected_typing_pack}
                self._updateAppProfilesList()
        dlg.Destroy()

    def onRemoveAppProfile(self, event):
        idx = self.appProfilesList.GetFirstSelected()
        if idx != -1:
            app_name = self.appProfilesList.GetItemText(idx)
            if app_name in self._app_profiles_cache:
                del self._app_profiles_cache[app_name]
                self._updateAppProfilesList()

    def _updateAppProfilesList(self):
        self.appProfilesList.DeleteAllItems()
        themes = AudioThemesHandler().get_installed_themes()
        folder_to_name = {t.folder: t.name for t in themes}
        for app, profile in self._app_profiles_cache.items():
            if isinstance(profile, str):
                theme_folder = profile
                typing_pack = ""
            else:
                theme_folder = profile.get("theme", "")
                typing_pack = profile.get("typing_pack", "")
            idx = self.appProfilesList.InsertItem(self.appProfilesList.GetItemCount(), app)
            theme_name = folder_to_name.get(theme_folder, theme_folder)
            self.appProfilesList.SetItem(idx, 1, theme_name)
            self.appProfilesList.SetItem(idx, 2, typing_pack)

    def setupMiscPage(self, page):
        """Tab 4: Miscellaneous — SentenceNav sentence/phrase navigation settings."""
        from .sentenceNavEngine import getSNConfig, getCurrentLanguage
        sizer = wx.BoxSizer(wx.VERTICAL)

        # --- Sentence navigation group ---
        sentBox = wx.StaticBoxSizer(wx.VERTICAL, page, _("Sentence Navigation (Alt+Arrows)"))

        # Paragraph chime volume
        pChimeLabel = wx.StaticText(page, -1, _("Paragraph boundary chime volume:"))
        self.paragraphChimeVolumeSlider = wx.Slider(page, -1, minValue=0, maxValue=100)
        sentBox.Add(pChimeLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        sentBox.Add(self.paragraphChimeVolumeSlider, 0, wx.EXPAND | wx.ALL, 5)

        # No next sentence chime
        nChimeLabel = wx.StaticText(page, -1, _("No more sentences chime volume:"))
        self.noNextSentenceChimeSlider = wx.Slider(page, -1, minValue=0, maxValue=100)
        sentBox.Add(nChimeLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        sentBox.Add(self.noNextSentenceChimeSlider, 0, wx.EXPAND | wx.ALL, 5)

        # Speak formatted text
        self.speakFormattedCheckbox = wx.CheckBox(page, -1, _("Speak formatted text"))
        sentBox.Add(self.speakFormattedCheckbox, 0, wx.ALL, 5)

        # Enable in Word
        self.enableInWordCheckbox = wx.CheckBox(page, -1, _("Enable experimental support for Word and WordPad"))
        sentBox.Add(self.enableInWordCheckbox, 0, wx.ALL, 5)

        # Break on Wiki References
        self.breakOnWikiReferencesCheckbox = wx.CheckBox(page, -1, _("Skip Wikipedia references in sentence endings"))
        sentBox.Add(self.breakOnWikiReferencesCheckbox, 0, wx.ALL, 5)

        # Reconstruct mode
        self.reconstructOptions = ["always", "sameIndent", "never"]
        self.reconstructOptionsText = [_("Always"), _("Same indent and style"), _("Never")]
        reconLabel = wx.StaticText(page, -1, _("Reconstruct sentences across paragraphs:"))
        self.reconstructModeCombobox = wx.Choice(page, -1, choices=self.reconstructOptionsText)
        sentBox.Add(reconLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        sentBox.Add(self.reconstructModeCombobox, 0, wx.EXPAND | wx.ALL, 5)

        # Sentence breakers
        breakLabel = wx.StaticText(page, -1, _("Sentence breakers:"))
        self.sentenceBreakersEdit = wx.TextCtrl(page, -1)
        sentBox.Add(breakLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        sentBox.Add(self.sentenceBreakersEdit, 0, wx.EXPAND | wx.ALL, 5)

        # Full width sentence breakers
        fwSentenceBreakLabel = wx.StaticText(page, -1, _("Full width sentence breakers:"))
        self.fullWidthSentenceBreakersEdit = wx.TextCtrl(page, -1)
        sentBox.Add(fwSentenceBreakLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        sentBox.Add(self.fullWidthSentenceBreakersEdit, 0, wx.EXPAND | wx.ALL, 5)

        # Phrase breakers
        phraseBreakLabel = wx.StaticText(page, -1, _("Phrase breakers:"))
        self.phraseBreakersEdit = wx.TextCtrl(page, -1)
        sentBox.Add(phraseBreakLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        sentBox.Add(self.phraseBreakersEdit, 0, wx.EXPAND | wx.ALL, 5)

        # Full width phrase breakers
        fwPhraseBreakLabel = wx.StaticText(page, -1, _("Full width phrase breakers:"))
        self.fullWidthPhraseBreakersEdit = wx.TextCtrl(page, -1)
        sentBox.Add(fwPhraseBreakLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        sentBox.Add(self.fullWidthPhraseBreakersEdit, 0, wx.EXPAND | wx.ALL, 5)

        # Skippable punctuation
        skipLabel = wx.StaticText(page, -1, _("Skippable punctuation:"))
        self.skippableEdit = wx.TextCtrl(page, -1)
        sentBox.Add(skipLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        sentBox.Add(self.skippableEdit, 0, wx.EXPAND | wx.ALL, 5)

        # Capital letters
        capsLabel = wx.StaticText(page, -1, _("Capital letters (no spaces):"))
        self.capitalLettersEdit = wx.TextCtrl(page, -1)
        sentBox.Add(capsLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        sentBox.Add(self.capitalLettersEdit, 0, wx.EXPAND | wx.ALL, 5)

        # Lower case letters
        lowerLabel = wx.StaticText(page, -1, _("Lower case letters (no spaces):"))
        self.lowerCaseLettersEdit = wx.TextCtrl(page, -1)
        sentBox.Add(lowerLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        sentBox.Add(self.lowerCaseLettersEdit, 0, wx.EXPAND | wx.ALL, 5)

        # Exceptional abbreviations
        abbrLabel = wx.StaticText(page, -1, _("Exceptional abbreviations (space separated):"))
        self.exceptionalAbbreviationsEdit = wx.TextCtrl(page, -1)
        sentBox.Add(abbrLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        sentBox.Add(self.exceptionalAbbreviationsEdit, 0, wx.EXPAND | wx.ALL, 5)

        # Blacklist
        blLabel = wx.StaticText(page, -1, _("Blacklist applications for sentence navigation (comma separated):"))
        self.snAppsBlacklistEdit = wx.TextCtrl(page, -1)
        sentBox.Add(blLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        sentBox.Add(self.snAppsBlacklistEdit, 0, wx.EXPAND | wx.ALL, 5)

        sizer.Add(sentBox, 0, wx.EXPAND | wx.ALL, 10)

        # --- Text navigation group ---
        textBox = wx.StaticBoxSizer(wx.VERTICAL, page, _("Text Navigation (Alt+Shift+Arrows)"))

        # Crackling Volume
        crackleTextLabel = wx.StaticText(page, -1, _("Paragraph crackle volume:"))
        self.textCrackleVolumeSlider = wx.Slider(page, -1, minValue=0, maxValue=100)
        textBox.Add(crackleTextLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        textBox.Add(self.textCrackleVolumeSlider, 0, wx.EXPAND | wx.ALL, 5)

        # No next text chime
        noTextChimeLabel = wx.StaticText(page, -1, _("No more text units chime volume:"))
        self.noNextTextChimeSlider = wx.Slider(page, -1, minValue=0, maxValue=100)
        textBox.Add(noTextChimeLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        textBox.Add(self.noNextTextChimeSlider, 0, wx.EXPAND | wx.ALL, 5)
        
        # Speak error message
        self.noNextTextMessageCheckbox = wx.CheckBox(page, -1, _("Speak message when no more text units found"))
        textBox.Add(self.noNextTextMessageCheckbox, 0, wx.ALL, 5)
        
        sizer.Add(textBox, 0, wx.EXPAND | wx.ALL, 10)


        # --- BrowserNav navigation group ---
        bnBox = wx.StaticBoxSizer(wx.VERTICAL, page, _("Advanced Browser Navigation (BrowserNav)"))

        # Crackling volume
        crackleLabel = wx.StaticText(page, -1, _("Crackling sound volume (during navigation):"))
        self.crackleVolumeSlider = wx.Slider(page, -1, minValue=0, maxValue=100)
        bnBox.Add(crackleLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        bnBox.Add(self.crackleVolumeSlider, 0, wx.EXPAND | wx.ALL, 5)

        # Beep volume
        beepLabel = wx.StaticText(page, -1, _("Beeping sound volume:"))
        self.beepVolumeSlider = wx.Slider(page, -1, minValue=0, maxValue=100)
        bnBox.Add(beepLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        bnBox.Add(self.beepVolumeSlider, 0, wx.EXPAND | wx.ALL, 5)

        # Skip Clutter volume
        skipLabel = wx.StaticText(page, -1, _("Skip Clutter chime volume:"))
        self.skipChimeVolumeSlider = wx.Slider(page, -1, minValue=0, maxValue=100)
        bnBox.Add(skipLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        bnBox.Add(self.skipChimeVolumeSlider, 0, wx.EXPAND | wx.ALL, 5)

        sizer.Add(bnBox, 0, wx.EXPAND | wx.ALL, 10)

        noteLabel = wx.StaticText(page, -1, _("Note: These settings adjust the audio feedback for SentenceNav, TextNav, and BrowserNav integrations."))
        sizer.Add(noteLabel, 0, wx.ALL, 10)

        page.SetSizer(sizer)

    def onSelectRoles(self, event):
        dlg = RoleSelectionDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            self.blacklisted_roles = dlg.getBlacklistedRoles()
        dlg.Destroy()

    def _initialize_at_state(self):
        def _b(v):
            if isinstance(v, str): return v.lower() == 'true'
            return bool(v)
        def _i(v, d=100):
            try: return int(v)
            except (ValueError, TypeError): return d

        conf = config.conf.get("audiothemes", {})
        self.enableThemesCheckbox.SetValue(_b(conf.get("enable_audio_themes", True)))
        self.play3dCheckbox.SetValue(_b(conf.get("audio3d", True)))
        self.speakRoleCheckbox.SetValue(_b(conf.get("speak_roles", True)))
        self.useInSayAllCheckbox.SetValue(_b(conf.get("use_in_say_all", False)))
        self.useSynthVolumeCheckbox.SetValue(_b(conf.get("use_synth_volume", True)))
        self.volumeSlider.SetValue(_i(conf.get("volume", 100)))
        self.disabledAppsEdit.SetValue(conf.get("disabled_apps", ""))
        self.blacklisted_roles = conf.get("blacklisted_roles", [])
        
        duck_val = conf.get("audio_ducking_enabled", True)
        if isinstance(duck_val, str):
            duck_val = duck_val.lower() == 'true'
        self.audioDuckingCheckbox.SetValue(_b(bool(duck_val)))
        
        duck_vol = conf.get("audio_ducking_volume", 30)
        if isinstance(duck_vol, str):
            try:
                duck_vol = int(duck_vol)
            except ValueError:
                duck_vol = 30
        self.audioDuckingVolumeSlider.SetValue(_i(duck_vol))
        self.audioDuckingVolumeSlider.Enable(bool(duck_val))
        
        unspoken_conf = config.conf["unspoken"]
        self.audioCacheCheckbox.SetValue(_b(unspoken_conf.get("AudioCache", True)))
        self.smartVolumeCheckbox.SetValue(_b(unspoken_conf.get("SmartVolume", True)))
        self.smoothEnvelopeCheckbox.SetValue(_b(unspoken_conf.get("SmoothEnvelope", True)))
        self.smoothPanningCheckbox.SetValue(_b(unspoken_conf.get("SmoothPanning", True)))
        trim_sil = unspoken_conf.get("TrimSilence", False)
        if isinstance(trim_sil, str):
            trim_sil = trim_sil.lower() == "true"
        self.trimSilenceCheckbox.SetValue(_b(bool(trim_sil)))
        
        mode = conf.get("output_mode", "stereo")
        if mode == "mono":
            self.outputModeChoice.SetSelection(1)
        else:
            self.outputModeChoice.SetSelection(0)
        
        self.typingSoundsCheckbox.SetValue(_b(conf.get("typing_sounds", False)))
        self.typingSoundsEditOnlyCheckbox.SetValue(_b(conf.get("typing_sounds_edit_only", True)))
        self.typingSoundsSpatialCheckbox.SetValue(_b(conf.get("typing_sounds_spatial", True)))
        self.typingSoundsSmartSpatialCheckbox.SetValue(_b(conf.get("typing_sounds_spatial_smart", True)))
        
        self.typingSoundsCheckbox.Bind(wx.EVT_CHECKBOX, self._update_typing_controls)
        self.typingSoundsSpatialCheckbox.Bind(wx.EVT_CHECKBOX, self._update_typing_controls)
        
        pack = conf.get("typing_sound_pack", "1blueSwitch")
        if pack in self.typingPackChoices:
            self.typingPackCombobox.SetStringSelection(pack)
        self.typingSoundsVolumeSlider.SetValue(_i(conf.get("typing_sounds_volume", 100)))
        self._update_typing_controls()
        
        # Speech Order
        fmt = conf.get("announceFormat", "0")
        for i, (f, n) in enumerate(self.ANNOUNCE_FORMATS):
            if f == fmt:
                self.announceFormatChoice.SetSelection(i)
                break
        
        # Per-role formats
        try:
            roleFormatsJson = conf.get("roleAnnounceFormats", "{}")
            roleFormatsDict = json.loads(roleFormatsJson)
        except Exception as e:
            log.debug(f"Could not load role formats: {e}")
            roleFormatsDict = {}

        # App Profiles
        try:
            appProfilesJson = conf.get("app_profiles", "{}")
            raw_profiles = json.loads(appProfilesJson)
            self._app_profiles_cache = {}
            for k, v in raw_profiles.items():
                if isinstance(v, str):
                    self._app_profiles_cache[k] = {"theme": v, "typing_pack": ""}
                else:
                    self._app_profiles_cache[k] = v
        except Exception:
            self._app_profiles_cache = {}

        for role, ch in self._roleFormatChoices.items():
            role_key = str(role.value) if hasattr(role, 'value') else str(role)
            saved_fmt = roleFormatsDict.get(role_key, "global")
            for idx, (code, name) in enumerate(self._PER_ROLE_FORMATS):
                if code == saved_fmt:
                    ch.SetSelection(idx)
                    break
        
        unspoken_conf = config.conf["unspoken"]
        self.enableReverbCheckbox.SetValue(_b(unspoken_conf["Reverb"]))
        self.roomSizeSlider.SetValue(_i(unspoken_conf["RoomSize"]))
        self.dampingSlider.SetValue(_i(unspoken_conf["Damping"]))
        self.wetLevelSlider.SetValue(_i(unspoken_conf["WetLevel"]))
        self.dryLevelSlider.SetValue(_i(unspoken_conf["DryLevel"]))
        self.widthSlider.SetValue(_i(unspoken_conf["Width"]))
        self.onEnableReverbCheckboxChanged(DummyEvent(unspoken_conf["Reverb"]))
        # Miscellaneous tab — SentenceNav settings
        from .sentenceNavEngine import getSNConfig, getCurrentLanguage
        self.snLang = getCurrentLanguage()
        snConf = config.conf["sentencenav"]
        self.paragraphChimeVolumeSlider.SetValue(_i(snConf["paragraphChimeVolume"]))
        self.noNextSentenceChimeSlider.SetValue(_i(snConf["noNextSentenceChimeVolume"]))
        self.speakFormattedCheckbox.SetValue(_b(snConf["speakFormatted"]))
        self.enableInWordCheckbox.SetValue(_b(snConf.get("enableInWord", False)))
        self.breakOnWikiReferencesCheckbox.SetValue(_b(snConf.get("breakOnWikiReferences", True)))
        
        self.textCrackleVolumeSlider.SetValue(_i(snConf.get("textCrackleVolume", 25)))
        self.noNextTextChimeSlider.SetValue(_i(snConf.get("noNextTextChimeVolume", 50)))
        self.noNextTextMessageCheckbox.SetValue(_b(snConf.get("noNextTextMessage", False)))
        reconIndex = self.reconstructOptions.index(str(snConf["reconstructMode"]))
        self.reconstructModeCombobox.SetSelection(reconIndex)
        
        self.sentenceBreakersEdit.SetValue(snConf["sentenceBreakers"])
        self.fullWidthSentenceBreakersEdit.SetValue(snConf.get("fullWidthSentenceBreakers", "。！？"))
        self.phraseBreakersEdit.SetValue(snConf.get("phraseBreakers", ".!?,;:-\u2013()"))
        self.fullWidthPhraseBreakersEdit.SetValue(snConf.get("fullWidthPhraseBreakers", "\u3002\uff01\uff1f\uff0c\uff1b\uff1a\uff08\uff09"))
        self.skippableEdit.SetValue(snConf.get("skippable", "\"\\u201d\\u00bb)"))
        
        # Language-specific config strings must use getSNConfig to parse JSON correctly
        try:
            self.capitalLettersEdit.SetValue(getSNConfig("capitalLetters", self.snLang))
        except Exception:
            self.capitalLettersEdit.SetValue("A-Z")
        
        try:
            self.lowerCaseLettersEdit.SetValue(getSNConfig("lowerCaseLetters", self.snLang))
        except Exception:
            self.lowerCaseLettersEdit.SetValue("a-z")
            
        try:
            self.exceptionalAbbreviationsEdit.SetValue(getSNConfig("exceptionalAbbreviations", self.snLang))
        except Exception:
            self.exceptionalAbbreviationsEdit.SetValue("Mr Ms Mrs Dr St e.g")
        
        self.snAppsBlacklistEdit.SetValue(snConf["applicationsBlacklist"])

        # Miscellaneous tab — BrowserNav settings
        bnConf = config.conf["browsernav"]
        self.crackleVolumeSlider.SetValue(_i(bnConf["crackleVolume"]))
        self.beepVolumeSlider.SetValue(_i(bnConf["beepVolume"]))
        self.skipChimeVolumeSlider.SetValue(_i(bnConf["skipChimeVolume"]))

    def _maintain_state(self):
        self.audio_themes = sorted(AudioThemesHandler.get_installed_themes())
        self.installedThemesChoice.Clear()
        for theme in self.audio_themes:
            self.installedThemesChoice.Append(theme.name, theme)
        for theme in self.audio_themes:
            if theme.folder == config.conf["audiothemes"]["active_theme"]:
                self.installedThemesChoice.SetStringSelection(theme.name)
        self.innerPanel.Enable(self.enableThemesCheckbox.IsChecked())
        self.volumeSlider.Enable(not self.useSynthVolumeCheckbox.IsChecked())
        self.onThemeSelectionChanged(None)
        if hasattr(self, "appProfilesList"):
            self._updateAppProfilesList()

    def onSave(self):
        conf = config.conf["audiothemes"]
        conf["enable_audio_themes"] = self.enableThemesCheckbox.IsChecked()
        if self.selected_theme is not None:
            conf["active_theme"] = self.selected_theme.folder
        conf["audio3d"] = self.play3dCheckbox.IsChecked()
        conf["speak_roles"] = self.speakRoleCheckbox.IsChecked()
        conf["use_in_say_all"] = self.useInSayAllCheckbox.IsChecked()
        conf["use_synth_volume"] = self.useSynthVolumeCheckbox.IsChecked()
        conf["volume"] = self.volumeSlider.GetValue()
        conf["disabled_apps"] = self.disabledAppsEdit.GetValue()
        if hasattr(self, 'blacklisted_roles'):
            conf["blacklisted_roles"] = self.blacklisted_roles
        conf["audio_ducking_enabled"] = self.audioDuckingCheckbox.IsChecked()
        conf["audio_ducking_volume"] = self.audioDuckingVolumeSlider.GetValue()
        
        if self.outputModeChoice.GetSelection() == 1:
            conf["output_mode"] = "mono"
        else:
            conf["output_mode"] = "stereo"
        
        conf["typing_sounds"] = self.typingSoundsCheckbox.GetValue()
        conf["typing_sounds_edit_only"] = self.typingSoundsEditOnlyCheckbox.GetValue()
        conf["typing_sounds_spatial"] = self.typingSoundsSpatialCheckbox.GetValue()
        conf["typing_sounds_spatial_smart"] = self.typingSoundsSmartSpatialCheckbox.GetValue()
        if self.typingPackCombobox.GetSelection() != wx.NOT_FOUND:
            conf["typing_sound_pack"] = self.typingPackCombobox.GetStringSelection()
        conf["typing_sounds_volume"] = self.typingSoundsVolumeSlider.GetValue()
        
        # Speech Order
        if self.announceFormatChoice.GetSelection() != wx.NOT_FOUND:
            conf["announceFormat"] = self.ANNOUNCE_FORMATS[self.announceFormatChoice.GetSelection()][0]
        
        # Per-role formats
        roleFormatsDict = {}
        for role, ch in self._roleFormatChoices.items():
            sel = ch.GetSelection()
            if sel != wx.NOT_FOUND and sel > 0:  # skip index 0 = "global"
                code = self._PER_ROLE_FORMATS[sel][0]
                role_key = str(role.value) if hasattr(role, 'value') else str(role)
                roleFormatsDict[role_key] = code
        conf["roleAnnounceFormats"] = json.dumps(roleFormatsDict)
        
        # App Profiles
        if hasattr(self, "_app_profiles_cache"):
            conf["app_profiles"] = json.dumps(self._app_profiles_cache)
        
        unspoken_conf = config.conf["unspoken"]
        unspoken_conf["AudioCache"] = self.audioCacheCheckbox.GetValue()
        unspoken_conf["SmartVolume"] = self.smartVolumeCheckbox.GetValue()
        unspoken_conf["SmoothEnvelope"] = self.smoothEnvelopeCheckbox.GetValue()
        unspoken_conf["SmoothPanning"] = self.smoothPanningCheckbox.GetValue()
        unspoken_conf["TrimSilence"] = self.trimSilenceCheckbox.GetValue()
        unspoken_conf["Reverb"] = self.enableReverbCheckbox.IsChecked()
        unspoken_conf["RoomSize"] = self.roomSizeSlider.GetValue()
        unspoken_conf["Damping"] = self.dampingSlider.GetValue()
        unspoken_conf["WetLevel"] = self.wetLevelSlider.GetValue()
        unspoken_conf["DryLevel"] = self.dryLevelSlider.GetValue()
        unspoken_conf["Width"] = self.widthSlider.GetValue()
        self.rulesPage.onSave()
        self.quickJumpPage.onSave()
        # Miscellaneous tab — SentenceNav settings
        from .sentenceNavEngine import setSNConfig, regexCache
        snConf = config.conf["sentencenav"]
        snConf["paragraphChimeVolume"] = self.paragraphChimeVolumeSlider.GetValue()
        snConf["noNextSentenceChimeVolume"] = self.noNextSentenceChimeSlider.GetValue()
        snConf["speakFormatted"] = self.speakFormattedCheckbox.GetValue()
        snConf["enableInWord"] = self.enableInWordCheckbox.GetValue()
        snConf["breakOnWikiReferences"] = self.breakOnWikiReferencesCheckbox.GetValue()
        
        snConf["textCrackleVolume"] = self.textCrackleVolumeSlider.GetValue()
        snConf["noNextTextChimeVolume"] = self.noNextTextChimeSlider.GetValue()
        snConf["noNextTextMessage"] = self.noNextTextMessageCheckbox.GetValue()
        snConf["reconstructMode"] = self.reconstructOptions[self.reconstructModeCombobox.GetSelection()]
        
        snConf["sentenceBreakers"] = self.sentenceBreakersEdit.GetValue()
        snConf["fullWidthSentenceBreakers"] = self.fullWidthSentenceBreakersEdit.GetValue()
        snConf["phraseBreakers"] = self.phraseBreakersEdit.GetValue()
        snConf["fullWidthPhraseBreakers"] = self.fullWidthPhraseBreakersEdit.GetValue()
        snConf["skippable"] = self.skippableEdit.GetValue()
        
        # Save language specific variables cleanly
        try:
            setSNConfig("capitalLetters", self.capitalLettersEdit.GetValue(), getattr(self, "snLang", "en"))
        except Exception:
            pass
        try:
            setSNConfig("lowerCaseLetters", self.lowerCaseLettersEdit.GetValue(), getattr(self, "snLang", "en"))
        except Exception:
            pass
        try:
            setSNConfig("exceptionalAbbreviations", self.exceptionalAbbreviationsEdit.GetValue(), getattr(self, "snLang", "en"))
        except Exception:
            pass
        
        snConf["applicationsBlacklist"] = self.snAppsBlacklistEdit.GetValue()
        
        # Clear the regex cache to force recompilation with new rules
        regexCache.clear()
        # Clear phraseRegex if it's imported from the module
        
        # Clear the audio cache so normalization/smoothing/mono changes apply immediately
        from .unspoken import sounds, sounds_lock, UnspokenPlayer
        with sounds_lock:
            sounds.clear()
        from .handler import AudioThemesHandler
        player = AudioThemesHandler().player
        if hasattr(player, "_play_cache"):
            with getattr(player, "_play_cache_lock", threading.Lock()):
                player._play_cache.clear()
        if hasattr(player, "_play_file_cache"):
            with getattr(player, "_cache_lock", threading.Lock()):
                player._play_file_cache.clear()
        
        # Miscellaneous tab — BrowserNav settings
        bnConf = config.conf["browsernav"]
        bnConf["crackleVolume"] = self.crackleVolumeSlider.GetValue()
        bnConf["beepVolume"] = self.beepVolumeSlider.GetValue()
        bnConf["skipChimeVolume"] = self.skipChimeVolumeSlider.GetValue()

    def postSave(self):
        audiotheme_changed.notify()

    def onDiscard(self):
        if hasattr(self.rulesPage, "onDiscard"):
            self.rulesPage.onDiscard()
        if hasattr(self.quickJumpPage, "onDiscard"):
            self.quickJumpPage.onDiscard()

    def onPreviewTheme(self, event):
        theme = self.selected_theme
        if not theme:
            return
        theme_path = os.path.join(THEMES_DIR, theme.folder)
        # Try to find common sound files to play
        sounds_to_try = [
            "focus.wav", "focus.ogg",
            "select.wav", "select.ogg",
            "button.wav", "button.ogg",
            "link.wav", "link.ogg"
        ]
        
        def play_preview():
            try:
                for snd in sounds_to_try:
                    p = os.path.join(theme_path, snd)
                    if os.path.exists(p):
                        nvwave.playWaveFile(p, asynchronous=True)
                        _time.sleep(0.3)
                        break
            except Exception:
                pass
        threading.Thread(target=play_preview).start()

    def onAbout(self, event):
        theme_dict = self.selected_theme.todict()
        author_val = theme_dict.get("author", "").strip()
        if not author_val or author_val.lower() == "unknown":
            theme_dict["author"] = _("Unknown")
            
        try:
            import os
            files = [f for f in os.listdir(self.selected_theme.directory) if f.lower().endswith(('.wav', '.ogg'))]
            theme_dict["count"] = len(files)
        except Exception:
            theme_dict["count"] = 0

        wx.MessageBox(
            # Translators: content of a message box containing theme information
            _("Name: {name}\nAuthor: {author}\nNumber of sounds: {count}\n\n{summary}").format(
                **theme_dict
            ),
            # Translators: title for a message containing theme information
            _("About Audio Theme"),
            style=wx.ICON_INFORMATION,
        )

    def onStoreClicked(self, event):
        from .studio.themes_store import ThemesStoreDialog
        dlg = ThemesStoreDialog(self)
        dlg.ShowModal()

    def onRemove(self, event):
        theme = self.selected_theme
        confirm = wx.MessageBox(
            # Translators: message asking the user to confirm the removal of an audio theme
            _(
                "This can not be undone.\nAre you sure you  want to remove audio theme {name}?"
            ).format(name=theme.name),
            # Translators: title of a message asking the user to confirm the removal of an audio theme
            _("Remove Audio Theme"),
            style=wx.YES_NO | wx.ICON_WARNING,
        )
        if confirm == wx.YES:
            AudioThemesHandler.remove_audio_theme(theme)
            self._maintain_state()

    def onAdd(self, event):
        openFileDlg = wx.FileDialog(
            self,
            # Translators: the title of a file dialog to browse to an audio theme package
            message=_("Choose an audio theme package"),
            # Translators: theme file type description
            wildcard=_("Audio Theme Packages") + " (*.atp)|*.atp",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        if openFileDlg.ShowModal() == wx.ID_OK:
            filename = openFileDlg.GetPath().strip()
            openFileDlg.Destroy()
            if filename:
                AudioThemesHandler.install_audio_themePackage(filename)
                self._maintain_state()

    def onThemeSelectionChanged(self, event):
        flag = self.selected_theme is not None
        for btn in (self.aboutThemeButton, self.removeThemeButton):
            btn.Enable(flag)
        # Play a preview sound from the selected theme
        if self.selected_theme is not None:
            self._playThemePreview(self.selected_theme)

    def _playThemePreview(self, theme):
        """Play a sample sound from the given theme as a preview."""
        # Try common sound names in order of preference
        preview_names = ["button.ogg", "button.wav", "link.ogg", "link.wav", "checkbox.ogg", "checkbox.wav"]
        theme_dir = os.path.join(THEMES_DIR, theme.folder)
        for name in preview_names:
            path = os.path.join(theme_dir, name)
            if os.path.exists(path):
                try: nvwave.playWaveFile(path, asynchronous=True)
                except Exception:
                    pass
                return

    def _add_directory_to_zip(self, zipf, source_dir, archive_prefix):
        """Recursively add all files from source_dir into zipf under archive_prefix."""
        if not os.path.isdir(source_dir):
            return
        for root, dirs, files in os.walk(source_dir):
            for fname in files:
                full_path = os.path.join(root, fname)
                arc_name = os.path.join(archive_prefix, os.path.relpath(full_path, source_dir))
                zipf.write(full_path, arc_name)

    def _extract_directory_from_zip(self, zipf, archive_prefix, dest_dir):
        """Extract all files matching archive_prefix/* from zipf into dest_dir."""
        prefix = archive_prefix.rstrip("/") + "/"
        for entry in zipf.namelist():
            if entry.startswith(prefix) and not entry.endswith("/"):
                rel = entry[len(prefix):]
                dest_path = os.path.join(dest_dir, rel)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                with zipf.open(entry) as src, open(dest_path, "wb") as dst:
                    dst.write(src.read())

    def onExportConfig(self, event):
        from .phoneticPunctuation import rulesFileName
        from .utils import getSoundsPath
        addon_dir = os.path.dirname(__file__)
        saveFileDlg = wx.FileDialog(
            self,
            _("Export Audio Themes Configuration"),
            wildcard=_("Audio Themes Configuration (*.atcfg)|*.atcfg"),
            defaultFile=_time.strftime("AudioThemes_Config_%Y%m%d.atcfg"),
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        )
        if saveFileDlg.ShowModal() == wx.ID_OK:
            filename = saveFileDlg.GetPath().strip()
            if filename:
                try:
                    with zipfile.ZipFile(filename, "w", zipfile.ZIP_DEFLATED) as zipf:
                        # 1. Rules JSON
                        if os.path.exists(rulesFileName):
                            zipf.write(rulesFileName, "earconsAndSpeechRules.json")
                        # 2. All settings
                        from .utils import phoneticPunctuationConfigKey
                        settings_data = {
                            "audiothemes": {k: config.conf["audiothemes"][k] for k in config.conf["audiothemes"]},
                            "unspoken": {k: config.conf["unspoken"][k] for k in config.conf["unspoken"]},
                            "phoneticpunctuation": {k: config.conf[phoneticPunctuationConfigKey][k] for k in config.conf[phoneticPunctuationConfigKey]},
                        }
                        zipf.writestr("audiothemes_settings.json", json.dumps(settings_data, indent=4))
                        # 3. Audio theme sound files (all installed themes)
                        self._add_directory_to_zip(zipf, THEMES_DIR, "audio-themes")
                        # 4. Typing sound packs
                        typing_dir = os.path.join(addon_dir, "typingSounds")
                        self._add_directory_to_zip(zipf, typing_dir, "typingSounds")
                        # 5. Built-in earcon sounds
                        sounds_dir = getSoundsPath()
                        self._add_directory_to_zip(zipf, sounds_dir, "sounds")
                    wx.MessageBox(_("Comprehensive export completed successfully!\nIncludes: settings, rules, themes, typing sounds, and earcon sounds."), _("Success"), style=wx.ICON_INFORMATION)
                except Exception as e:
                    wx.MessageBox(_("Error exporting configuration:\n{}").format(str(e)), _("Error"), style=wx.ICON_ERROR)

    def onImportConfig(self, event):
        from .phoneticPunctuation import rulesFileName, reloadRules
        from .utils import getSoundsPath
        addon_dir = os.path.dirname(__file__)
        openFileDlg = wx.FileDialog(
            self,
            _("Import Audio Themes Configuration"),
            wildcard=_("Audio Themes Configuration (*.atcfg)|*.atcfg"),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        )
        if openFileDlg.ShowModal() == wx.ID_OK:
            filename = openFileDlg.GetPath().strip()
            if filename:
                try:
                    with zipfile.ZipFile(filename, "r") as zipf:
                        files = zipf.namelist()
                        # 1. Rules
                        if "earconsAndSpeechRules.json" in files:
                            zipf.extract("earconsAndSpeechRules.json", path=os.path.dirname(rulesFileName))
                        # 2. Settings
                        if "audiothemes_settings.json" in files:
                            settings_data = json.loads(zipf.read("audiothemes_settings.json"))
                            if "audiothemes" in settings_data:
                                for k, v in settings_data["audiothemes"].items():
                                    try:
                                        config.conf["audiothemes"][k] = v
                                    except Exception:
                                        pass
                            if "unspoken" in settings_data:
                                for k, v in settings_data["unspoken"].items():
                                    try:
                                        config.conf["unspoken"][k] = v
                                    except Exception:
                                        pass
                            if "phoneticpunctuation" in settings_data:
                                from .utils import phoneticPunctuationConfigKey
                                for k, v in settings_data["phoneticpunctuation"].items():
                                    try:
                                        config.conf[phoneticPunctuationConfigKey][k] = v
                                    except Exception:
                                        pass
                        # 3. Audio themes
                        has_themes = any(n.startswith("audio-themes/") for n in files)
                        if has_themes:
                            overwrite = wx.MessageBox(
                                _("This package contains audio themes.\nDo you want to overwrite existing themes with the same name?"),
                                _("Import Themes"),
                                style=wx.YES_NO | wx.ICON_QUESTION
                            )
                            if overwrite == wx.YES:
                                self._extract_directory_from_zip(zipf, "audio-themes", THEMES_DIR)
                            else:
                                # Only extract themes that don't already exist
                                prefix = "audio-themes/"
                                for entry in files:
                                    if entry.startswith(prefix) and not entry.endswith("/"):
                                        rel = entry[len(prefix):]
                                        dest_path = os.path.join(THEMES_DIR, rel)
                                        if not os.path.exists(dest_path):
                                            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                                            with zipf.open(entry) as src, open(dest_path, "wb") as dst:
                                                dst.write(src.read())
                        # 4. Typing sounds
                        has_typing = any(n.startswith("typingSounds/") for n in files)
                        if has_typing:
                            typing_dir = os.path.join(addon_dir, "typingSounds")
                            self._extract_directory_from_zip(zipf, "typingSounds", typing_dir)
                        # 5. Earcon sounds
                        has_sounds = any(n.startswith("sounds/") for n in files)
                        if has_sounds:
                            sounds_dir = getSoundsPath()
                            self._extract_directory_from_zip(zipf, "sounds", sounds_dir)
                    # Reload everything
                    reloadRules()
                    self._initialize_at_state()
                    self._maintain_state()
                    audiotheme_changed.notify()
                    wx.MessageBox(_("Comprehensive import completed successfully!"), _("Success"), style=wx.ICON_INFORMATION)
                except Exception as e:
                    wx.MessageBox(_("Error importing configuration:\n{}").format(str(e)), _("Error"), style=wx.ICON_ERROR)

    def onCheckUpdates(self, event):
        check_for_updates(self)
