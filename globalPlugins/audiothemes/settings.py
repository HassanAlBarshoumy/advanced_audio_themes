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

from .handler import AudioThemesHandler, audiotheme_changed, THEMES_DIR, _get_blacklisted_roles, theme_roles, role_name_to_int, role_int_to_name, SpecialProps
from .update_checker import check_for_updates
from .frenzy import get_ducking_factor, _DEFAULT_DUCKING_CATEGORIES
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
        
        self.rolesListBox = wx.ListView(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_NO_HEADER, name=_("Roles"))
        self.rolesListBox.EnableCheckBoxes(True)
        self.rolesListBox.InsertColumn(0, _("Roles"), width=360)
        mainSizer.Add(self.rolesListBox, 1, wx.ALL | wx.EXPAND, 10)
        
        self.role_ids = []
        blacklisted = getattr(parent, 'blacklisted_roles', _get_blacklisted_roles())
        
        idx = 0
        for role_id, role_label in controlTypes.roleLabels.items():
            if role_id >= 10000:  # Skip states (STATE_OFFSET in handler)
                continue
            self.role_ids.append(role_id)
            self.rolesListBox.InsertItem(idx, role_label)
            if role_id not in blacklisted:
                self.rolesListBox.CheckItem(idx, True)
            idx += 1
        # Add emoji role
        self.role_ids.append(SpecialProps.emoji)
        self.rolesListBox.InsertItem(idx, _("Emoji Sound"))
        if SpecialProps.emoji not in blacklisted:
            self.rolesListBox.CheckItem(idx, True)
                
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

        # Tab 3: Audio Formats and FFmpeg
        self.audioFormatsPage = wx.Panel(self.notebook)
        self.setupAudioFormatsPage(self.audioFormatsPage)
        self.notebook.AddPage(self.audioFormatsPage, _("Audio Formats"))

        # Tab 4: Earcons and Speech Rules (lazy loaded)
        self._rulesPage = None
        self._rulesLoaded = False
        self.rulesPage = wx.Panel(self.notebook)
        self.notebook.AddPage(self.rulesPage, _("Earcons & Speech Rules"))

        # Tab 5: Miscellaneous
        self.miscPage = wx.Panel(self.notebook)
        self.setupMiscPage(self.miscPage)
        self.notebook.AddPage(self.miscPage, _("Miscellaneous"))

        # Tab 5: Speech Order (Control Type Before Label) — per-role grid lazy loaded
        self._speechOrderLoaded = False
        self.speechOrderPage = wx.Panel(self.notebook)
        self.setupSpeechOrderPage(self.speechOrderPage)
        self.notebook.AddPage(self.speechOrderPage, _("Speech Order"))

        # Tab 6: App Profiles
        self.appProfilesPage = wx.Panel(self.notebook)
        self.setupAppProfilesPage(self.appProfilesPage)
        self.notebook.AddPage(self.appProfilesPage, _("App Profiles"))

        # Tab 7: QuickSearch Websites & Bookmarks (lazy loaded)
        self._quickJumpPage = None
        self._quickJumpLoaded = False
        self.quickJumpPage = wx.Panel(self.notebook)
        self.notebook.AddPage(self.quickJumpPage, _("QuickSearch & Bookmarks"))

        # Tab 8: First/Last item detection
        self.firstLastPage = wx.Panel(self.notebook)
        self.setupFirstLastPage(self.firstLastPage)
        self.notebook.AddPage(self.firstLastPage, _("First/Last Item"))

        # Tab 9: System Status Sounds
        self.sysStatusPage = wx.Panel(self.notebook)
        self.setupSystemStatusPage(self.sysStatusPage)
        self.notebook.AddPage(self.sysStatusPage, _("System Status"))

        # Tab 10: Emoji Settings
        self.emojiPage = wx.Panel(self.notebook)
        self.setupEmojiPage(self.emojiPage)
        self.notebook.AddPage(self.emojiPage, _("Emoji"))

        settingsSizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 5)

        self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self._onLazyLoadTab)

        self._initialize_at_state()
        self._maintain_state()

    def setupGeneralPage(self, page):
        # Translators: label for the checkbox to enable or disable audio themes
        self.enableThemesCheckbox = wx.CheckBox(page, -1, _("Enable audio themes"))
        self.innerPanel = innerPanel = wx.Panel(page)
        self.themePanel = themePanel = wx.Panel(innerPanel)
        # Translators: label for a combobox containing a list of installed audio themes
        installedThemesLabel = wx.StaticText(themePanel, -1, _("Select theme:"))
        self.installedThemesChoice = wx.Choice(themePanel, -1, name=_("Select theme"))
        # Translators: label for a button to show info about an audio theme
        self.aboutThemeButton = wx.Button(themePanel, -1, _("&About"))
        # Translators: label for a button to remove an audio theme
        self.removeThemeButton = wx.Button(themePanel, -1, _("&Remove"))
        # Translators: label for a button to add a new audio theme
        self.addThemeButton = wx.Button(themePanel, -1, _("Add &New..."))
        # Translators: label for a button to open the themes store
        self.storeThemeButton = wx.Button(themePanel, -1, _("Themes Store"))
        # Translators: label for a button to open the Theme Studio
        self.blenderThemeButton = wx.Button(themePanel, -1, _("Theme Studio"))
        # Translators: label for a button to preview the selected theme
        self.previewThemeButton = wx.Button(themePanel, -1, _("P&review"))
        # Translators: label for a checkbox to toggle the 3D mode
        self.play3dCheckbox = wx.CheckBox(themePanel, -1, _("Play sounds in 3D mode"))
        # Translators: label for a checkbox to toggle the speaking of object role
        self.speakRoleCheckbox = wx.CheckBox(
            themePanel, -1, _("Speak roles such as button, edit box , link etc. ")
        )
        # Translators: label for a checkbox to toggle the use of audio themes during say all
        self.useInSayAllCheckbox = wx.CheckBox(
            themePanel, -1, _("Speak roles during say all")
        )
        # Translators: label for a checkbox to toggle whether the volume of this add-on should follow the synthesizer volume
        self.useSynthVolumeCheckbox = wx.CheckBox(
            themePanel, -1, _("Use speech synthesizer volume")
        )
        # Translators: label for a slider to set the volume of this add-on
        volumeLabel = wx.StaticText(themePanel, -1, _("Audio themes volume:"))
        self.volumeSlider = wx.Slider(
            themePanel, -1, minValue=0, maxValue=100, name=_("Audio themes volume")
        )
        themeSizer = wx.BoxSizer(wx.VERTICAL)
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
        themeSizer.AddMany(
            [(themesListSizer, 1, wx.EXPAND, 10), (actionSizer, 1, wx.ALIGN_CENTER, 10)]
        )
        themeSizer.AddSpacer(10)
        # Audio Ducking
        self.audioDuckingCheckbox = wx.CheckBox(themePanel, -1, _("Audio Ducking (lower volume when NVDA speaks)"))
        self.duckingCategoriesBtn = wx.Button(themePanel, -1, _("Ducking categories..."))
        self.duckingCategoriesBtn.Bind(wx.EVT_BUTTON, self.onDuckingCategories)
        self.duckingVolLabel = wx.StaticText(themePanel, -1, _("Ducked Volume (%):"))
        self.audioDuckingVolumeSlider = wx.Slider(themePanel, -1, minValue=1, maxValue=100, name=_("Ducked Volume"))
        
        # Speak Roles Checkbox (alone)
        # Say All Roles Sizer
        sayAllRolesSizer = wx.BoxSizer(wx.HORIZONTAL)
        sayAllRolesSizer.Add(self.useInSayAllCheckbox, 0, wx.ALIGN_CENTER_VERTICAL)
        self.selectRolesButton = wx.Button(themePanel, -1, _("Select Roles..."))
        self.selectRolesButton.Bind(wx.EVT_BUTTON, self.onSelectRoles)
        sayAllRolesSizer.Add(self.selectRolesButton, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        
        themeSizer.AddMany(
            [
                (self.play3dCheckbox, 0, wx.ALL, 5),
                (self.speakRoleCheckbox, 0, wx.ALL, 5),
                (sayAllRolesSizer, 0, wx.ALL, 5),
                (self.useSynthVolumeCheckbox, 0, wx.ALL, 5),
                (volumeLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 10),
                (self.volumeSlider, 0, wx.BOTTOM | wx.LEFT | wx.RIGHT, 5),
                (self.audioDuckingCheckbox, 0, wx.ALL, 5),
                (self.duckingCategoriesBtn, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 5),
                (self.duckingVolLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 10),
                (self.audioDuckingVolumeSlider, 0, wx.BOTTOM | wx.LEFT | wx.RIGHT, 5),
            ]
        )
        
        # First/Last item fallback controls
        # Build role list for custom selectors (exclude first/last to avoid circular refs)
        self.fl_choices = []
        self.fl_names = []
        for r_int, r_label in theme_roles.items():
            if r_int in (SpecialProps.first, SpecialProps.last):
                continue
            r_name = role_int_to_name.get(r_int)
            if r_name:
                self.fl_choices.append(r_label)
                self.fl_names.append(r_name)
        # Translators: label for a combobox to choose first/last item fallback behavior
        flLabel = wx.StaticText(themePanel, -1, _("When no sound for first/last item:"))
        self.firstlastFallbackChoice = wx.Choice(themePanel, -1, choices=[
            _("Play the item's role sound"),
            _("Don't play any sound"),
            _("Play the first available sound"),
            _("Use custom role sounds"),
        ], name=_("First/Last item fallback"))
        themeSizer.Add(flLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 10)
        themeSizer.Add(self.firstlastFallbackChoice, 0, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)
        # Custom role selectors for first and last
        self.firstRoleLabel = wx.StaticText(themePanel, -1, _("First item sound:"))
        self.firstRoleChoice = wx.Choice(themePanel, -1, choices=self.fl_choices, name=_("First item fallback role"))
        self.lastRoleLabel = wx.StaticText(themePanel, -1, _("Last item sound:"))
        self.lastRoleChoice = wx.Choice(themePanel, -1, choices=self.fl_choices, name=_("Last item fallback role"))
        themeSizer.Add(self.firstRoleLabel, 0, wx.LEFT | wx.RIGHT, 10)
        themeSizer.Add(self.firstRoleChoice, 0, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)
        themeSizer.Add(self.lastRoleLabel, 0, wx.LEFT | wx.RIGHT, 10)
        themeSizer.Add(self.lastRoleChoice, 0, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)
        self.Bind(wx.EVT_CHOICE, self._on_fl_fallback_changed, self.firstlastFallbackChoice)

        # General fallback controls
        # Translators: label for a combobox to choose fallback behavior when no sound is found for any role
        gfLabel = wx.StaticText(themePanel, -1, _("When no sound is found for a role or state:"))
        self.generalFallbackChoice = wx.Choice(themePanel, -1, choices=[
            _("Play the object's role sound"),
            _("Don't play any sound"),
            _("Play the first available sound"),
            _("Use custom role sound"),
        ], name=_("General fallback"))
        themeSizer.Add(gfLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 10)
        themeSizer.Add(self.generalFallbackChoice, 0, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)
        self.generalRoleLabel = wx.StaticText(themePanel, -1, _("Fallback sound:"))
        self.generalRoleChoice = wx.Choice(themePanel, -1, choices=self.fl_choices, name=_("General fallback role"))
        themeSizer.Add(self.generalRoleLabel, 0, wx.LEFT | wx.RIGHT, 10)
        themeSizer.Add(self.generalRoleChoice, 0, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)
        self.Bind(wx.EVT_CHOICE, self._on_general_fallback_changed, self.generalFallbackChoice)

        # State sounds toggle
        # Translators: checkbox for whether state sounds suppress the role sound
        self.stateSoundsSuppressCheckbox = wx.CheckBox(themePanel, -1, _("State sounds suppress the role sound"))
        themeSizer.Add(self.stateSoundsSuppressCheckbox, 0, wx.TOP | wx.LEFT | wx.RIGHT, 10)
        
        themeSizer.Fit(themePanel)
        
        # Application Blacklist
        disabledAppsLabel = wx.StaticText(themePanel, -1, _("Disable Audio Themes in these applications (comma separated):"))
        self.disabledAppsEdit = wx.TextCtrl(themePanel, -1, value="", name=_("Disable in applications"))
        self.suppressCategoriesBtn = wx.Button(themePanel, -1, _("Categories to suppress in disabled apps..."))
        self.suppressCategoriesBtn.Bind(wx.EVT_BUTTON, self.onSuppressCategories)
        themeSizer.AddMany([
            (disabledAppsLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 10),
            (self.disabledAppsEdit, 0, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 5),
            (self.suppressCategoriesBtn, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        ])
        
        themePanel.SetSizer(themeSizer)
        
        # Typing Sounds Group
        self.typingSoundsCheckbox = wx.CheckBox(innerPanel, -1, _("Enable typing sounds"))
        self.typingSoundsEditOnlyCheckbox = wx.CheckBox(innerPanel, -1, _("Play typing sounds only in edit boxes"))
        typingVolumeLabel = wx.StaticText(innerPanel, -1, _("Typing sounds volume:"))
        self.typingSoundsVolumeSlider = wx.Slider(innerPanel, -1, minValue=0, maxValue=100, name=_("Typing sounds volume"))
        
        typingPackLabel = wx.StaticText(innerPanel, -1, _("Typing sound pack:"))
        self.typingPackChoices = []
        typingSoundsDir = os.path.join(os.path.dirname(__file__), "typingSounds")
        if os.path.isdir(typingSoundsDir):
            self.typingPackChoices = [d for d in os.listdir(typingSoundsDir) if os.path.isdir(os.path.join(typingSoundsDir, d))]
        if not self.typingPackChoices:
            self.typingPackChoices = ["1blueSwitch"]

        typingPackSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.typingPackCombobox = wx.Choice(innerPanel, -1, choices=self.typingPackChoices, name=_("Typing sound pack"))
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
        
        configActionSizer = wx.BoxSizer(wx.HORIZONTAL)
        # Translators: label for a checkbox to enable automatic update checking
        self.autoUpdateCheckbox = wx.CheckBox(innerPanel, -1, _("Check for updates &automatically"))
        # Translators: label for a checkbox to include pre-release versions in updates
        self.prereleaseUpdateCheckbox = wx.CheckBox(innerPanel, -1, _("Include &pre-release (beta) versions"))
        
        updateSizer = wx.BoxSizer(wx.VERTICAL)
        updateSizer.Add(self.autoUpdateCheckbox, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        updateSizer.Add(self.prereleaseUpdateCheckbox, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        
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
        
        innerSizer = wx.BoxSizer(wx.VERTICAL)
        innerSizer.Add(themePanel, 1, wx.EXPAND | wx.ALL, 0)
        innerSizer.Add(typingSizer, 0, wx.EXPAND | wx.ALL, 10)
        innerSizer.Add(updateSizer, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
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
            self._on_enable_themes_changed,
            self.enableThemesCheckbox,
        )
        self.Bind(
            wx.EVT_CHECKBOX,
            lambda e: self.volumeSlider.Enable(not e.IsChecked()),
            self.useSynthVolumeCheckbox,
        )
        self.Bind(
            wx.EVT_CHECKBOX,
            self._on_ducking_changed,
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
        files = [f for f in os.listdir(typingSoundsDir) if f.lower().endswith(('.wav', '.ogg', '.mp3'))]
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
            files = [f for f in os.listdir(typingSoundsDir) if f.lower().endswith(('.wav', '.ogg', '.mp3'))]
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
            except Exception as e:
                import logging
                logging.getLogger("audiothemes").error(f"AudioThemes Error: {e}", exc_info=True)
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
        self.aboutTypingSoundsButton.Enable(enabled)
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

        trimSizer = wx.BoxSizer(wx.HORIZONTAL)
        trimThresholdLabel = wx.StaticText(page, -1, _("Threshold:"))
        self.trimThresholdSlider = wx.Slider(page, -1, minValue=0, maxValue=100, name=_("Trim silence threshold"))
        self.trimThresholdValueLabel = wx.StaticText(page, -1, "0.01")
        trimSizer.Add(trimThresholdLabel, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        trimSizer.Add(self.trimThresholdSlider, 1, wx.EXPAND | wx.ALL, 5)
        trimSizer.Add(self.trimThresholdValueLabel, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        engineSizer.Add(trimSizer, 0, wx.EXPAND)
        self.trimThresholdSlider.Bind(wx.EVT_SLIDER, self._onTrimThresholdChanged)

        # Noise Gate
        noiseBox = wx.StaticBox(page, -1, _("Noise Gate"))
        noiseSizer = wx.StaticBoxSizer(noiseBox, wx.VERTICAL)

        self.noiseGateCheckbox = wx.CheckBox(page, -1, _("Enable Noise Gate (remove quiet background noise)"))
        noiseSizer.Add(self.noiseGateCheckbox, 0, wx.ALL, 5)

        ngThreshSizer = wx.BoxSizer(wx.HORIZONTAL)
        ngThreshLabel = wx.StaticText(page, -1, _("Threshold:"))
        self.noiseThresholdSlider = wx.Slider(page, -1, minValue=1, maxValue=100, name=_("Noise gate threshold"))
        self.noiseThresholdValueLabel = wx.StaticText(page, -1, "0.02")
        ngThreshSizer.Add(ngThreshLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        ngThreshSizer.Add(self.noiseThresholdSlider, 1, wx.EXPAND | wx.ALL, 5)
        ngThreshSizer.Add(self.noiseThresholdValueLabel, 0, wx.ALIGN_CENTER_VERTICAL, 5)
        noiseSizer.Add(ngThreshSizer, 0, wx.EXPAND)

        ngAttackSizer = wx.BoxSizer(wx.HORIZONTAL)
        ngAttackLabel = wx.StaticText(page, -1, _("Attack (ms):"))
        self.noiseAttackSlider = wx.Slider(page, -1, minValue=1, maxValue=100, name=_("Noise gate attack"))
        self.noiseAttackValueLabel = wx.StaticText(page, -1, "5")
        ngAttackSizer.Add(ngAttackLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        ngAttackSizer.Add(self.noiseAttackSlider, 1, wx.EXPAND | wx.ALL, 5)
        ngAttackSizer.Add(self.noiseAttackValueLabel, 0, wx.ALIGN_CENTER_VERTICAL, 5)
        noiseSizer.Add(ngAttackSizer, 0, wx.EXPAND)

        ngReleaseSizer = wx.BoxSizer(wx.HORIZONTAL)
        ngReleaseLabel = wx.StaticText(page, -1, _("Release (ms):"))
        self.noiseReleaseSlider = wx.Slider(page, -1, minValue=1, maxValue=500, name=_("Noise gate release"))
        self.noiseReleaseValueLabel = wx.StaticText(page, -1, "50")
        ngReleaseSizer.Add(ngReleaseLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        ngReleaseSizer.Add(self.noiseReleaseSlider, 1, wx.EXPAND | wx.ALL, 5)
        ngReleaseSizer.Add(self.noiseReleaseValueLabel, 0, wx.ALIGN_CENTER_VERTICAL, 5)
        noiseSizer.Add(ngReleaseSizer, 0, wx.EXPAND)

        self.noiseGateCheckbox.Bind(wx.EVT_CHECKBOX, self._on_noise_gate_changed)
        self.noiseThresholdSlider.Bind(wx.EVT_SLIDER, self._on_noise_threshold_changed)
        self.noiseAttackSlider.Bind(wx.EVT_SLIDER, self._on_noise_attack_changed)
        self.noiseReleaseSlider.Bind(wx.EVT_SLIDER, self._on_noise_release_changed)

        engineSizer.Add(noiseSizer, 0, wx.EXPAND | wx.ALL, 5)

        # Bass Boost
        bassBox = wx.StaticBox(page, -1, _("Bass Boost"))
        bassSizer = wx.StaticBoxSizer(bassBox, wx.VERTICAL)

        self.bassBoostCheckbox = wx.CheckBox(page, -1, _("Enable Bass Boost (enhance low frequencies)"))
        bassSizer.Add(self.bassBoostCheckbox, 0, wx.ALL, 5)

        bassGainSizer = wx.BoxSizer(wx.HORIZONTAL)
        bassGainLabel = wx.StaticText(page, -1, _("Gain (dB):"))
        self.bassGainSlider = wx.Slider(page, -1, minValue=0, maxValue=12, name=_("Bass boost gain"))
        self.bassGainValueLabel = wx.StaticText(page, -1, "3 dB")
        bassGainSizer.Add(bassGainLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        bassGainSizer.Add(self.bassGainSlider, 1, wx.EXPAND | wx.ALL, 5)
        bassGainSizer.Add(self.bassGainValueLabel, 0, wx.ALIGN_CENTER_VERTICAL, 5)
        bassSizer.Add(bassGainSizer, 0, wx.EXPAND)

        bassCutSizer = wx.BoxSizer(wx.HORIZONTAL)
        bassCutLabel = wx.StaticText(page, -1, _("Cutoff (Hz):"))
        self.bassCutoffSlider = wx.Slider(page, -1, minValue=50, maxValue=500, name=_("Bass boost cutoff"))
        self.bassCutoffValueLabel = wx.StaticText(page, -1, "200 Hz")
        bassCutSizer.Add(bassCutLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        bassCutSizer.Add(self.bassCutoffSlider, 1, wx.EXPAND | wx.ALL, 5)
        bassCutSizer.Add(self.bassCutoffValueLabel, 0, wx.ALIGN_CENTER_VERTICAL, 5)
        bassSizer.Add(bassCutSizer, 0, wx.EXPAND)

        self.bassBoostCheckbox.Bind(wx.EVT_CHECKBOX, self._on_bass_boost_changed)
        self.bassGainSlider.Bind(wx.EVT_SLIDER, self._on_bass_gain_changed)
        self.bassCutoffSlider.Bind(wx.EVT_SLIDER, self._on_bass_cutoff_changed)

        engineSizer.Add(bassSizer, 0, wx.EXPAND | wx.ALL, 5)

        # Output Mode
        modeSizer = wx.BoxSizer(wx.HORIZONTAL)
        modeLabel = wx.StaticText(page, -1, _("Audio Output Mode:"))
        self.outputModeChoice = wx.Choice(page, -1, choices=[_("3D Spatial (Stereo)"), _("Centered (Mono)")], name=_("Audio Output Mode"))
        modeSizer.Add(modeLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        modeSizer.Add(self.outputModeChoice, 1, wx.EXPAND | wx.ALL, 0)
        engineSizer.Add(modeSizer, 0, wx.EXPAND | wx.ALL, 5)

        # Progress Bar Spatial Audio
        progressBox = wx.StaticBox(page, -1, _("Progress Bar Spatial Audio"))
        progressSizer = wx.StaticBoxSizer(progressBox, wx.VERTICAL)

        panModeSizer = wx.BoxSizer(wx.HORIZONTAL)
        panModeLabel = wx.StaticText(page, -1, _("Pan Mode:"))
        self.progressPanModeChoice = wx.Choice(page, -1, choices=[_("Progress-based (left to right)"), _("Screen position (bar location on screen)")], name=_("Progress Pan Mode"))
        panModeSizer.Add(panModeLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        panModeSizer.Add(self.progressPanModeChoice, 1, wx.EXPAND | wx.ALL, 0)
        progressSizer.Add(panModeSizer, 0, wx.EXPAND | wx.ALL, 5)

        rangeSizer = wx.BoxSizer(wx.HORIZONTAL)
        rangeLabel = wx.StaticText(page, -1, _("Pan Range:"))
        self.progressPanRangeSlider = wx.Slider(page, -1, minValue=45, maxValue=180, name=_("Progress pan range"))
        self.progressPanRangeValueLabel = wx.StaticText(page, -1, "180\xb0")
        rangeSizer.Add(rangeLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        rangeSizer.Add(self.progressPanRangeSlider, 1, wx.EXPAND | wx.ALL, 5)
        rangeSizer.Add(self.progressPanRangeValueLabel, 0, wx.ALIGN_CENTER_VERTICAL, 5)
        progressSizer.Add(rangeSizer, 0, wx.EXPAND)
        self.progressPanRangeSlider.Bind(wx.EVT_SLIDER, self._onProgressRangeChanged)

        self.progressPitchShiftCheckbox = wx.CheckBox(page, -1, _("Pitch shift with progress (higher pitch = more progress)"))
        progressSizer.Add(self.progressPitchShiftCheckbox, 0, wx.ALL, 5)

        engineSizer.Add(progressSizer, 0, wx.EXPAND | wx.ALL, 5)

        page.SetSizer(engineSizer)

    def setupAudioFormatsPage(self, page):
        """Tab: Audio Formats and FFmpeg configuration."""
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.ffmpegEnableCheckbox = wx.CheckBox(page, -1, _("Use FFmpeg for additional audio formats (MP3, FLAC, M4A, etc.)"))
        sizer.Add(self.ffmpegEnableCheckbox, 0, wx.ALL, 5)

        self.ffmpegStatusText = wx.StaticText(page, -1, _("FFmpeg status: checking..."))
        sizer.Add(self.ffmpegStatusText, 0, wx.ALL, 5)

        self.downloadFFmpegButton = wx.Button(page, -1, _("&Download and Install FFmpeg"))
        sizer.Add(self.downloadFFmpegButton, 0, wx.ALL, 5)
        self.Bind(wx.EVT_BUTTON, self.onDownloadFFmpeg, self.downloadFFmpegButton)

        sizer.AddStretchSpacer()
        infoText = wx.StaticText(page, -1, _(
            "FFmpeg enables support for many audio formats.\n"
            "Without it, WAV, OGG, MP3, and FLAC are supported natively.\n"
            "Download size: ~50MB, extracted: ~12MB."
        ))
        sizer.Add(infoText, 0, wx.ALL, 5)

        page.SetSizer(sizer)

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

    def _slider_to_threshold(self, val):
        return val / 100.0 * 0.5

    def _threshold_to_slider(self, val):
        return int(round(val / 0.5 * 100))

    def _onTrimThresholdChanged(self, event):
        val = self.trimThresholdSlider.GetValue()
        threshold = self._slider_to_threshold(val)
        if threshold == 0:
            self.trimThresholdValueLabel.SetLabel(_("0 (off)"))
        else:
            self.trimThresholdValueLabel.SetLabel(f"{threshold:.3f}")
        self.trimThresholdSlider.Enable(self.trimSilenceCheckbox.GetValue())

    def _onProgressRangeChanged(self, event):
        val = self.progressPanRangeSlider.GetValue()
        self.progressPanRangeValueLabel.SetLabel(_("%d\xb0") % val)

    # ── Noise Gate event handlers ──────────────────────────────────────

    def _noise_threshold_to_slider(self, value):
        return max(1, min(100, int(float(value) * 1000)))

    def _slider_to_noise_threshold(self, value):
        return max(0.001, min(0.1, value / 1000.0))

    def _on_noise_gate_changed(self, event):
        enabled = self.noiseGateCheckbox.GetValue()
        self.noiseThresholdSlider.Enable(enabled)
        self.noiseAttackSlider.Enable(enabled)
        self.noiseReleaseSlider.Enable(enabled)

    def _on_noise_threshold_changed(self, event):
        val = self._slider_to_noise_threshold(self.noiseThresholdSlider.GetValue())
        self.noiseThresholdValueLabel.SetLabel("%.3f" % val)

    def _on_noise_attack_changed(self, event):
        val = self.noiseAttackSlider.GetValue()
        self.noiseAttackValueLabel.SetLabel("%d" % val)

    def _on_noise_release_changed(self, event):
        val = self.noiseReleaseSlider.GetValue()
        self.noiseReleaseValueLabel.SetLabel("%d" % val)

    # ── Bass Boost event handlers ──────────────────────────────────────

    def _on_bass_boost_changed(self, event):
        enabled = self.bassBoostCheckbox.GetValue()
        self.bassGainSlider.Enable(enabled)
        self.bassCutoffSlider.Enable(enabled)

    def _on_bass_gain_changed(self, event):
        val = self.bassGainSlider.GetValue()
        self.bassGainValueLabel.SetLabel(_("%d dB") % val)

    def _on_bass_cutoff_changed(self, event):
        val = self.bassCutoffSlider.GetValue()
        self.bassCutoffValueLabel.SetLabel(_("%d Hz") % val)

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
        self.announceFormatChoice = wx.Choice(page, -1, choices=announceFormatChoices, name=_("Announcement format"))
        sizer.Add(self.announceFormatChoice, 0, wx.EXPAND | wx.ALL, 5)
        
        # --- Per-role customization ---
        separator = wx.StaticLine(page)
        sizer.Add(separator, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 8)
        
        # Translators: label for per-role customization
        perRoleLabel = wx.StaticText(page, -1, _("Customize announcement format per role:"))
        sizer.Add(perRoleLabel, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        
        # Build role list (fast — just iterates enum)
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
        self._role_list.append((SpecialProps.emoji, _("Emoji Sound")))
        self._role_list.sort(key=lambda x: x[1])
        
        # Per-role format choices
        self._PER_ROLE_FORMATS = (
            ("global", _("Use global setting")),
            ("0", _("Default (name, role then state)")),
            ("rsc", _("Role and state, then name")),
            ("sc", _("State, then name")),
        )
        
        # Search box for filtering roles
        searchSizer = wx.BoxSizer(wx.HORIZONTAL)
        searchLabel = wx.StaticText(page, -1, _("Search for a role:"))
        self.roleSearchEdit = wx.TextCtrl(page, -1, value="", name=_("Search for a role"))
        searchSizer.Add(searchLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        searchSizer.Add(self.roleSearchEdit, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(searchSizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        
        page.SetSizer(sizer)
        
        self.roleSearchEdit.Bind(wx.EVT_TEXT, self.onRoleSearch)

    def onRoleSearch(self, event):
        if not hasattr(self, 'roleListCtrl'):
            return
        self._populateRoleList(self.roleSearchEdit.GetValue().lower())

    def _createRoleGrid(self):
        self._gridFormatNames = [name for code, name in self._PER_ROLE_FORMATS]
        self._roleFormats = {}
        
        self.roleListCtrl = wx.ListCtrl(self.speechOrderPage, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SIMPLE)
        self.roleListCtrl.AppendColumn(_("Role"), width=200)
        self.roleListCtrl.AppendColumn(_("Format"), width=200)
        self.roleListCtrl.SetMinSize((-1, 200))
        
        sizer = self.speechOrderPage.GetSizer()
        sizer.Add(self.roleListCtrl, 1, wx.EXPAND | wx.ALL, 5)
        
        self.roleFormatChoice = wx.Choice(self.speechOrderPage, -1, choices=self._gridFormatNames)
        self.roleFormatChoice.Enable(False)
        sizer.Add(self.roleFormatChoice, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        sizer.Layout()
        
        self._populateRoleList()
        self.roleListCtrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self._onRoleSelected)
        self.roleFormatChoice.Bind(wx.EVT_CHOICE, self._onRoleFormatChanged)
        
        self._initSpeechOrderFormats()
        self._speechOrderLoaded = True

    def _populateRoleList(self, filterText=""):
        self.roleListCtrl.DeleteAllItems()
        for role, label in self._role_list:
            if filterText and filterText not in label.lower():
                continue
            code = self._roleFormats.get(role, "global")
            fmtName = self._gridFormatNames[0]
            for i, (c, n) in enumerate(self._PER_ROLE_FORMATS):
                if c == code:
                    fmtName = self._gridFormatNames[i]
                    break
            idx = self.roleListCtrl.Append([label, fmtName])
            self.roleListCtrl.SetItemData(idx, role.value)

    def _onRoleSelected(self, event):
        idx = event.GetIndex()
        roleValue = self.roleListCtrl.GetItemData(idx)
        role = controlTypes.Role(roleValue)
        code = self._roleFormats.get(role, "global")
        for i, (c, n) in enumerate(self._PER_ROLE_FORMATS):
            if c == code:
                self.roleFormatChoice.SetSelection(i)
                break
        self.roleFormatChoice.Enable(True)

    def _onRoleFormatChanged(self, event):
        idx = self.roleListCtrl.GetFirstSelected()
        if idx == -1:
            return
        roleValue = self.roleListCtrl.GetItemData(idx)
        role = controlTypes.Role(roleValue)
        sel = self.roleFormatChoice.GetSelection()
        if sel == wx.NOT_FOUND:
            return
        code = self._PER_ROLE_FORMATS[sel][0]
        self._roleFormats[role] = code
        self.roleListCtrl.SetItem(idx, 1, self._gridFormatNames[sel])

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
        self.appProfilesList = wx.ListCtrl(page, style=wx.LC_REPORT | wx.LC_SINGLE_SEL, name=_("Application Profiles"))
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
        self.paragraphChimeVolumeSlider = wx.Slider(page, -1, minValue=0, maxValue=100, name=_("Paragraph boundary chime volume"))
        sentBox.Add(pChimeLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        sentBox.Add(self.paragraphChimeVolumeSlider, 0, wx.EXPAND | wx.ALL, 5)

        # No next sentence chime
        nChimeLabel = wx.StaticText(page, -1, _("No more sentences chime volume:"))
        self.noNextSentenceChimeSlider = wx.Slider(page, -1, minValue=0, maxValue=100, name=_("No more sentences chime volume"))
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

        # Break at element boundaries (links, etc.)
        self.breakAtElementBoundariesCheckbox = wx.CheckBox(page, -1, _("Break sentences at element boundaries (links, separators, etc.)"))
        sentBox.Add(self.breakAtElementBoundariesCheckbox, 0, wx.ALL, 5)

        # Reconstruct mode
        self.reconstructOptions = ["always", "sameIndent", "never"]
        self.reconstructOptionsText = [_("Always"), _("Same indent and style"), _("Never")]
        reconLabel = wx.StaticText(page, -1, _("Reconstruct sentences across paragraphs:"))
        self.reconstructModeCombobox = wx.Choice(page, -1, choices=self.reconstructOptionsText, name=_("Reconstruct sentences across paragraphs"))
        sentBox.Add(reconLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        sentBox.Add(self.reconstructModeCombobox, 0, wx.EXPAND | wx.ALL, 5)

        # Sentence breakers
        breakLabel = wx.StaticText(page, -1, _("Sentence breakers:"))
        self.sentenceBreakersEdit = wx.TextCtrl(page, -1, name=_("Sentence breakers"))
        sentBox.Add(breakLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        sentBox.Add(self.sentenceBreakersEdit, 0, wx.EXPAND | wx.ALL, 5)

        # Full width sentence breakers
        fwSentenceBreakLabel = wx.StaticText(page, -1, _("Full width sentence breakers:"))
        self.fullWidthSentenceBreakersEdit = wx.TextCtrl(page, -1, name=_("Full width sentence breakers"))
        sentBox.Add(fwSentenceBreakLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        sentBox.Add(self.fullWidthSentenceBreakersEdit, 0, wx.EXPAND | wx.ALL, 5)

        # Phrase breakers
        phraseBreakLabel = wx.StaticText(page, -1, _("Phrase breakers:"))
        self.phraseBreakersEdit = wx.TextCtrl(page, -1, name=_("Phrase breakers"))
        sentBox.Add(phraseBreakLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        sentBox.Add(self.phraseBreakersEdit, 0, wx.EXPAND | wx.ALL, 5)

        # Full width phrase breakers
        fwPhraseBreakLabel = wx.StaticText(page, -1, _("Full width phrase breakers:"))
        self.fullWidthPhraseBreakersEdit = wx.TextCtrl(page, -1, name=_("Full width phrase breakers"))
        sentBox.Add(fwPhraseBreakLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        sentBox.Add(self.fullWidthPhraseBreakersEdit, 0, wx.EXPAND | wx.ALL, 5)

        # Skippable punctuation
        skipLabel = wx.StaticText(page, -1, _("Skippable punctuation:"))
        self.skippableEdit = wx.TextCtrl(page, -1, name=_("Skippable punctuation"))
        sentBox.Add(skipLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        sentBox.Add(self.skippableEdit, 0, wx.EXPAND | wx.ALL, 5)

        # Capital letters
        capsLabel = wx.StaticText(page, -1, _("Capital letters (no spaces):"))
        self.capitalLettersEdit = wx.TextCtrl(page, -1, name=_("Capital letters"))
        sentBox.Add(capsLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        sentBox.Add(self.capitalLettersEdit, 0, wx.EXPAND | wx.ALL, 5)

        # Lower case letters
        lowerLabel = wx.StaticText(page, -1, _("Lower case letters (no spaces):"))
        self.lowerCaseLettersEdit = wx.TextCtrl(page, -1, name=_("Lower case letters"))
        sentBox.Add(lowerLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        sentBox.Add(self.lowerCaseLettersEdit, 0, wx.EXPAND | wx.ALL, 5)

        # Exceptional abbreviations
        abbrLabel = wx.StaticText(page, -1, _("Exceptional abbreviations (space separated):"))
        self.exceptionalAbbreviationsEdit = wx.TextCtrl(page, -1, name=_("Exceptional abbreviations"))
        sentBox.Add(abbrLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        sentBox.Add(self.exceptionalAbbreviationsEdit, 0, wx.EXPAND | wx.ALL, 5)

        # Blacklist
        blLabel = wx.StaticText(page, -1, _("Blacklist applications for sentence navigation (comma separated):"))
        self.snAppsBlacklistEdit = wx.TextCtrl(page, -1, name=_("Blacklist applications"))
        sentBox.Add(blLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        sentBox.Add(self.snAppsBlacklistEdit, 0, wx.EXPAND | wx.ALL, 5)

        sizer.Add(sentBox, 0, wx.EXPAND | wx.ALL, 10)

        # --- Text navigation group ---
        textBox = wx.StaticBoxSizer(wx.VERTICAL, page, _("Text Navigation (Alt+Shift+Arrows)"))

        # Crackling Volume
        crackleTextLabel = wx.StaticText(page, -1, _("Paragraph crackle volume:"))
        self.textCrackleVolumeSlider = wx.Slider(page, -1, minValue=0, maxValue=100, name=_("Paragraph crackle volume"))
        textBox.Add(crackleTextLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        textBox.Add(self.textCrackleVolumeSlider, 0, wx.EXPAND | wx.ALL, 5)

        # No next text chime
        noTextChimeLabel = wx.StaticText(page, -1, _("No more text units chime volume:"))
        self.noNextTextChimeSlider = wx.Slider(page, -1, minValue=0, maxValue=100, name=_("No more text units chime volume"))
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
        self.crackleVolumeSlider = wx.Slider(page, -1, minValue=0, maxValue=100, name=_("Crackling sound volume"))
        bnBox.Add(crackleLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        bnBox.Add(self.crackleVolumeSlider, 0, wx.EXPAND | wx.ALL, 5)

        # Beep volume
        beepLabel = wx.StaticText(page, -1, _("Beeping sound volume:"))
        self.beepVolumeSlider = wx.Slider(page, -1, minValue=0, maxValue=100, name=_("Beeping sound volume"))
        bnBox.Add(beepLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        bnBox.Add(self.beepVolumeSlider, 0, wx.EXPAND | wx.ALL, 5)

        # Skip Clutter volume
        skipLabel = wx.StaticText(page, -1, _("Skip Clutter chime volume:"))
        self.skipChimeVolumeSlider = wx.Slider(page, -1, minValue=0, maxValue=100, name=_("Skip Clutter chime volume"))
        bnBox.Add(skipLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        bnBox.Add(self.skipChimeVolumeSlider, 0, wx.EXPAND | wx.ALL, 5)

        sizer.Add(bnBox, 0, wx.EXPAND | wx.ALL, 10)

        # --- Navigation Layer group ---
        navLayerBox = wx.StaticBoxSizer(wx.VERTICAL, page, _("Navigation Layer (NVDA+Windows+N)") if "_" in globals() else "Navigation Layer (NVDA+Windows+N)")

        # Pass-through Unknown Keys
        self.navLayerPassThroughCheckbox = wx.CheckBox(page, -1, _("Pass-through unknown keys (Auto-exit on typing)") if "_" in globals() else "Pass-through unknown keys (Auto-exit on typing)")
        navLayerBox.Add(self.navLayerPassThroughCheckbox, 0, wx.ALL, 5)

        # Auto-Exit Timeout
        self.navLayerTimeoutCheckbox = wx.CheckBox(page, -1, _("Auto-exit layer after 10 seconds of inactivity") if "_" in globals() else "Auto-exit layer after 10 seconds of inactivity")
        navLayerBox.Add(self.navLayerTimeoutCheckbox, 0, wx.ALL, 5)

        # Play Sounds
        self.navLayerPlaySoundsCheckbox = wx.CheckBox(page, -1, _("Play sounds for layer actions") if "_" in globals() else "Play sounds for layer actions")
        navLayerBox.Add(self.navLayerPlaySoundsCheckbox, 0, wx.ALL, 5)

        # Available Modes
        modeLabel = wx.StaticText(page, -1, _("Active Navigation Modes:") if "_" in globals() else "Active Navigation Modes:")
        navLayerBox.Add(modeLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        
        from .navLayer import NavLayerMixin
        self.navLayerAllModes = NavLayerMixin._ALL_MODES
        self.navLayerModeNames = [m["name"] for m in self.navLayerAllModes]
        from gui.nvdaControls import CustomCheckListBox
        self.navLayerModesList = CustomCheckListBox(page, -1, choices=self.navLayerModeNames)
        self.navLayerModesList.SetMinSize((-1, 150))
        navLayerBox.Add(self.navLayerModesList, 0, wx.EXPAND | wx.ALL, 5)

        sizer.Add(navLayerBox, 0, wx.EXPAND | wx.ALL, 10)

        noteLabel = wx.StaticText(page, -1, _("Note: These settings adjust the audio feedback for SentenceNav, TextNav, and BrowserNav integrations."))
        sizer.Add(noteLabel, 0, wx.ALL, 10)

        page.SetSizer(sizer)

    # ── First/Last Item tab ──────────────────────────────────────────────

    def setupFirstLastPage(self, page):
        """Tab: First/Last Item universal detection settings."""
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Global toggle
        self.flEnableCheckbox = wx.CheckBox(page, -1, _("Enable first/last item detection"))
        sizer.Add(self.flEnableCheckbox, 0, wx.ALL, 10)

        # Detection Mode
        modeBox = wx.StaticBoxSizer(wx.VERTICAL, page, _("Detection mode"))
        modeHelp = wx.StaticText(page, -1, _(
            "Controls how first/last items are identified."
        ))
        modeBox.Add(modeHelp, 0, wx.ALL, 5)
        self.flModeChoice = wx.Choice(page, -1, choices=[
            _("Smart (Recommended) – ignore separators, fall back to any adjacent item"),
            _("Strict – same role only"),
            _("Any adjacent item – standard"),
        ], name=_("Detection mode"))
        modeBox.Add(self.flModeChoice, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(modeBox, 0, wx.EXPAND | wx.ALL, 10)

        # Detection scope
        scopeBox = wx.StaticBoxSizer(wx.VERTICAL, page, _("Detection scope"))
        self.flScopeAll = wx.RadioButton(page, -1, _("Apply to all roles"), style=wx.RB_GROUP)
        self.flScopeSelected = wx.RadioButton(page, -1, _("Apply to selected roles only"))
        self.flSelectRolesBtn = wx.Button(page, -1, _("Select roles..."))
        self.flSelectRolesBtn.Enable(False)
        scopeBox.Add(self.flScopeAll, 0, wx.ALL, 5)
        scopeBox.Add(self.flScopeSelected, 0, wx.ALL, 5)
        scopeBox.Add(self.flSelectRolesBtn, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.Bind(wx.EVT_RADIOBUTTON, self._on_fl_scope_changed, self.flScopeAll)
        self.Bind(wx.EVT_RADIOBUTTON, self._on_fl_scope_changed, self.flScopeSelected)
        self.Bind(wx.EVT_BUTTON, self._on_fl_select_roles, self.flSelectRolesBtn)
        sizer.Add(scopeBox, 0, wx.EXPAND | wx.ALL, 10)

        # Solo items behavior
        soloBox = wx.StaticBoxSizer(wx.VERTICAL, page, _("Solo items"))
        soloHelp = wx.StaticText(page, -1, _(
            "Solo items are items that have no siblings of the same type."
        ))
        soloBox.Add(soloHelp, 0, wx.ALL, 5)
        soloLabel = wx.StaticText(page, -1, _("Behavior:"))
        self.flSoloChoice = wx.Choice(page, -1, choices=[
            _("Detect as first item"),
            _("Detect as last item"),
            _("Don't detect solo items"),
        ], name=_("Solo item behavior"))
        soloBox.Add(soloLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        soloBox.Add(self.flSoloChoice, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(soloBox, 0, wx.EXPAND | wx.ALL, 10)

        # Note about fallback
        noteLabel = wx.StaticText(page, -1, _(
            "Note: Fallback behavior when no first/last sound exists can be configured in the General tab under \"When no sound for first/last item\"."
        ))
        sizer.Add(noteLabel, 0, wx.ALL, 10)

        sizer.AddStretchSpacer()
        page.SetSizer(sizer)

    def setupSystemStatusPage(self, page):
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Master enable
        self.sysStatusEnableCheckbox = wx.CheckBox(page, -1, _("Enable system status sounds"))
        sizer.Add(self.sysStatusEnableCheckbox, 0, wx.ALL, 10)

        # Volume slider
        volLabel = wx.StaticText(page, -1, _("System status sounds volume:"))
        self.sysStatusVolumeSlider = wx.Slider(page, -1, minValue=0, maxValue=100, name=_("System status sounds volume"))
        sizer.Add(volLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 10)
        sizer.Add(self.sysStatusVolumeSlider, 0, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)

        # USB monitoring mode
        usbBox = wx.StaticBoxSizer(wx.VERTICAL, page, _("USB Monitoring"))
        self.sysAllUsbCheckbox = wx.CheckBox(page, -1, _("Monitor all USB devices (keyboard, mouse, storage, etc.)"))
        usbBox.Add(self.sysAllUsbCheckbox, 0, wx.ALL, 5)
        sizer.Add(usbBox, 0, wx.EXPAND | wx.ALL, 10)

        # Per-event toggles
        eventsBox = wx.StaticBoxSizer(wx.VERTICAL, page, _("Events"))

        self.sysAcEnableCheckbox = wx.CheckBox(page, -1, _("AC power connected/disconnected"))
        eventsBox.Add(self.sysAcEnableCheckbox, 0, wx.ALL, 5)
        self.sysBatteryEnableCheckbox = wx.CheckBox(page, -1, _("Battery level changes (low, critical, full)"))
        eventsBox.Add(self.sysBatteryEnableCheckbox, 0, wx.ALL, 5)
        self.sysUsbEnableCheckbox = wx.CheckBox(page, -1, _("USB device plug/unplug"))
        eventsBox.Add(self.sysUsbEnableCheckbox, 0, wx.ALL, 5)
        self.sysVolumeEnableCheckbox = wx.CheckBox(page, -1, _("Storage volume mount/unmount"))
        eventsBox.Add(self.sysVolumeEnableCheckbox, 0, wx.ALL, 5)
        self.sysNetworkEnableCheckbox = wx.CheckBox(page, -1, _("Network connect/disconnect"))
        eventsBox.Add(self.sysNetworkEnableCheckbox, 0, wx.ALL, 5)
        self.sysWakeEnableCheckbox = wx.CheckBox(page, -1, _("System wake/sleep"))
        eventsBox.Add(self.sysWakeEnableCheckbox, 0, wx.ALL, 5)

        sizer.Add(eventsBox, 0, wx.EXPAND | wx.ALL, 10)

        # Battery thresholds
        thresholdBox = wx.StaticBoxSizer(wx.VERTICAL, page, _("Battery Thresholds"))

        lowLabel = wx.StaticText(page, -1, _("Low battery threshold (%):"))
        self.sysBatteryLowSpin = wx.SpinCtrl(page, -1, min=0, max=100, initial=20, name=_("Low battery threshold"))
        thresholdBox.Add(lowLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        thresholdBox.Add(self.sysBatteryLowSpin, 0, wx.EXPAND | wx.ALL, 5)

        critLabel = wx.StaticText(page, -1, _("Critical battery threshold (%):"))
        self.sysBatteryCriticalSpin = wx.SpinCtrl(page, -1, min=0, max=100, initial=10, name=_("Critical battery threshold"))
        thresholdBox.Add(critLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        thresholdBox.Add(self.sysBatteryCriticalSpin, 0, wx.EXPAND | wx.ALL, 5)

        sizer.Add(thresholdBox, 0, wx.EXPAND | wx.ALL, 10)

        # Check intervals
        intervalBox = wx.StaticBoxSizer(wx.VERTICAL, page, _("Check Intervals"))

        netLabel = wx.StaticText(page, -1, _("Network check interval (seconds):"))
        self.sysNetworkIntervalSpin = wx.SpinCtrl(page, -1, min=5, max=300, initial=15, name=_("Network check interval"))
        intervalBox.Add(netLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        intervalBox.Add(self.sysNetworkIntervalSpin, 0, wx.EXPAND | wx.ALL, 5)

        batLabel = wx.StaticText(page, -1, _("Battery check interval (seconds):"))
        self.sysBatteryIntervalSpin = wx.SpinCtrl(page, -1, min=5, max=300, initial=30, name=_("Battery check interval"))
        intervalBox.Add(batLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        intervalBox.Add(self.sysBatteryIntervalSpin, 0, wx.EXPAND | wx.ALL, 5)

        sizer.Add(intervalBox, 0, wx.EXPAND | wx.ALL, 10)

        # Sound file naming note
        noteBox = wx.StaticBoxSizer(wx.VERTICAL, page, _("Custom Sound Files"))
        note = wx.StaticText(page, -1, _(
            "Place .wav files in your theme folder with these names:\n"
            "sys_ac_plug.wav, sys_ac_unplug.wav, sys_battery_low.wav,\n"
            "sys_battery_critical.wav, sys_battery_full.wav, sys_usb_plug.wav,\n"
            "sys_usb_unplug.wav, sys_volume_plug.wav, sys_volume_unplug.wav,\n"
            "sys_network_connect.wav, sys_network_disconnect.wav,\n"
            "sys_wake.wav, sys_sleep.wav"
        ))
        noteBox.Add(note, 0, wx.ALL, 10)
        sizer.Add(noteBox, 0, wx.EXPAND | wx.ALL, 10)

        sizer.AddStretchSpacer()
        page.SetSizer(sizer)

    def setupEmojiPage(self, page):
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Master enable
        self.emojiEnableCheckbox = wx.CheckBox(page, -1, _("Enable emoji sounds and speech prefix"))
        sizer.Add(self.emojiEnableCheckbox, 0, wx.ALL, 10)

        # Sound enable
        self.emojiSoundCheckbox = wx.CheckBox(page, -1, _("Play sound when emoji is encountered"))
        sizer.Add(self.emojiSoundCheckbox, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Speech prefix enable
        self.emojiPrefixCheckbox = wx.CheckBox(page, -1, _("Speak prefix text before emoji descriptions"))
        sizer.Add(self.emojiPrefixCheckbox, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Prefix text
        prefixLabel = wx.StaticText(page, -1, _("Prefix text:"))
        self.emojiPrefixTextCtrl = wx.TextCtrl(page, -1, name=_("Emoji prefix text"))
        sizer.Add(prefixLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 10)
        sizer.Add(self.emojiPrefixTextCtrl, 0, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)

        # Prefix position
        posLabel = wx.StaticText(page, -1, _("Prefix position:"))
        self.emojiPositionChoice = wx.Choice(page, -1, choices=[
            _("Before emoji"),
            _("After emoji"),
            _("Before and after"),
            _("No prefix"),
        ], name=_("Prefix position"))
        sizer.Add(posLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 10)
        sizer.Add(self.emojiPositionChoice, 0, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)

        # Repeat mode
        repeatLabel = wx.StaticText(page, -1, _("Repeat mode:"))
        self.emojiRepeatChoice = wx.Choice(page, -1, choices=[
            _("Once per emoji character"),
            _("Once per text block"),
        ], name=_("Emoji repeat mode"))
        sizer.Add(repeatLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 10)
        sizer.Add(self.emojiRepeatChoice, 0, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)

        # Volume slider
        volLabel = wx.StaticText(page, -1, _("Emoji sound volume:"))
        self.emojiVolumeSlider = wx.Slider(page, -1, minValue=0, maxValue=100, name=_("Emoji sound volume"))
        sizer.Add(volLabel, 0, wx.TOP | wx.LEFT | wx.RIGHT, 10)
        sizer.Add(self.emojiVolumeSlider, 0, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)

        # Category checkboxes
        catBox = wx.StaticBoxSizer(wx.VERTICAL, page, _("Emoji Categories"))
        self.emojiCatCheckboxes = {}
        cats = [
            ("emoji_cat_smileys", _("Smileys & Emotion")),
            ("emoji_cat_people", _("People & Body")),
            ("emoji_cat_animals", _("Animals & Nature")),
            ("emoji_cat_food", _("Food & Drink")),
            ("emoji_cat_travel", _("Travel & Places")),
            ("emoji_cat_activities", _("Activities")),
            ("emoji_cat_objects", _("Objects")),
            ("emoji_cat_symbols", _("Symbols")),
            ("emoji_cat_flags", _("Flags")),
        ]
        for key, label in cats:
            cb = wx.CheckBox(page, -1, label)
            self.emojiCatCheckboxes[key] = cb
            catBox.Add(cb, 0, wx.ALL, 5)
        sizer.Add(catBox, 0, wx.EXPAND | wx.ALL, 10)

        # Note about role assignment
        noteBox = wx.StaticBoxSizer(wx.VERTICAL, page, _("Note"))
        note = wx.StaticText(page, -1, _(
            "Emoji is now available as a role in the Audio Themes role system.\n"
            "You can assign a custom emoji sound in your theme by creating\n"
            "an emoji.wav file, or configure it via the role selection dialogs\n"
            "in the First/Last and Speech Order tabs."
        ))
        noteBox.Add(note, 0, wx.ALL, 10)
        sizer.Add(noteBox, 0, wx.EXPAND | wx.ALL, 10)

        sizer.AddStretchSpacer()
        page.SetSizer(sizer)

    def onSelectRoles(self, event):
        dlg = RoleSelectionDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            self.blacklisted_roles = dlg.getBlacklistedRoles()
        dlg.Destroy()

    def onDuckingCategories(self, event):
        dlg = DuckingCategoriesDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            self._ducking_categories = dlg.getCategories()
        dlg.Destroy()

    def onSuppressCategories(self, event):
        dlg = SuppressCategoriesDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            self._suppress_categories = dlg.getCategories()
        dlg.Destroy()

    def _initialize_at_state(self):
        def _b(v):
            if isinstance(v, str): return v.lower() == 'true'
            return bool(v)
        def _i(v, d=100):
            try: return int(v)
            except (ValueError, TypeError): return d

        conf = config.conf["audiothemes"]
        self.enableThemesCheckbox.SetValue(_b(conf.get("enable_audio_themes", True)))
        self.play3dCheckbox.SetValue(_b(conf.get("audio3d", True)))
        self.speakRoleCheckbox.SetValue(_b(conf.get("speak_roles", True)))
        self.useInSayAllCheckbox.SetValue(_b(conf.get("use_in_say_all", False)))
        self.useSynthVolumeCheckbox.SetValue(_b(conf.get("use_synth_volume", True)))
        self.volumeSlider.SetValue(_i(conf.get("volume", 100)))
        self.disabledAppsEdit.SetValue(conf.get("disabled_apps", ""))
        self.blacklisted_roles = _get_blacklisted_roles()
        self.autoUpdateCheckbox.SetValue(_b(conf.get("check_for_updates_auto", True)))
        self.prereleaseUpdateCheckbox.SetValue(_b(conf.get("check_for_updates_prerelease", False)))
        
        duck_val = conf.get("audio_ducking_enabled", True)
        if isinstance(duck_val, str):
            duck_val = duck_val.lower() == 'true'
        self.audioDuckingCheckbox.SetValue(_b(bool(duck_val)))
        
        duck_cat_str = conf.get("ducking_categories", "")
        if duck_cat_str:
            try:
                self._ducking_categories = json.loads(duck_cat_str)
            except Exception:
                self._ducking_categories = dict(_DEFAULT_DUCKING_CATEGORIES)
        else:
            self._ducking_categories = dict(_DEFAULT_DUCKING_CATEGORIES)

        suppress_cat_str = conf.get("disabled_apps_suppress_categories", "")
        if suppress_cat_str:
            try:
                self._suppress_categories = json.loads(suppress_cat_str)
            except Exception:
                self._suppress_categories = dict(_DEFAULT_DUCKING_CATEGORIES)
        else:
            self._suppress_categories = dict(_DEFAULT_DUCKING_CATEGORIES)

        duck_vol = conf.get("audio_ducking_volume", 30)
        if isinstance(duck_vol, str):
            try:
                duck_vol = int(duck_vol)
            except ValueError:
                duck_vol = 30
        self.audioDuckingVolumeSlider.SetValue(_i(duck_vol))
        self._set_ducking_controls_visibility(bool(duck_val))
        
        unspoken_conf = config.conf["unspoken"]
        self.audioCacheCheckbox.SetValue(_b(unspoken_conf.get("AudioCache", True)))
        self.smartVolumeCheckbox.SetValue(_b(unspoken_conf.get("SmartVolume", False)))
        self.smoothEnvelopeCheckbox.SetValue(_b(unspoken_conf.get("SmoothEnvelope", False)))
        self.smoothPanningCheckbox.SetValue(_b(unspoken_conf.get("SmoothPanning", True)))
        trim_sil = unspoken_conf.get("TrimSilence", True)
        if isinstance(trim_sil, str):
            trim_sil = trim_sil.lower() == "true"
        self.trimSilenceCheckbox.SetValue(_b(bool(trim_sil)))
        trim_threshold = unspoken_conf.get("TrimSilenceThreshold", 0.01)
        if isinstance(trim_threshold, str):
            try:
                trim_threshold = float(trim_threshold)
            except ValueError:
                trim_threshold = 0.01
        slider_val = self._threshold_to_slider(float(trim_threshold))
        self.trimThresholdSlider.SetValue(slider_val)
        self._onTrimThresholdChanged(None)
        self.trimThresholdSlider.Enable(self.trimSilenceCheckbox.GetValue())
        self.trimThresholdValueLabel.Enable(self.trimSilenceCheckbox.GetValue())
        self.noiseGateCheckbox.SetValue(_b(unspoken_conf.get("NoiseGate", False)))
        ng_threshold = float(unspoken_conf.get("NoiseGateThreshold", 0.02))
        self.noiseThresholdSlider.SetValue(self._noise_threshold_to_slider(ng_threshold))
        self._on_noise_threshold_changed(None)
        ng_attack = int(unspoken_conf.get("NoiseGateAttack", 5))
        self.noiseAttackSlider.SetValue(ng_attack)
        self._on_noise_attack_changed(None)
        ng_release = int(unspoken_conf.get("NoiseGateRelease", 50))
        self.noiseReleaseSlider.SetValue(ng_release)
        self._on_noise_release_changed(None)
        self._on_noise_gate_changed(None)

        self.bassBoostCheckbox.SetValue(_b(unspoken_conf.get("BassBoost", False)))
        bb_gain = int(unspoken_conf.get("BassBoostGain", 3))
        self.bassGainSlider.SetValue(bb_gain)
        self._on_bass_gain_changed(None)
        bb_cutoff = int(unspoken_conf.get("BassBoostCutoff", 200))
        self.bassCutoffSlider.SetValue(bb_cutoff)
        self._on_bass_cutoff_changed(None)
        self._on_bass_boost_changed(None)
        
        mode = conf.get("output_mode", "stereo")
        if mode == "mono":
            self.outputModeChoice.SetSelection(1)
        else:
            self.outputModeChoice.SetSelection(0)

        # Progress bar spatial audio
        pan_mode = conf.get("progress_pan_mode", "progress")
        self.progressPanModeChoice.SetSelection(0 if pan_mode == "progress" else 1)
        pan_range = _i(conf.get("progress_pan_range", 180))
        self.progressPanRangeSlider.SetValue(pan_range)
        self._onProgressRangeChanged(None)
        self.progressPitchShiftCheckbox.SetValue(_b(conf.get("progress_pitch_shift", True)))

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

        # First/Last item fallback
        fl_map = {"role": 0, "silence": 1, "first_available": 2, "custom_role": 3}
        fl_val = conf.get("firstlast_fallback", "role")
        fl_idx = fl_map.get(fl_val, 0)
        self.firstlastFallbackChoice.SetSelection(fl_idx)
        # Set custom role selectors
        f_name = conf.get("first_fallback_role_name", "listitem")
        l_name = conf.get("last_fallback_role_name", "listitem")
        f_idx = self.fl_names.index(f_name) if f_name in self.fl_names else 0
        l_idx = self.fl_names.index(l_name) if l_name in self.fl_names else 0
        self.firstRoleChoice.SetSelection(f_idx)
        self.lastRoleChoice.SetSelection(l_idx)
        # Show/hide custom role selectors
        show_custom = fl_idx == 3
        self.firstRoleLabel.Show(show_custom)
        self.firstRoleChoice.Show(show_custom)
        self.lastRoleLabel.Show(show_custom)
        self.lastRoleChoice.Show(show_custom)

        # General fallback
        gf_map = {"role": 0, "silence": 1, "first_available": 2, "custom_role": 3}
        gf_val = conf.get("general_fallback", "role")
        gf_idx = gf_map.get(gf_val, 0)
        self.generalFallbackChoice.SetSelection(gf_idx)
        g_name = conf.get("general_fallback_role_name", "listitem")
        g_idx = self.fl_names.index(g_name) if g_name in self.fl_names else 0
        self.generalRoleChoice.SetSelection(g_idx)
        show_gf_custom = gf_idx == 3
        self.generalRoleLabel.Show(show_gf_custom)
        self.generalRoleChoice.Show(show_gf_custom)

        # State sounds toggle
        self.stateSoundsSuppressCheckbox.SetValue(conf.get("state_sounds_suppress_role", False))

        # First/Last Item tab
        self.flEnableCheckbox.SetValue(_b(conf.get("universal_fl_enabled", True)))
        fl_mode_map = {"smart": 0, "strict": 1, "any_sibling": 2}
        fl_mode_val = conf.get("fl_detection_mode", "smart")
        self.flModeChoice.SetSelection(fl_mode_map.get(fl_mode_val, 0))
        fl_roles_raw = conf.get("fl_enabled_roles", "all")
        if fl_roles_raw == "all":
            self.flScopeAll.SetValue(True)
            self.flSelectRolesBtn.Enable(False)
        else:
            self.flScopeSelected.SetValue(True)
            self.flSelectRolesBtn.Enable(True)
            try:
                self._fl_enabled_roles_list = json.loads(fl_roles_raw)
            except Exception:
                self._fl_enabled_roles_list = []
        solo_map = {"first": 0, "last": 1, "none": 2}
        solo_val = conf.get("fl_solo_behavior", "first")
        self.flSoloChoice.SetSelection(solo_map.get(solo_val, 0))

        # System Status tab
        self.sysStatusEnableCheckbox.SetValue(_b(conf.get("sys_status_enabled", True)))
        self.sysStatusVolumeSlider.SetValue(_i(conf.get("sys_status_volume", 20)))
        self.sysAllUsbCheckbox.SetValue(_b(conf.get("sys_all_usb", True)))
        self.sysAcEnableCheckbox.SetValue(_b(conf.get("sys_ac_enabled", True)))
        self.sysBatteryEnableCheckbox.SetValue(_b(conf.get("sys_battery_enabled", True)))
        self.sysUsbEnableCheckbox.SetValue(_b(conf.get("sys_usb_enabled", True)))
        self.sysVolumeEnableCheckbox.SetValue(_b(conf.get("sys_volume_enabled", True)))
        self.sysNetworkEnableCheckbox.SetValue(_b(conf.get("sys_network_enabled", True)))
        self.sysWakeEnableCheckbox.SetValue(_b(conf.get("sys_wake_enabled", True)))
        self.sysBatteryLowSpin.SetValue(_i(conf.get("sys_battery_low_threshold", 20)))
        self.sysBatteryCriticalSpin.SetValue(_i(conf.get("sys_battery_critical_threshold", 10)))
        self.sysNetworkIntervalSpin.SetValue(_i(conf.get("sys_network_check_interval", 15), 15))
        self.sysBatteryIntervalSpin.SetValue(_i(conf.get("sys_battery_check_interval", 30), 30))

        # Emoji tab
        self.emojiEnableCheckbox.SetValue(_b(conf.get("emoji_enabled", True)))
        self.emojiSoundCheckbox.SetValue(_b(conf.get("emoji_sound", True)))
        self.emojiPrefixCheckbox.SetValue(_b(conf.get("emoji_prefix", True)))
        self.emojiPrefixTextCtrl.SetValue(conf.get("emoji_prefix_text", "emoji"))
        pos_map = {"before": 0, "after": 1, "both": 2, "none": 3}
        pos_val = conf.get("emoji_position", "before")
        self.emojiPositionChoice.SetSelection(pos_map.get(pos_val, 0))
        rep_map = {"per_emoji": 0, "per_block": 1}
        rep_val = conf.get("emoji_repeat", "per_emoji")
        self.emojiRepeatChoice.SetSelection(rep_map.get(rep_val, 0))
        self.emojiVolumeSlider.SetValue(_i(conf.get("emoji_volume", 20)))
        for key in self.emojiCatCheckboxes:
            self.emojiCatCheckboxes[key].SetValue(_b(conf.get(key, True)))

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

        if hasattr(self, '_roleFormats'):
            for role, label in self._role_list:
                role_key = str(role.value) if hasattr(role, 'value') else str(role)
                self._roleFormats[role] = roleFormatsDict.get(role_key, "global")
            self._populateRoleList()
        
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
        self.breakAtElementBoundariesCheckbox.SetValue(_b(snConf.get("breakAtElementBoundaries", True)))
        
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

        # Miscellaneous tab — Navigation Layer settings
        nlConf = config.conf.get("audiothemes", {})
        self.navLayerPassThroughCheckbox.SetValue(_b(nlConf.get("navLayerPassThrough", True)))
        self.navLayerTimeoutCheckbox.SetValue(_b(nlConf.get("navLayerTimeout", True)))
        self.navLayerPlaySoundsCheckbox.SetValue(_b(nlConf.get("navLayerPlaySounds", True)))

        import json
        try:
            enabled_ids = json.loads(nlConf.get("navLayerEnabledModes", "[]"))
        except Exception:
            enabled_ids = []
        if not enabled_ids:
            enabled_ids = [m["id"] for m in self.navLayerAllModes]
        checked_indices = []
        for i, m in enumerate(self.navLayerAllModes):
            if m["id"] in enabled_ids:
                checked_indices.append(i)
        self.navLayerModesList.SetCheckedItems(checked_indices)

        # Audio Formats tab — FFmpeg
        audioConf = config.conf["audiothemes"]
        self.ffmpegEnableCheckbox.SetValue(audioConf.get("enable_ffmpeg", False))
        self._updateFFmpegStatus()

    def _updateFFmpegStatus(self):
        try:
            from .unspoken import ffmpeg_utils
            path = ffmpeg_utils.get_ffmpeg_path()
            if path:
                self.ffmpegStatusText.SetLabel(_("FFmpeg: available at {path}").format(path=path))
                self.downloadFFmpegButton.Enable(False)
            else:
                self.ffmpegStatusText.SetLabel(_("FFmpeg: not installed"))
                self.downloadFFmpegButton.Enable(True)
        except Exception:
            self.ffmpegStatusText.SetLabel(_("FFmpeg: not available"))
            self.downloadFFmpegButton.Enable(True)

    def onDownloadFFmpeg(self, event):
        self.downloadFFmpegButton.Enable(False)
        self.downloadFFmpegButton.SetLabel(_("Downloading..."))
        import wx
        from .unspoken import ffmpeg_utils
        def cb(progress, msg):
            wx.CallAfter(lambda: self.ffmpegStatusText.SetLabel(msg))
            if progress >= 0:
                wx.CallAfter(lambda: self.downloadFFmpegButton.SetLabel(
                    _(f"Downloading... {progress}%")))
            else:
                wx.CallAfter(lambda: self.downloadFFmpegButton.Enable(True))
                wx.CallAfter(lambda: self.downloadFFmpegButton.SetLabel(
                    _("&Download and Install FFmpeg")))
        result = ffmpeg_utils.download_ffmpeg(progress_callback=cb)
        if result:
            wx.CallAfter(self._updateFFmpegStatus)
        else:
            wx.CallAfter(lambda: self.ffmpegStatusText.SetLabel(_("FFmpeg download failed.")))
            wx.CallAfter(lambda: self.downloadFFmpegButton.Enable(True))
            wx.CallAfter(lambda: self.downloadFFmpegButton.SetLabel(
                _("&Download and Install FFmpeg")))

    def _on_enable_themes_changed(self, event):
        show = event.IsChecked()
        self.themePanel.Show(show)
        self.innerPanel.GetSizer().Layout()

    def _on_ducking_changed(self, event):
        self._set_ducking_controls_visibility(event.IsChecked())
        self.innerPanel.GetSizer().Layout()

    def _set_ducking_controls_visibility(self, show):
        self.duckingCategoriesBtn.Show(show)
        self.duckingVolLabel.Show(show)
        self.audioDuckingVolumeSlider.Show(show)

    def _on_fl_fallback_changed(self, event):
        show = self.firstlastFallbackChoice.GetSelection() == 3
        self.firstRoleLabel.Show(show)
        self.firstRoleChoice.Show(show)
        self.lastRoleLabel.Show(show)
        self.lastRoleChoice.Show(show)
        self.themePanel.GetSizer().Layout()

    def _on_general_fallback_changed(self, event):
        show = self.generalFallbackChoice.GetSelection() == 3
        self.generalRoleLabel.Show(show)
        self.generalRoleChoice.Show(show)
        self.themePanel.GetSizer().Layout()

    # ── First/Last tab event handlers ────────────────────────────────────

    def _on_fl_scope_changed(self, event):
        self.flSelectRolesBtn.Enable(self.flScopeSelected.GetValue())
        if self.flScopeSelected.GetValue() and not hasattr(self, '_fl_enabled_roles_list'):
            import json
            conf = config.conf["audiothemes"]
            raw = conf.get("fl_enabled_roles", "all")
            if raw == "all":
                self._fl_enabled_roles_list = ["listitem", "treeviewitem", "menuitem", "tab"]
            else:
                try:
                    self._fl_enabled_roles_list = json.loads(raw)
                except Exception:
                    self._fl_enabled_roles_list = ["listitem", "treeviewitem", "menuitem", "tab"]

    def _on_fl_select_roles(self, event):
        """Show dialog to pick which roles get first/last detection."""
        current = getattr(self, '_fl_enabled_roles_list', [])
        dlg = wx.Dialog(self, title=_("Select roles for first/last detection"))
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(dlg, -1, _("Select the roles that should have first/last item detection:"))
        mainSizer.Add(label, 0, wx.ALL | wx.EXPAND, 10)
        lst = wx.ListView(dlg, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_NO_HEADER, name=_("Roles"))
        lst.EnableCheckBoxes(True)
        lst.InsertColumn(0, _("Role"), width=360)
        mainSizer.Add(lst, 1, wx.ALL | wx.EXPAND, 10)
        # Populate – include all SpecialProps and controlTypes roles
        items = []  # (int_val, name, label)
        for r_int, r_label in theme_roles.items():
            r_name = role_int_to_name.get(r_int)
            if r_name:
                items.append((r_int, r_name, r_label))
        items.sort(key=lambda x: x[2].lower())
        for i, (r_int, r_name, r_label) in enumerate(items):
            lst.InsertItem(i, r_label)
            if r_name in current:
                lst.CheckItem(i, True)
        def _toggle_all(state):
            for j in range(lst.GetItemCount()):
                lst.CheckItem(j, state)
        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        selectAllBtn = wx.Button(dlg, -1, _("Select All"))
        deselectAllBtn = wx.Button(dlg, -1, _("Deselect All"))
        selectAllBtn.Bind(wx.EVT_BUTTON, lambda e: _toggle_all(True))
        deselectAllBtn.Bind(wx.EVT_BUTTON, lambda e: _toggle_all(False))
        btnSizer.Add(selectAllBtn, 0, wx.RIGHT, 5)
        btnSizer.Add(deselectAllBtn, 0)
        mainSizer.Add(btnSizer, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        stdBtns = dlg.CreateButtonSizer(wx.OK | wx.CANCEL)
        mainSizer.Add(stdBtns, 0, wx.ALL | wx.ALIGN_RIGHT, 10)
        dlg.SetSizer(mainSizer)
        dlg.SetMinSize((400, 500))
        dlg.Fit()
        if dlg.ShowModal() == wx.ID_OK:
            self._fl_enabled_roles_list = []
            for j in range(lst.GetItemCount()):
                if lst.IsItemChecked(j):
                    r_name = items[j][1]
                    self._fl_enabled_roles_list.append(r_name)
        dlg.Destroy()

    def _maintain_state(self):
        self.audio_themes = sorted(AudioThemesHandler.get_installed_themes())
        self.installedThemesChoice.Clear()
        for theme in self.audio_themes:
            self.installedThemesChoice.Append(theme.name, theme)
        for theme in self.audio_themes:
            if theme.folder == config.conf["audiothemes"]["active_theme"]:
                self.installedThemesChoice.SetStringSelection(theme.name)
        self._on_enable_themes_changed(DummyEvent(self.enableThemesCheckbox.IsChecked()))
        self.volumeSlider.Enable(not self.useSynthVolumeCheckbox.IsChecked())
        self._suppressPreview = True
        self.onThemeSelectionChanged(None)
        self._suppressPreview = False
        if hasattr(self, "appProfilesList"):
            self._updateAppProfilesList()

    def _onLazyLoadTab(self, event):
        event.Skip()
        idx = event.GetSelection()
        page = self.notebook.GetPage(idx)
        if page is self.rulesPage and not self._rulesLoaded:
            wx.CallAfter(self._loadRulesPage)
        elif page is self.quickJumpPage and not self._quickJumpLoaded:
            wx.CallAfter(self._loadQuickJumpPage)
        elif page is self.speechOrderPage and not self._speechOrderLoaded:
            wx.CallAfter(self._loadSpeechOrderPage)

    def _loadRulesPage(self):
        if self._rulesLoaded:
            return
        from .phoneticPunctuationGui import RulesDialog
        real = RulesDialog(self.notebook)
        idx = self._getPageIndex(self.rulesPage)
        if idx < 0:
            real.Destroy()
            return
        self.notebook.DeletePage(idx)
        self.notebook.InsertPage(idx, real, _("Earcons & Speech Rules"))
        self._rulesPage = real
        self._rulesLoaded = True
        if self.notebook.GetSelection() != idx:
            self.notebook.SetSelection(idx)

    def _loadQuickJumpPage(self):
        if self._quickJumpLoaded:
            return
        from .browserNavEngine.quickJump import SettingsDialog as QuickJumpSettingsDialog
        real = QuickJumpSettingsDialog(self.notebook)
        idx = self._getPageIndex(self.quickJumpPage)
        if idx < 0:
            real.Destroy()
            return
        self.notebook.DeletePage(idx)
        self.notebook.InsertPage(idx, real, _("QuickSearch & Bookmarks"))
        self._quickJumpPage = real
        self._quickJumpLoaded = True
        if self.notebook.GetSelection() != idx:
            self.notebook.SetSelection(idx)

    def _loadSpeechOrderPage(self):
        if self._speechOrderLoaded:
            return
        self._createRoleGrid()

    def _initSpeechOrderFormats(self):
        conf = config.conf.get("audiothemes", {})
        try:
            roleFormatsJson = conf.get("roleAnnounceFormats", "{}")
            roleFormatsDict = json.loads(roleFormatsJson)
        except Exception as e:
            log.debug(f"Could not load role formats: {e}")
            roleFormatsDict = {}
        for role, label in self._role_list:
            role_key = str(role.value) if hasattr(role, 'value') else str(role)
            saved_fmt = roleFormatsDict.get(role_key, "global")
            self._roleFormats[role] = saved_fmt
        self._populateRoleList()

    def _getPageIndex(self, page):
        for i in range(self.notebook.GetPageCount()):
            if self.notebook.GetPage(i) is page:
                return i
        return -1

    def onSave(self):
        import json
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
        conf["check_for_updates_auto"] = self.autoUpdateCheckbox.IsChecked()
        conf["check_for_updates_prerelease"] = self.prereleaseUpdateCheckbox.IsChecked()
        if hasattr(self, 'blacklisted_roles') and isinstance(self.blacklisted_roles, list) and all(isinstance(r, int) for r in self.blacklisted_roles):
            conf["blacklisted_roles"] = json.dumps(self.blacklisted_roles)
        else:
            conf["blacklisted_roles"] = json.dumps([19])
        conf["audio_ducking_enabled"] = self.audioDuckingCheckbox.IsChecked()
        conf["audio_ducking_volume"] = self.audioDuckingVolumeSlider.GetValue()
        conf["ducking_categories"] = json.dumps(self._ducking_categories)
        if hasattr(self, '_suppress_categories'):
            conf["disabled_apps_suppress_categories"] = json.dumps(self._suppress_categories)

        if self.outputModeChoice.GetSelection() == 1:
            conf["output_mode"] = "mono"
        else:
            conf["output_mode"] = "stereo"

        # Progress bar spatial audio
        conf["progress_pan_mode"] = "screen" if self.progressPanModeChoice.GetSelection() == 1 else "progress"
        conf["progress_pan_range"] = self.progressPanRangeSlider.GetValue()
        conf["progress_pitch_shift"] = self.progressPitchShiftCheckbox.GetValue()

        conf["typing_sounds"] = self.typingSoundsCheckbox.GetValue()
        conf["typing_sounds_edit_only"] = self.typingSoundsEditOnlyCheckbox.GetValue()
        conf["typing_sounds_spatial"] = self.typingSoundsSpatialCheckbox.GetValue()
        conf["typing_sounds_spatial_smart"] = self.typingSoundsSmartSpatialCheckbox.GetValue()
        if self.typingPackCombobox.GetSelection() != wx.NOT_FOUND:
            conf["typing_sound_pack"] = self.typingPackCombobox.GetStringSelection()
        conf["typing_sounds_volume"] = self.typingSoundsVolumeSlider.GetValue()

        # First/Last item fallback
        fl_map = {0: "role", 1: "silence", 2: "first_available", 3: "custom_role"}
        sel = self.firstlastFallbackChoice.GetSelection()
        if sel != wx.NOT_FOUND:
            conf["firstlast_fallback"] = fl_map.get(sel, "role")
        if self.firstRoleChoice.GetSelection() != wx.NOT_FOUND:
            conf["first_fallback_role_name"] = self.fl_names[self.firstRoleChoice.GetSelection()]
        if self.lastRoleChoice.GetSelection() != wx.NOT_FOUND:
            conf["last_fallback_role_name"] = self.fl_names[self.lastRoleChoice.GetSelection()]

        # General fallback
        gf_map = {0: "role", 1: "silence", 2: "first_available", 3: "custom_role"}
        sel = self.generalFallbackChoice.GetSelection()
        if sel != wx.NOT_FOUND:
            conf["general_fallback"] = gf_map.get(sel, "role")
        if self.generalRoleChoice.GetSelection() != wx.NOT_FOUND:
            conf["general_fallback_role_name"] = self.fl_names[self.generalRoleChoice.GetSelection()]

        # State sounds toggle
        conf["state_sounds_suppress_role"] = self.stateSoundsSuppressCheckbox.GetValue()

        # First/Last Item tab
        conf["universal_fl_enabled"] = self.flEnableCheckbox.GetValue()
        fl_mode_map = {0: "smart", 1: "strict", 2: "any_sibling"}
        sel = self.flModeChoice.GetSelection()
        conf["fl_detection_mode"] = fl_mode_map.get(sel, "smart")
        if self.flScopeAll.GetValue():
            conf["fl_enabled_roles"] = "all"
        else:
            enabled_list = getattr(self, '_fl_enabled_roles_list', [])
            if not enabled_list:
                enabled_list = ["listitem", "treeviewitem", "menuitem", "tab"]
            conf["fl_enabled_roles"] = json.dumps(enabled_list)
        solo_map = {0: "first", 1: "last", 2: "none"}
        sel = self.flSoloChoice.GetSelection()
        conf["fl_solo_behavior"] = solo_map.get(sel, "first")

        # System Status tab
        conf["sys_status_enabled"] = self.sysStatusEnableCheckbox.GetValue()
        conf["sys_status_volume"] = self.sysStatusVolumeSlider.GetValue()
        conf["sys_all_usb"] = self.sysAllUsbCheckbox.GetValue()
        conf["sys_ac_enabled"] = self.sysAcEnableCheckbox.GetValue()
        conf["sys_battery_enabled"] = self.sysBatteryEnableCheckbox.GetValue()
        conf["sys_usb_enabled"] = self.sysUsbEnableCheckbox.GetValue()
        conf["sys_volume_enabled"] = self.sysVolumeEnableCheckbox.GetValue()
        conf["sys_network_enabled"] = self.sysNetworkEnableCheckbox.GetValue()
        conf["sys_wake_enabled"] = self.sysWakeEnableCheckbox.GetValue()
        conf["sys_battery_low_threshold"] = self.sysBatteryLowSpin.GetValue()
        conf["sys_battery_critical_threshold"] = self.sysBatteryCriticalSpin.GetValue()
        conf["sys_network_check_interval"] = self.sysNetworkIntervalSpin.GetValue()
        conf["sys_battery_check_interval"] = self.sysBatteryIntervalSpin.GetValue()

        # Emoji tab
        conf["emoji_enabled"] = self.emojiEnableCheckbox.GetValue()
        conf["emoji_sound"] = self.emojiSoundCheckbox.GetValue()
        conf["emoji_prefix"] = self.emojiPrefixCheckbox.GetValue()
        conf["emoji_prefix_text"] = self.emojiPrefixTextCtrl.GetValue()
        pos_map_rev = {0: "before", 1: "after", 2: "both", 3: "none"}
        sel = self.emojiPositionChoice.GetSelection()
        conf["emoji_position"] = pos_map_rev.get(sel, "before")
        rep_map_rev = {0: "per_emoji", 1: "per_block"}
        sel = self.emojiRepeatChoice.GetSelection()
        conf["emoji_repeat"] = rep_map_rev.get(sel, "per_emoji")
        conf["emoji_volume"] = self.emojiVolumeSlider.GetValue()
        for key, cb in self.emojiCatCheckboxes.items():
            conf[key] = cb.GetValue()

        # Speech Order
        if self.announceFormatChoice.GetSelection() != wx.NOT_FOUND:
            conf["announceFormat"] = self.ANNOUNCE_FORMATS[self.announceFormatChoice.GetSelection()][0]
        
        # Per-role formats (only if tab was loaded)
        if hasattr(self, '_roleFormats'):
            roleFormatsDict = {}
            for role, code in self._roleFormats.items():
                if code != "global":
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
        slider_val = self.trimThresholdSlider.GetValue()
        unspoken_conf["TrimSilenceThreshold"] = self._slider_to_threshold(slider_val)
        unspoken_conf["NoiseGate"] = self.noiseGateCheckbox.GetValue()
        unspoken_conf["NoiseGateThreshold"] = self._slider_to_noise_threshold(self.noiseThresholdSlider.GetValue())
        unspoken_conf["NoiseGateAttack"] = self.noiseAttackSlider.GetValue()
        unspoken_conf["NoiseGateRelease"] = self.noiseReleaseSlider.GetValue()
        unspoken_conf["BassBoost"] = self.bassBoostCheckbox.GetValue()
        unspoken_conf["BassBoostGain"] = self.bassGainSlider.GetValue()
        unspoken_conf["BassBoostCutoff"] = self.bassCutoffSlider.GetValue()
        unspoken_conf["Reverb"] = self.enableReverbCheckbox.IsChecked()
        unspoken_conf["RoomSize"] = self.roomSizeSlider.GetValue()
        unspoken_conf["Damping"] = self.dampingSlider.GetValue()
        unspoken_conf["WetLevel"] = self.wetLevelSlider.GetValue()
        unspoken_conf["DryLevel"] = self.dryLevelSlider.GetValue()
        unspoken_conf["Width"] = self.widthSlider.GetValue()
        if self._rulesLoaded and hasattr(self._rulesPage, 'onSave'):
            self._rulesPage.onSave()
        if self._quickJumpLoaded and hasattr(self._quickJumpPage, 'onSave'):
            self._quickJumpPage.onSave()
        # Miscellaneous tab — SentenceNav settings
        from .sentenceNavEngine import setSNConfig, regexCache
        snConf = config.conf["sentencenav"]
        snConf["paragraphChimeVolume"] = self.paragraphChimeVolumeSlider.GetValue()
        snConf["noNextSentenceChimeVolume"] = self.noNextSentenceChimeSlider.GetValue()
        snConf["speakFormatted"] = self.speakFormattedCheckbox.GetValue()
        snConf["enableInWord"] = self.enableInWordCheckbox.GetValue()
        snConf["breakOnWikiReferences"] = self.breakOnWikiReferencesCheckbox.GetValue()
        snConf["breakAtElementBoundaries"] = self.breakAtElementBoundariesCheckbox.GetValue()
        
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
        except Exception as e:
            import logging
            logging.getLogger("audiothemes").error(f"AudioThemes Error: {e}", exc_info=True)
        try:
            setSNConfig("lowerCaseLetters", self.lowerCaseLettersEdit.GetValue(), getattr(self, "snLang", "en"))
        except Exception as e:
            import logging
            logging.getLogger("audiothemes").error(f"AudioThemes Error: {e}", exc_info=True)
        try:
            setSNConfig("exceptionalAbbreviations", self.exceptionalAbbreviationsEdit.GetValue(), getattr(self, "snLang", "en"))
        except Exception as e:
            import logging
            logging.getLogger("audiothemes").error(f"AudioThemes Error: {e}", exc_info=True)
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

        # Miscellaneous tab — Navigation Layer settings
        conf["navLayerPassThrough"] = self.navLayerPassThroughCheckbox.GetValue()
        conf["navLayerTimeout"] = self.navLayerTimeoutCheckbox.GetValue()
        conf["navLayerPlaySounds"] = self.navLayerPlaySoundsCheckbox.GetValue()
        
        checked_indices = self.navLayerModesList.GetCheckedItems()
        enabled_ids = [self.navLayerAllModes[i]["id"] for i in checked_indices]
        conf["navLayerEnabledModes"] = json.dumps(enabled_ids)

        # Audio Formats tab — FFmpeg
        conf["enable_ffmpeg"] = self.ffmpegEnableCheckbox.IsChecked()

    def postSave(self):
        audiotheme_changed.notify()

    def onDiscard(self):
        if self._rulesLoaded and hasattr(self._rulesPage, "onDiscard"):
            self._rulesPage.onDiscard()
        if self._quickJumpLoaded and hasattr(self._quickJumpPage, "onDiscard"):
            self._quickJumpPage.onDiscard()

    def onPreviewTheme(self, event):
        theme = self.selected_theme
        if not theme:
            return
        theme_path = os.path.join(THEMES_DIR, theme.folder)
        # Try to find common sound files to play
        sounds_to_try = [
            "focus.wav", "focus.ogg", "focus.mp3", "focus.flac",
            "select.wav", "select.ogg", "select.mp3", "select.flac",
            "button.wav", "button.ogg", "button.mp3", "button.flac",
            "link.wav", "link.ogg", "link.mp3", "link.flac"
        ]
        
        def play_preview():
            try:
                for snd in sounds_to_try:
                    p = os.path.join(theme_path, snd)
                    if os.path.exists(p):
                        nvwave.playWaveFile(p, asynchronous=True)
                        _time.sleep(0.3)
                        break
            except Exception as e:
                import logging
                logging.getLogger("audiothemes").error(f"AudioThemes Error: {e}", exc_info=True)
        threading.Thread(target=play_preview).start()

    def onAbout(self, event):
        theme_dict = self.selected_theme.todict()
        author_val = theme_dict.get("author", "").strip()
        if not author_val or author_val.lower() == "unknown":
            theme_dict["author"] = _("Unknown")
            
        try:
            import os
            files = [f for f in os.listdir(self.selected_theme.directory) if f.lower().endswith(('.wav', '.ogg', '.mp3'))]
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
            remaining = list(AudioThemesHandler.get_installed_themes())
            if remaining:
                config.conf["audiothemes"]["active_theme"] = remaining[0].folder
            self._maintain_state()

    def onAdd(self, event):
        dlg = wx.Dialog(self, title=_("Add Audio Theme"))
        outer = wx.BoxSizer(wx.VERTICAL)
        
        # Translators: label for ZIP/.atp import button
        zipBtn = wx.Button(dlg, -1, _("Import &ZIP or .atp file..."))
        # Translators: label for folder import button
        folderBtn = wx.Button(dlg, -1, _("Import &folder..."))
        # Translators: label for cancel button
        cancelBtn = wx.Button(dlg, wx.ID_CANCEL, _("&Cancel"))
        
        btnSizer = wx.BoxSizer(wx.VERTICAL)
        btnSizer.Add(zipBtn, 0, wx.EXPAND | wx.ALL, 5)
        btnSizer.Add(folderBtn, 0, wx.EXPAND | wx.ALL, 5)
        btnSizer.Add(cancelBtn, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        outer.Add(btnSizer, 1, wx.EXPAND | wx.ALL, 15)
        dlg.SetSizer(outer)
        dlg.Fit()
        dlg.CentreOnParent()
        
        def onZip(evt):
            fd = wx.FileDialog(
                self,
                # Translators: the title of a file dialog to browse to an audio theme package
                message=_("Choose an audio theme package"),
                # Translators: theme file type description
                wildcard=_("Audio Theme Packages") + " (*.atp;*.zip)|*.atp;*.zip",
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
            )
            if fd.ShowModal() == wx.ID_OK:
                dlg.result = ("zip", fd.GetPath().strip())
            fd.Destroy()
            dlg.EndModal(wx.ID_OK)
        
        def onFolder(evt):
            dd = wx.DirDialog(
                self,
                # Translators: the title of a folder dialog to browse to an audio theme folder
                message=_("Choose a folder containing audio theme files"),
            )
            if dd.ShowModal() == wx.ID_OK:
                dlg.result = ("folder", dd.GetPath().strip())
            dd.Destroy()
            dlg.EndModal(wx.ID_OK)
        
        zipBtn.Bind(wx.EVT_BUTTON, onZip)
        folderBtn.Bind(wx.EVT_BUTTON, onFolder)
        cancelBtn.Bind(wx.EVT_BUTTON, lambda evt: dlg.EndModal(wx.ID_CANCEL))
        
        if dlg.ShowModal() == wx.ID_OK and hasattr(dlg, 'result') and dlg.result:
            action, path = dlg.result
            if action == "zip":
                AudioThemesHandler.install_audio_themePackage(path)
            else:
                AudioThemesHandler.install_audio_themeFolder(path)
            self._maintain_state()
        dlg.Destroy()

    def onThemeSelectionChanged(self, event):
        flag = self.selected_theme is not None
        for btn in (self.aboutThemeButton, self.removeThemeButton):
            btn.Enable(flag)
        # Play a preview sound from the selected theme
        if self.selected_theme is not None:
            self._playThemePreview(self.selected_theme)

    def _playThemePreview(self, theme):
        if getattr(self, '_suppressPreview', False):
            return
        preview_names = ["button.ogg", "button.wav", "button.mp3", "button.flac", "link.ogg", "link.wav", "link.mp3", "link.flac", "checkbox.ogg", "checkbox.wav", "checkbox.mp3", "checkbox.flac"]
        theme_dir = os.path.join(THEMES_DIR, theme.folder)
        for name in preview_names:
            path = os.path.join(theme_dir, name)
            if os.path.exists(path):
                try: nvwave.playWaveFile(path, asynchronous=True)
                except Exception as e:
                    import logging
                    logging.getLogger("audiothemes").error(f"AudioThemes Error: {e}", exc_info=True)
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
                                    except Exception as e:
                                        import logging
                                        logging.getLogger("audiothemes").error(f"AudioThemes Error: {e}", exc_info=True)
                            if "unspoken" in settings_data:
                                for k, v in settings_data["unspoken"].items():
                                    try:
                                        config.conf["unspoken"][k] = v
                                    except Exception as e:
                                        import logging
                                        logging.getLogger("audiothemes").error(f"AudioThemes Error: {e}", exc_info=True)
                            if "phoneticpunctuation" in settings_data:
                                from .utils import phoneticPunctuationConfigKey
                                for k, v in settings_data["phoneticpunctuation"].items():
                                    try:
                                        config.conf[phoneticPunctuationConfigKey][k] = v
                                    except Exception as e:
                                        import logging
                                        logging.getLogger("audiothemes").error(f"AudioThemes Error: {e}", exc_info=True)
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
        prerelease = self.prereleaseUpdateCheckbox.IsChecked()
        check_for_updates(self, prerelease=prerelease)


class DuckingCategoriesDialog(wx.Dialog):
    CATEGORIES = [
        ("theme_sounds", _("Theme sounds (roles, states, focus)")),
        ("typing_sounds", _("Typing sounds")),
        ("earcons", _("Phonetic punctuation earcons (Alt+P)")),
        ("browsernav", _("BrowserNav sounds (indentation, navigation)")),
        ("sentencenav", _("SentenceNav sounds (Alt+Up/Down)")),
        ("textnav", _("TextNav sounds (Alt+Shift+Up/Down)")),
        ("ui_beeps", _("UI feedback beeps (layer, error, beacon)")),
    ]

    def __init__(self, parent):
        title = _("Audio Ducking Categories")
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(panel, -1, _("Select which sound categories should be ducked when NVDA speaks:"))
        sizer.Add(label, 0, wx.ALL, 10)

        self._checkboxes = {}
        conf = config.conf.get("audiothemes", {})
        cat_str = conf.get("ducking_categories", "")
        if cat_str:
            try:
                categories = json.loads(cat_str)
            except Exception:
                categories = dict(_DEFAULT_DUCKING_CATEGORIES)
        else:
            categories = dict(_DEFAULT_DUCKING_CATEGORIES)

        for key, label_text in self.CATEGORIES:
            cb = wx.CheckBox(panel, -1, label_text)
            cb.SetValue(categories.get(key, True))
            self._checkboxes[key] = cb
            sizer.Add(cb, 0, wx.ALL, 5)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        ok_btn = wx.Button(panel, wx.ID_OK)
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        btn_sizer.Add(ok_btn, 0, wx.ALL, 5)
        btn_sizer.Add(cancel_btn, 0, wx.ALL, 5)
        sizer.Add(btn_sizer, 0, wx.ALL | wx.ALIGN_RIGHT, 10)
        panel.SetSizer(sizer)
        self.SetClientSize(panel.GetBestSize())

    def getCategories(self):
        return {key: cb.IsChecked() for key, cb in self._checkboxes.items()}


class SuppressCategoriesDialog(wx.Dialog):
    CATEGORIES = [
        ("theme_sounds", _("Theme sounds (roles, states, focus)")),
        ("typing_sounds", _("Typing sounds")),
        ("earcons", _("Phonetic punctuation earcons (Alt+P)")),
        ("browsernav", _("BrowserNav sounds (indentation, navigation)")),
        ("sentencenav", _("SentenceNav sounds (Alt+Up/Down)")),
        ("textnav", _("TextNav sounds (Alt+Shift+Up/Down)")),
        ("ui_beeps", _("UI feedback beeps (layer, error, beacon)")),
    ]

    def __init__(self, parent):
        title = _("Categories to Suppress in Disabled Apps")
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(panel, -1, _("Select which sound categories to suppress when the foreground app is in the disabled list:"))
        sizer.Add(label, 0, wx.ALL, 10)

        self._checkboxes = {}
        conf = config.conf.get("audiothemes", {})
        cat_str = conf.get("disabled_apps_suppress_categories", "")
        if cat_str:
            try:
                categories = json.loads(cat_str)
            except Exception:
                categories = dict(_DEFAULT_DUCKING_CATEGORIES)
        else:
            categories = dict(_DEFAULT_DUCKING_CATEGORIES)

        for key, label_text in self.CATEGORIES:
            cb = wx.CheckBox(panel, -1, label_text)
            cb.SetValue(categories.get(key, True))
            self._checkboxes[key] = cb
            sizer.Add(cb, 0, wx.ALL, 5)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        ok_btn = wx.Button(panel, wx.ID_OK)
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        btn_sizer.Add(ok_btn, 0, wx.ALL, 5)
        btn_sizer.Add(cancel_btn, 0, wx.ALL, 5)
        sizer.Add(btn_sizer, 0, wx.ALL | wx.ALIGN_RIGHT, 10)
        panel.SetSizer(sizer)
        self.SetClientSize(panel.GetBestSize())

    def getCategories(self):
        return {key: cb.IsChecked() for key, cb in self._checkboxes.items()}
