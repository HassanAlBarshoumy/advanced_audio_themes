import wx
import urllib.request
import json
import threading
import os
import tempfile
import gui
from ..handler import AudioThemesHandler

import addonHandler
try:
    addonHandler.initTranslation()
except AttributeError:
    pass
import config

STORE_URL = "https://raw.githubusercontent.com/HassanAlBarshoumy/AudioThemesStore/main/store.json"

class ThemesStoreDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title=_("Themes Store"), size=(500, 450))
        self.themes_data = []
        self.filtered_themes = []
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        urlSizer = wx.BoxSizer(wx.HORIZONTAL)
        urlLabel = wx.StaticText(self, label=_("Store URL:"))
        self.urlEdit = wx.TextCtrl(self, value=config.conf.get("audiothemes", {}).get("store_url", STORE_URL))
        self.refreshBtn = wx.Button(self, label=_("&Refresh"))
        urlSizer.Add(urlLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        urlSizer.Add(self.urlEdit, 1, wx.EXPAND | wx.ALL, 5)
        urlSizer.Add(self.refreshBtn, 0, wx.ALL, 5)
        sizer.Add(urlSizer, 0, wx.EXPAND | wx.ALL, 10)
        
        searchSizer = wx.BoxSizer(wx.HORIZONTAL)
        searchLabel = wx.StaticText(self, label=_("Search:"))
        self.searchEdit = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        searchSizer.Add(searchLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        searchSizer.Add(self.searchEdit, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(searchSizer, 0, wx.EXPAND | wx.ALL, 10)
        
        self.statusLabel = wx.StaticText(self, label=_("Connecting to store..."))
        sizer.Add(self.statusLabel, 0, wx.ALL, 10)
        
        self.progressBar = wx.Gauge(self, range=100, style=wx.GA_HORIZONTAL)
        sizer.Add(self.progressBar, 0, wx.EXPAND | wx.ALL, 10)
        
        self.themesList = wx.ListBox(self, choices=[])
        sizer.Add(self.themesList, 1, wx.EXPAND | wx.ALL, 10)
        
        self.descText = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        sizer.Add(self.descText, 1, wx.EXPAND | wx.ALL, 10)
        
        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.downloadBtn = wx.Button(self, label=_("&Download & Install"))
        self.downloadBtn.Disable()
        self.previewBtn = wx.Button(self, label=_("&Live Preview"))
        self.previewBtn.Disable()
        self.closeBtn = wx.Button(self, id=wx.ID_CANCEL, label=_("&Close"))
        
        btnSizer.Add(self.downloadBtn, 0, wx.ALL, 5)
        btnSizer.Add(self.previewBtn, 0, wx.ALL, 5)
        btnSizer.Add(self.closeBtn, 0, wx.ALL, 5)
        
        sizer.Add(btnSizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        self.SetSizer(sizer)
        self.Center()
        
        self.Bind(wx.EVT_LISTBOX, self.OnSelectTheme, self.themesList)
        self.Bind(wx.EVT_TEXT, self.OnSearch, self.searchEdit)
        self.Bind(wx.EVT_BUTTON, self.OnDownload, self.downloadBtn)
        self.Bind(wx.EVT_BUTTON, self.OnPreview, self.previewBtn)
        self.Bind(wx.EVT_BUTTON, self.OnRefresh, self.refreshBtn)
        self.Bind(wx.EVT_BUTTON, self.OnClose, self.closeBtn)
        
        # Start fetch
        self.OnRefresh(None)
        
    def OnRefresh(self, event):
        url = self.urlEdit.GetValue().strip()
        if not url: return
        config.conf["audiothemes"]["store_url"] = url
        self.statusLabel.SetLabel(_("Connecting to store..."))
        self.themesList.Clear()
        self.descText.Clear()
        self.downloadBtn.Disable()
        self.previewBtn.Disable()
        threading.Thread(target=self.FetchStoreData, args=(url,), daemon=True).start()

    def FetchStoreData(self, url):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                wx.CallAfter(self.PopulateList, data)
        except Exception as e:
            wx.CallAfter(self.statusLabel.SetLabel, _("Failed to connect to store. Check your internet connection."))
            
    def PopulateList(self, data):
        if isinstance(data, list):
            self.themes_data = data
        else:
            self.themes_data = data.get("themes", [])
        self.filtered_themes = list(self.themes_data)
        self.statusLabel.SetLabel(_("Themes successfully fetched. Select a theme:"))
        self.UpdateThemesList()

    def UpdateThemesList(self):
        self.themesList.Clear()
        for t in self.filtered_themes:
            size_str = f" ({t['size']})" if "size" in t else ""
            self.themesList.Append(t.get("name", "Unknown") + size_str)

    def OnSearch(self, event):
        query = self.searchEdit.GetValue().lower()
        if query:
            self.filtered_themes = [
                t for t in self.themes_data
                if query in t.get("name", "").lower() 
                or query in t.get("author", "").lower() 
                or query in t.get("description", "").lower()
            ]
        else:
            self.filtered_themes = list(self.themes_data)
        self.UpdateThemesList()
        self.descText.Clear()
        self.downloadBtn.Disable()
        self.previewBtn.Disable()
            
    def OnSelectTheme(self, event):
        idx = self.themesList.GetSelection()
        if idx != wx.NOT_FOUND:
            t = self.filtered_themes[idx]
            desc = f"Author: {t.get('author', 'Unknown')}\n\n{t.get('description', '')}"
            self.descText.SetValue(desc)
            self.downloadBtn.Enable()
            self.previewBtn.Enable()
            
    def OnDownload(self, event):
        idx = self.themesList.GetSelection()
        if idx == wx.NOT_FOUND: return
        t = self.filtered_themes[idx]
        url = t.get("url")
        if not url: return
        
        self.downloadBtn.Disable()
        self.statusLabel.SetLabel(_("Downloading... Please wait"))
        pkg_type = t.get("type", "theme")
        threading.Thread(target=self.DownloadAndInstall, args=(url, pkg_type), daemon=True).start()
        
    def DownloadAndInstall(self, url, pkg_type):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as response:
                total_size = response.info().get('Content-Length')
                total_size = int(total_size) if total_size else 0
                downloaded = 0
                pack_data = bytearray()
                
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    pack_data.extend(chunk)
                    downloaded += len(chunk)
                    if total_size:
                        percent = int((downloaded / total_size) * 100)
                        wx.CallAfter(self.progressBar.SetValue, percent)
                        wx.CallAfter(self.statusLabel.SetLabel, _("Downloading... {}%").format(percent))
                        
            wx.CallAfter(self.progressBar.SetValue, 0)
            fd, tmp_path = tempfile.mkstemp(suffix=".zip")
            with os.fdopen(fd, 'wb') as f:
                f.write(pack_data)
                
            wx.CallAfter(self.InstallFinished, tmp_path, pkg_type)
        except Exception as e:
            wx.CallAfter(self.statusLabel.SetLabel, _("Download failed."))
            wx.CallAfter(self.downloadBtn.Enable)
            
    def InstallFinished(self, tmp_path, pkg_type):
        try:
            if pkg_type == "typing_pack":
                AudioThemesHandler.install_typing_soundPackage(tmp_path)
                self.statusLabel.SetLabel(_("Typing pack installation successful!"))
                wx.MessageBox(_("Typing sound pack successfully installed."), _("Success"), wx.ICON_INFORMATION)
            else:
                AudioThemesHandler.install_audio_themePackage(tmp_path)
                self.statusLabel.SetLabel(_("Installation successful!"))
                wx.MessageBox(_("Audio theme successfully installed. You can now select it from the themes menu."), _("Success"), wx.ICON_INFORMATION)
        except Exception as e:
            self.statusLabel.SetLabel(_("Error during installation."))
        finally:
            self.downloadBtn.Enable()
            try:
                os.remove(tmp_path)
            except Exception as e:
                import logging
                logging.getLogger("audiothemes").error(f"AudioThemes Error: {e}", exc_info=True)
    def OnPreview(self, event):
        idx = self.themesList.GetSelection()
        if idx == wx.NOT_FOUND: return
        t = self.filtered_themes[idx]
        url = t.get("url")
        preview_url = t.get("preview_url")
        if not url and not preview_url: return
        
        self.previewBtn.Disable()
        self.statusLabel.SetLabel(_("Downloading audio preview..."))
        threading.Thread(target=self.DownloadAndPreview, args=(url, preview_url), daemon=True).start()

    def DownloadAndPreview(self, url, preview_url):
        try:
            import nvwave
            import urllib.request
            
            if preview_url:
                req = urllib.request.Request(preview_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    audio_data = response.read()
                ext = os.path.splitext(preview_url)[1] or ".wav"
                fd, tmp_path = tempfile.mkstemp(suffix=ext)
                with os.fdopen(fd, 'wb') as f:
                    f.write(audio_data)
                
                try:
                    nvwave.playWaveFile(tmp_path, asynchronous=True)
                    import threading
                    threading.Timer(5.0, lambda: os.remove(tmp_path) if os.path.exists(tmp_path) else None).start()
                except Exception:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                wx.CallAfter(self.statusLabel.SetLabel, _("Preview finished."))
                wx.CallAfter(self.previewBtn.Enable)
                return

            import zipfile
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as response:
                total_size = response.info().get('Content-Length')
                total_size = int(total_size) if total_size else 0
                downloaded = 0
                pack_data = bytearray()
                
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    pack_data.extend(chunk)
                    downloaded += len(chunk)
                    if total_size:
                        percent = int((downloaded / total_size) * 100)
                        wx.CallAfter(self.progressBar.SetValue, percent)
                        wx.CallAfter(self.statusLabel.SetLabel, _("Downloading preview... {}%").format(percent))
            
            wx.CallAfter(self.progressBar.SetValue, 0)
            fd, tmp_path = tempfile.mkstemp(suffix=".atp")
            with os.fdopen(fd, 'wb') as f:
                f.write(pack_data)
                
            with zipfile.ZipFile(tmp_path, "r") as z:
                wav_files = [n for n in z.namelist() if n.lower().endswith('.wav') or n.lower().endswith('.ogg') or n.lower().endswith('.mp3')]
                if wav_files:
                    import random
                    # Prioritize button or window sounds for preview
                    prioritized = [n for n in wav_files if "button" in n.lower() or "window" in n.lower()]
                    preview_file = random.choice(prioritized) if prioritized else random.choice(wav_files)
                    
                    extracted_path = z.extract(preview_file, tempfile.gettempdir())
                    try:
                        nvwave.playWaveFile(extracted_path, asynchronous=True)
                        # Remove the file after a short delay since asynchronous play might still need it
                        import threading
                        threading.Timer(5.0, lambda: os.remove(extracted_path) if os.path.exists(extracted_path) else None).start()
                    except Exception:
                        if os.path.exists(extracted_path):
                            os.remove(extracted_path)
                        
            wx.CallAfter(self.statusLabel.SetLabel, _("Preview finished."))
        except Exception as e:
            wx.CallAfter(self.statusLabel.SetLabel, _("Audio preview failed."))
        finally:
            wx.CallAfter(self.previewBtn.Enable)
            try:
                os.remove(tmp_path)
            except Exception as e:
                import logging
                logging.getLogger("audiothemes").error(f"AudioThemes Error: {e}", exc_info=True)
    def OnClose(self, event):
        self.Destroy()
