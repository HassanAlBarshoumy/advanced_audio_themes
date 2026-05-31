import wx
import json
import os
import ssl
import tempfile
import threading
import addonHandler
import config
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
LATEST_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
LIST_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases"

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


def _fetch_json(url):
    ctx = ssl.create_default_context()
    req = Request(url, headers={"User-Agent": "advanced_audio_themes"})
    resp = urlopen(req, timeout=10, context=ctx)
    return json.loads(resp.read().decode("utf-8"))


def _find_asset(data):
    assets = data.get("assets", [])
    for asset in assets:
        name = asset.get("name", "")
        if name.endswith(".nvda-addon"):
            return asset.get("browser_download_url")
    return None


def get_latest_release(prerelease=False):
    try:
        if not prerelease:
            data = _fetch_json(LATEST_API)
            tag = data.get("tag_name", "")
            return tag, _find_asset(data), data.get("html_url", "")
        releases = _fetch_json(LIST_API)
        best = None
        for rel in releases:
            if rel.get("draft", False):
                continue
            tag = rel.get("tag_name", "")
            url = _find_asset(rel)
            if not url:
                continue
            published = rel.get("published_at", "")
            best = (tag, url, published, rel.get("html_url", ""))
        if best:
            return best[0], best[1], best[3]
        return None, None, None
    except (URLError, json.JSONDecodeError, OSError):
        return None, None, None


def get_latest_version_info(prerelease=False):
    tag, download_url, html_url = get_latest_release(prerelease)
    if tag:
        return tag, parse_version(tag), download_url, html_url
    return None, None, None, None


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


def check_for_updates(parent=None, prerelease=False):
    if parent is None:
        parent = wx.GetActiveWindow()

    def _check_thread():
        tag, download_url, html_url = get_latest_release(prerelease)
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

    import ui
    ui.message(_("Checking for updates..."))
    threading.Thread(target=_check_thread, daemon=True).start()


def check_for_updates_auto():
    try:
        conf = config.conf["audiothemes"]
        if not conf.get("check_for_updates_auto", True):
            return
        prerelease = conf.get("check_for_updates_prerelease", False)
    except Exception:
        return

    def _check_thread():
        try:
            tag, download_url, html_url = get_latest_release(prerelease)
            if tag is None:
                return
            latest = parse_version(tag)
            current = parse_version(CURRENT_VERSION)
            if latest <= current:
                return
            wx.CallAfter(_notify, tag, download_url, html_url)
        except Exception:
            pass

    def _notify(tag, download_url, html_url):
        result = wx.MessageBox(
            _("A new version is available: {tag}\n\nCurrent version: {current}\n\nWould you like to download and install the update?").format(tag=tag, current=CURRENT_VERSION),
            _("Update Available"),
            style=wx.YES_NO | wx.ICON_QUESTION
        )
        if result == wx.YES and download_url:
            def on_download(success, path, error):
                if success and path:
                    os.startfile(path)
            download_addon(download_url, on_download)

    threading.Thread(target=_check_thread, daemon=True).start()
