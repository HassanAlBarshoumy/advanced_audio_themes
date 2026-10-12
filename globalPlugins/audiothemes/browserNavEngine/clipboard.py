#A part of the BrowserNav addon for NVDA
#Copyright (C) 2017-2022 Tony Malykh
#This file is covered by the GNU General Public License.
#See the file LICENSE  for more details.

import ctypes
import gui
import winUser
import wx

def ephemeralCopyToClip(text: str):
    """
    Copies string to clipboard without leaving an entry in clipboard history.
    """
    with winUser.openClipboard(gui.mainFrame.Handle):
        winUser.emptyClipboard()
        winUser.setClipboardData(winUser.CF_UNICODETEXT, text)
        ephemeralFormat = ctypes.windll.user32.RegisterClipboardFormatW("ExcludeClipboardContentFromMonitorProcessing")
        ctypes.windll.user32.SetClipboardData(ephemeralFormat,None)

TEXT_FORMAT = "Text"
def deleteEntryFromClipboardHistory(textToDelete, maxEntries=10):
    from .pywinsdk.relative.winsdk.windows.applicationmodel.datatransfer import Clipboard
    from .pywinsdk.relative.winsdk.windows.foundation import AsyncStatus
    
    def dummyAwait(result):
        while result.status == AsyncStatus.STARTED:
            wx.Yield()
        if result.status == AsyncStatus.COMPLETED:
            return result
        raise RuntimeError(f"Bad async status {result.status}")

    history = dummyAwait(Clipboard.get_history_items_async())
    items = history.get_results()
    itemTuples = []    
    result = False
    for i in range(maxEntries):
        try:
            item = items.items[i]
        except OSError:
            continue
        content = item.content
        avf = content.available_formats
        avf2 = [avf.get_at(j) for j in range(avf.size)]
        if TEXT_FORMAT not in avf2:
            continue
        itemTuples.append((item,content.get_text_async()))
    for item, text in itemTuples:
        text = dummyAwait(text)
        value = text.get_results()
        if value == textToDelete:
            r = Clipboard.delete_item_from_history(item)
            result = result or r
    return result
