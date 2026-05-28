# -*- coding: UTF-8 -*-

# Build customizations
# Change this file instead of sconstruct or manifest files, whenever possible.


# Since some strings in "addon_info" are translatable,
# we need to include them in the .po files.
# Gettext recognizes only strings given as parameters to the "_" function.
# To avoid initializing translations in this module we simply roll our own "fake" "_" function
# which returns whatever is given to it as an argument.
def _(arg):
	return arg

# Add-on information variables
addon_info = {
	# add-on Name/identifier, internal for NVDA
	"addon_name": "advanced_audio_themes",
	# Add-on summary, usually the user visible name of the addon.
	# Translators: Summary for this add-on to be shown
	# on installation and add-on information.
	"addon_summary": _("Advanced Audio Themes"),
	# Add-on description
	# Translators: Long description to be shown for this add-on
	# on add-on information from add-ons manager
	"addon_description": _("""Continuing the work on the Audio Themes add-on, with added support for newer NVDA versions.
This add-on creates a virtual audio display that plays sounds when focusing on or navigating between objects.
The add-on also allows you to enable, install, remove, edit, create, and distribute audio theme packages.

Integrated with Earcons and Speech rules add-on:
Allows configuring custom sounds for words, characters, object types, states, and formatting information.

Integrated with SentenceNav add-on for sentence navigation (Alt+Arrows).
Integrated with BrowserNav add-on for advanced browser navigation (NVDA+Alt+Arrows).
"""),
	# version
	"addon_version": "9.3-beta1",
	# Author(s)
	"addon_author": u"Hassan AlBarshoumy, Ahmed Sami, Musharraf Omer, Tony Malykh, Austin Hicks, Bryan Smart",
	# URL for the add-on documentation support
	"addon_url": "https://t.me/HassanAlBarshoumy",
	# URL for the add-on repository where the source code can be found
	"addon_sourceURL": "https://github.com/HassanAlBarshoumy/advanced_audio_themes",
	# Documentation file name
	"addon_docFileName": "readme.html",
	# Minimum NVDA version supported (e.g. "2018.3")
	"addon_minimumNVDAVersion": "2024.1.0",
	# Last NVDA version supported/tested
	# (e.g. "2018.4", ideally more recent than minimum version)
	"addon_lastTestedNVDAVersion": "2026.1.0",
	# Add-on update channel (default is stable or None)
	"addon_updateChannel": "beta",
	# Add-on license such as GPL 2
	"addon_license": "GPL 2",
	# URL for the license document the ad-on is licensed under
	"addon_licenseURL": "https://www.gnu.org/licenses/old-licenses/gpl-2.0.html",
}

# Define the python files that are the sources of your add-on.
# You can use glob expressions here, they will be expanded.
pythonSources = ["globalPlugins/**/*.py", "*.py"]

# Files that contain strings for translation. Usually your python sources
i18nSources = pythonSources

# Files that will be ignored when building the nvda-addon file
# Paths are relative to the addon directory,
# not to the root directory of your addon sources.
excludedFiles = []

# If your add-on is written in a language other than english,
# modify this variable.
# For example:
# set baseLanguage to "es" if your add-on is primarily written in spanish.
baseLanguage = "en"

# Markdown extensions for add-on documentation
# Most add-ons do not require additional Markdown extensions.
# If you need to add support for markup such as tables, fill out the below list.
# Extensions string must be of the form "markdown.extensions.extensionName"
# e.g. "markdown.extensions.tables" to add tables.
markdownExtensions = []
