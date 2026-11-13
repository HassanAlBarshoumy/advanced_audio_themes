import wx
import hashlib
import json
import os
import re
import ssl
import tempfile
import threading
import addonHandler
import config
from urllib.request import urlopen, Request
from urllib.error import URLError
from logHandler import log

try:
    addonHandler.initTranslation()
except Exception:
    log.debug("AudioThemes: swallowed Exception in update_checker")
try:
    _
except NameError:
    def _(msg):
        return msg

GITHUB_REPO = "HassanAlBarshoumy/advanced_audio_themes"
LATEST_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
LIST_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases"

# A downloaded package is only ever opened when its SHA-256 matches the
# checksum published next to it.  Older releases had no checksum asset: in that
# case the download is allowed to proceed with a warning in the log, so an
# update from an old release is never blocked outright.
CHECKSUM_SUFFIX = ".sha256"
MAX_DOWNLOAD_BYTES = 64 * 1024 * 1024
_SHA256_RE = re.compile(r"\b([0-9a-fA-F]{64})\b")
_MANIFEST_VERSION_RE = re.compile(r"(?m)^\s*version\s*=\s*([^\r\n#;]+)")

CURRENT_VERSION = None
for addon in addonHandler.getAvailableAddons():
    if addon.name == "advanced_audio_themes":
        CURRENT_VERSION = addon.version
        break


def _read_manifest_version():
    """Return the version from the shipped manifest.ini, or None.

    ``addonHandler`` is the authoritative source, but when the add-on metadata
    cannot be read (for example a development checkout) the manifest next to
    this package still gives the exact installed version.  Returning None is
    intentional: an unknown current version must suppress the comparison
    instead of silently pretending the installed version is 0.
    """
    try:
        addon_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        with open(os.path.join(addon_root, "manifest.ini"), "r", encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError):
        return None
    match = _MANIFEST_VERSION_RE.search(text)
    if match is None:
        return None
    version = match.group(1).strip().strip("\"'")
    return version or None


if CURRENT_VERSION is None:
    CURRENT_VERSION = _read_manifest_version()


def parse_version(v):
    try:
        parts = v.lstrip("v").split(".")
        result = []
        saw_digit = False
        for part in parts:
            digits = ""
            for ch in part:
                if ch.isdigit():
                    digits += ch
                else:
                    break
            if digits:
                saw_digit = True
            result.append(int(digits) if digits else 0)
        if not saw_digit:
            return (0, 0, 0)
        return tuple(result)
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


def _find_checksum_asset(data):
    assets = data.get("assets", [])
    for asset in assets:
        name = asset.get("name", "")
        if name.endswith(".nvda-addon" + CHECKSUM_SUFFIX):
            return asset.get("browser_download_url")
    return None


def _parse_checksum(text):
    """Return the lower-case SHA-256 digest contained in ``text`` or None.

    Accepts the output of ``sha256sum`` (``<digest>  <filename>``) as well as a
    bare digest, which is what the release workflow produces.
    """
    if not text or not isinstance(text, str):
        return None
    match = _SHA256_RE.search(text)
    if match is None:
        return None
    return match.group(1).lower()


def _sha256_of_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fetch_text(url):
    ctx = ssl.create_default_context()
    req = Request(url, headers={"User-Agent": "advanced_audio_themes"})
    resp = urlopen(req, timeout=15, context=ctx)
    return resp.read(4096).decode("utf-8", "replace")


def get_latest_release(prerelease=False):
    """Return ``(tag, download_url, html_url, checksum_url)`` for the release.

    ``checksum_url`` may be None for releases published before checksums were
    attached; the download path then warns instead of refusing the update.
    """
    try:
        if not prerelease:
            data = _fetch_json(LATEST_API)
            tag = data.get("tag_name", "")
            return (
                tag,
                _find_asset(data),
                data.get("html_url", ""),
                _find_checksum_asset(data),
            )
        releases = _fetch_json(LIST_API)
        best = None
        best_published = ""
        for rel in releases:
            if rel.get("draft", False):
                continue
            tag = rel.get("tag_name", "")
            url = _find_asset(rel)
            if not url:
                continue
            published = rel.get("published_at") or rel.get("created_at") or ""
            if best is None or published > best_published:
                best = (tag, url, published, rel.get("html_url", ""), _find_checksum_asset(rel))
                best_published = published
        if best:
            return best[0], best[1], best[3], best[4]
        return None, None, None, None
    except (URLError, json.JSONDecodeError, OSError):
        return None, None, None, None





