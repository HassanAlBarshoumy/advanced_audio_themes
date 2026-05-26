import wx
import json
import os
import ssl
import tempfile
import threading
import addonHandler
from urllib.request import urlopen, Request
from urllib.error import URLError

try:
    addonHandler.initTranslation()
except Exception:
    pass
try:
    _
except NameError:
    def _(msg):
        return msg

GITHUB_REPO = "HassanAlBarshoumy/advanced_audio_themes"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

CURRENT_VERSION = None
for addon in addonHandler.getAvailableAddons():
    if addon.name == "advanced_audio_themes":
        CURRENT_VERSION = addon.version
        break
if CURRENT_VERSION is None:
    CURRENT_VERSION = "9.0.0"


def parse_version(v):
    try:
        parts = v.lstrip("v").split(".")
        return tuple(int(p) for p in parts)
    except (ValueError, AttributeError):
        return (0, 0, 0)


def get_latest_release():
    try:
        ctx = ssl.create_default_context()
        req = Request(RELEASES_API, headers={"User-Agent": "advanced_audio_themes"})
        resp = urlopen(req, timeout=10, context=ctx)
        data = json.loads(resp.read().decode("utf-8"))
        tag = data.get("tag_name", "")
        assets = data.get("assets", [])
        download_url = None
        for asset in assets:
            name = asset.get("name", "")
            if name.endswith(".nvda-addon"):
                download_url = asset.get("browser_download_url")
                break
        return tag, download_url, data.get("html_url", "")
    except (URLError, json.JSONDecodeError, OSError) as e:
        return None, None, None


def download_addon(url, callback):
    def _download():
        try:
            ctx = ssl.create_default_context()
            req = Request(url, headers={"User-Agent": "advanced_audio_themes"})
            resp = urlopen(req, timeout=60, context=ctx)
            ext = os.path.splitext(url.split("/")[-1])[1] or ".nvda-addon"
            fd, path = tempfile.mkstemp(suffix=ext, prefix="audiothemes_update_")
            with os.fdopen(fd, "wb") as f:
                f.write(resp.read())
            wx.CallAfter(callback, True, path, None)
        except Exception as e:
            wx.CallAfter(callback, False, None, str(e))
    threading.Thread(target=_download, daemon=True).start()


def check_for_updates(parent=None):
    if parent is None:
        parent = wx.GetActiveWindow()
    import ui
    ui.message(_("Checking for updates..."))

    def _check_thread():
        tag, download_url, _html_url = get_latest_release()
        wx.CallAfter(_on_result, tag, download_url)

    def _on_result(tag, download_url):
        if tag is None:
            wx.MessageBox(
                _("Could not check for updates. Please check your internet connection."),
                _("Update Check"),
                style=wx.ICON_ERROR
            )
            return

        latest = parse_version(tag)
        current = parse_version(CURRENT_VERSION)

        if latest <= current:
            wx.MessageBox(
                _("You are already running the latest version ({version}).").format(version=CURRENT_VERSION),
                _("Update Check"),
                style=wx.ICON_INFORMATION
            )
            return

        result = wx.MessageBox(
            _("A new version is available: {tag}\n\nCurrent version: {current}\n\nWould you like to download and install the update?").format(tag=tag, current=CURRENT_VERSION),
            _("Update Available"),
            style=wx.YES_NO | wx.ICON_QUESTION
        )

        if result == wx.YES and download_url:
            def on_download(success, path, error):
                if success and path:
                    wx.MessageBox(
                        _("Download complete. The add-on installation dialog will now open."),
                        _("Update Check"),
                        style=wx.ICON_INFORMATION
                    )
                    os.startfile(path)
                else:
                    wx.MessageBox(
                        _("Failed to download the update: {error}").format(error=error or _("Unknown error")),
                        _("Update Error"),
                        style=wx.ICON_ERROR
                    )
            download_addon(download_url, on_download)

    threading.Thread(target=_check_thread, daemon=True).start()
