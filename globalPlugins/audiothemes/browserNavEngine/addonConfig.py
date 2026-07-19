#A part of the BrowserNav addon for NVDA
#Copyright (C) 2017-2021 Tony Malykh
#This file is covered by the GNU General Public License.
#See the file LICENSE  for more details.

import config

_bne_cached_config = {}
def refreshBNEConfigCache():
    global _bne_cached_config
    try:
        src = config.conf["browsernav"]
        _bne_cached_config = {k: src[k] for k in src}
    except Exception:
        _bne_cached_config = {}

def getConfig(key):
    val = _bne_cached_config.get(key)
    if val is not None:
        return val
    val = config.conf["browsernav"][key]
    _bne_cached_config[key] = val
    return val

def setConfig(key, value):
    config.conf["browsernav"][key] = value
    _bne_cached_config[key] = value