def download_addon(url, callback, parent=None, checksum_url=None, expected_sha256=None):
    progress_dlg = [None]

    def _show_progress():
        dlg = wx.ProgressDialog(
            _("Downloading Update"),
            _("Downloading the latest version..."),
            parent=parent,
            style=wx.PD_APP_MODAL
        )
        dlg.Show()
        progress_dlg[0] = dlg

    def _pulse_progress():
        dlg = progress_dlg[0]
        if dlg:
            dlg.Pulse()

    def _close_progress():
        dlg = progress_dlg[0]
        if dlg:
            dlg.Destroy()
            progress_dlg[0] = None

    def _download():
        path = None
        try:
            resolved_checksum = expected_sha256
            if resolved_checksum is None and checksum_url:
                resolved_checksum = _parse_checksum(_fetch_text(checksum_url))
                if resolved_checksum is None:
                    raise ValueError(
                        _("The published checksum could not be read.")
                    )
            ctx = ssl.create_default_context()
            req = Request(url, headers={"User-Agent": "advanced_audio_themes"})
            resp = urlopen(req, timeout=60, context=ctx)
            ext = os.path.splitext(url.split("/")[-1])[1] or ".nvda-addon"
            fd, path = tempfile.mkstemp(suffix=ext, prefix="audiothemes_update_")
            wx.CallAfter(_show_progress)
            total = 0
            with os.fdopen(fd, "wb") as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_DOWNLOAD_BYTES:
                        raise ValueError("downloaded file is larger than the allowed size")
                    f.write(chunk)
                    wx.CallAfter(_pulse_progress)
            if resolved_checksum:
                actual = _sha256_of_file(path)
                if actual != resolved_checksum:
                    raise ValueError(
                        _("The downloaded file failed its integrity check.")
                    )
            else:
                log.warning(
                    "AudioThemes: the release publishes no checksum; "
                    "the downloaded update could not be verified"
                )
            wx.CallAfter(_close_progress)
            wx.CallAfter(callback, True, path, None)
        except Exception as e:
            if path is not None:
                try:
                    os.unlink(path)
                except Exception:
                    log.debug("AudioThemes: swallowed Exception in update_checker._download")
            wx.CallAfter(_close_progress)
            wx.CallAfter(callback, False, None, str(e))
    threading.Thread(target=_download, daemon=True).start()


def check_for_updates(parent=None, prerelease=False):
    if parent is None:
        parent = wx.GetActiveWindow()

    def _check_thread():
        tag, download_url, html_url, checksum_url = get_latest_release(prerelease)
        wx.CallAfter(_on_result, tag, download_url, checksum_url)

    def _on_result(tag, download_url, checksum_url):
        if tag is None:
            wx.MessageBox(
                _("Could not check for updates. Please check your internet connection."),
                _("Update Check"),
                style=wx.ICON_ERROR
            )
            return

        if CURRENT_VERSION is None:
            wx.MessageBox(
                _("The installed version could not be determined.\nThe latest published version is {tag}.").format(tag=tag),
                _("Update Check"),
                style=wx.ICON_INFORMATION
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
                    try:
                        os.startfile(path)
                    except Exception as e:
                        wx.MessageBox(
                            _("Failed to open the update file: {error}").format(error=str(e)),
                            _("Update Error"),
                            style=wx.ICON_ERROR
                        )
                else:
                    wx.MessageBox(
                        _("Failed to download the update: {error}").format(error=error or _("Unknown error")),
                        _("Update Error"),
                        style=wx.ICON_ERROR
                    )
            download_addon(download_url, on_download, checksum_url=checksum_url)

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
            tag, download_url, html_url, checksum_url = get_latest_release(prerelease)
            if tag is None:
                return
            if CURRENT_VERSION is None:
                return
            latest = parse_version(tag)
            current = parse_version(CURRENT_VERSION)
            if latest <= current:
                return
            wx.CallAfter(_notify, tag, download_url, html_url, checksum_url)
        except Exception:
            log.debug("AudioThemes: swallowed Exception in update_checker._check_thread")

    def _notify(tag, download_url, html_url, checksum_url):
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
                    try:
                        os.startfile(path)
                    except Exception as e:
                        wx.MessageBox(
                            _("Failed to open the update file: {error}").format(error=str(e)),
                            _("Update Error"),
                            style=wx.ICON_ERROR
                        )
                else:
                    wx.MessageBox(
                        _("Failed to download the update: {error}").format(error=error or _("Unknown error")),
                        _("Update Error"),
                        style=wx.ICON_ERROR
                    )
            download_addon(download_url, on_download, checksum_url=checksum_url)

    threading.Thread(target=_check_thread, daemon=True).start()
