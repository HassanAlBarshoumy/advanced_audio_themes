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
	"addon_description": _("""استكمال العمل على إضافة سمات الصوت (Audio Themes)، مع إضافة دعم للإصدارات الأحدث من NVDA.
تقوم هذه الإضافة بإنشاء عرض صوتي افتراضي يشغل أصواتاً عند التركيز أو التنقل بين العناصر.
كما تتيح لك الإضافة تفعيل، تثبيت، إزالة، تحرير، إنشاء، وتوزيع حزم السمات الصوتية.

تم دمجها مع إضافة Earcons and Speech rules:
تسمح بإعداد أصوات مخصصة للكلمات، الأحرف، أنواع العناصر، الحالات، ومعلومات التنسيق.

تم دمج إضافة SentenceNav للتنقل بالجمل (Alt+أسهم).
تم دمج إضافة BrowserNav للتنقل المتقدم في المتصفح (NVDA+Alt+أسهم).
"""),
	# version
	"addon_version": "9.0.0",
	# Author(s)
	"addon_author": u"Hassan AlBarshoumy, Musharraf Omer, Tony Malykh, Austin Hicks, Bryan Smart, Ahmed Sami",
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
	"addon_updateChannel": None,
	# Add-on license such as GPL 2
	"addon_license": None,
	# URL for the license document the ad-on is licensed under
	"addon_licenseURL": None,
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
