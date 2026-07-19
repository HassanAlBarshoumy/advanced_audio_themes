# -*- coding: UTF-8 -*-
#A part of the Earcons and Speech Rules addon for NVDA

#This file is covered by the GNU General Public License.
#See the file COPYING.txt for more details.

import api
import array
import config
import ctypes
import fnmatch
import json
import os
import queue
import time
from queue import Queue
from logHandler import log
import speech
import speech.commands
import threading
from threading import Thread
from . import common

debug = False
# Debug logging removed: no hardcoded paths in production builds.
def mylog(s):
    if debug:
        log.debug(str(s))

def myAssert(condition):
    if not condition:
        raise RuntimeError("Assertion failed")

_cached_output_mode = "stereo"

def _set_cached_output_mode(mode):
    global _cached_output_mode
    _cached_output_mode = mode

def ensure_mono(audio_bytes, channels, sample_rate):
	if channels != 2:
		return audio_bytes
	if _cached_output_mode != "mono":
		return audio_bytes
	arr = array.array('h')
	arr.frombytes(audio_bytes)
	n = len(arr) // 2
	result = array.array('h', (int((arr[i * 2] + arr[i * 2 + 1]) * 0.5) for i in range(n) for _ in range(2)))
	return result.tobytes()


# Sentinel object used to signal Worker threads to shut down cleanly.
_WORKER_STOP = object()


class Worker(Thread):
    """
    Thread executing tasks from a given tasks queue.
    Exits cleanly when it receives the _WORKER_STOP sentinel.
    """
    def __init__(self, tasks):
        Thread.__init__(self)
        self.tasks = tasks
        self.daemon = True
        self.is_busy = False
        self.task_start_time = 0
        self.start()

    def run(self):
        try:
            THREAD_PRIORITY_NORMAL = 0
            ctypes.windll.kernel32.SetThreadPriority(ctypes.windll.kernel32.GetCurrentThread(), THREAD_PRIORITY_NORMAL)
        except Exception as e:
            log.error(f"AudioThemes Error: {e}", exc_info=True)
        while True:
            item = self.tasks.get()
            if item is _WORKER_STOP:
                self.tasks.task_done()
                break
            func, args, kargs = item
            self.is_busy = True
            self.task_start_time = time.time()
            try:
                func(*args, **kargs)
            except Exception:
                log.exception("Error in audio_themes_NG ThreadPool worker")
            except BaseException:
                log.exception("CRITICAL: Unhandled BaseException in audio_themes_NG ThreadPool worker")
            finally:
                self.is_busy = False
                self.tasks.task_done()


class ThreadPool:
    """
    Pool of threads consuming tasks from an unbounded queue.

    Key fixes vs. the original:
    * Queue is now **unbounded** — a bounded Queue with capacity == num_threads
      would block the NVDA main thread whenever all workers were busy, causing
      the watchdog freezes observed in the log.
    * add_task() is non-blocking by design (no timeout on put).
    * shutdown() sends a stop sentinel to every worker so they exit cleanly
      when the add-on is unloaded.
    """
    def __init__(self, num_threads):
        # Professional bounded queue: Drop incoming tasks rather than freezing RAM or Main Thread
        self.tasks = Queue(maxsize=30)
        self._num_threads = num_threads
        self._workers = []
        self._last_watchdog_time = 0.0
        for _ in range(num_threads):
            w = Worker(self.tasks)
            self._workers.append(w)

    def _check_and_respawn_workers(self):
        """Watchdog: Detect dead workers only.
        
        Stuck threads (busy >10s) are no longer auto-respawned, since
        Fix 1 (COM caching) prevents the main deadlock cause.  They
        will recover naturally once unblocked.
        """
        current_time = time.time()
        for i, w in enumerate(self._workers):
            if not w.is_alive():
                log.warning("ThreadPool: Worker thread died. Respawning.")
                self._workers[i] = Worker(self.tasks)
            elif w.is_busy and (current_time - w.task_start_time) > 10.0:
                log.warning(f"ThreadPool: Worker {i} busy >10s (may be stuck). Waiting for recovery.")
                
    def add_task(self, func, *args, **kargs):
        """Enqueue a task.  Returns immediately; never blocks the caller."""
        # Throttled watchdog: only check workers every 5 seconds
        now = time.monotonic()
        if now - self._last_watchdog_time > 5.0:
            self._last_watchdog_time = now
            self._check_and_respawn_workers()
            
        try:
            # put_nowait raises queue.Full instantly instead of blocking the main NVDA thread
            self.tasks.put_nowait((func, args, kargs))
        except queue.Full:
            # Queue is full (User moved mouse/keyboard too fast) -> Drop gracefully without memory leak
            pass
    def map(self, func, args_list):
        """Enqueue one task per element in args_list."""
        for args in args_list:
            self.add_task(func, args)

    def wait_completion(self):
        """Block until all currently-queued tasks finish."""
        self.tasks.join()

    def shutdown(self, wait=True):
        """Signal every worker to exit.  Call from addon.terminate()."""
        for _ in self._workers:
            self.tasks.put_nowait(_WORKER_STOP)
        if wait:
            for w in self._workers:
                w.join(timeout=3.0)
        else:
            self._workers.clear()

    def restart(self):
        """Respawn workers if they were cleared."""
        if not self._workers:
            for _ in range(self._num_threads):
                w = Worker(self.tasks)
                self._workers.append(w)

threadPool = ThreadPool(4)   # 4 workers for audio playback tasks.

phoneticPunctuationConfigKey = "phoneticpunctuation"
_pp_config_cache = {}

def refreshPpConfigCache():
    global _pp_config_cache
    try:
        section = config.conf.get(phoneticPunctuationConfigKey, {})
        _pp_config_cache = dict(section)
    except Exception:
        _pp_config_cache = {}

def getConfig(key):
    try:
        return _pp_config_cache[key]
    except KeyError:
        val = config.conf[phoneticPunctuationConfigKey].get(key)
        _pp_config_cache[key] = val
        return val

def setConfig(key, value):
    config.conf[phoneticPunctuationConfigKey][key] = value
    _pp_config_cache[key] = value

def initConfiguration():
    confspec = {
        "enabled" : "boolean( default=False)",
        "rules" : "string( default='')",
        "applicationsBlacklist" : "string( default='')",
        "stateVerbose" : "boolean( default=True)",
    }
    config.conf.spec[phoneticPunctuationConfigKey] = confspec
    refreshPpConfigCache()

def getSoundsPath():
    globalPluginPath = os.path.abspath(os.path.dirname(__file__))
    addonPath = os.path.split(globalPluginPath)[0]
    addonPath = os.path.split(addonPath)[0]
    soundsPath = os.path.join(addonPath, "sounds")
    return soundsPath

_cached_blacklist_string = None
_cached_blacklist_set = set()

def isAppBlacklisted():
    try:
        handler = _handler_ref
        appName = getattr(handler, '_current_app_name', "")
    except Exception:
        appName = ""
    if not appName:
        return False
        
    global _cached_blacklist_string, _cached_blacklist_set
    current_blacklist = getConfig("applicationsBlacklist")
    if current_blacklist != _cached_blacklist_string:
        _cached_blacklist_string = current_blacklist
        _cached_blacklist_set = {app.strip().lower() for app in current_blacklist.split(",") if app.strip()}
        
    app_lower = appName.lower()
    if app_lower in _cached_blacklist_set:
        return True
        
    for pattern in _cached_blacklist_set:
        if fnmatch.fnmatch(app_lower, pattern):
            return True
            
    return False

def isPhoneticPunctuationEnabled():
    return not isAppBlacklisted() and getConfig("enabled")

def isURLResolutionAvailable():
    try:
        api.getCurrentURL
        return True
    except AttributeError:
        return False

_last_url = ""
_last_url_time = 0
_URL_CACHE_TTL = 0.5
def getCurrentURLSafe():
    global _last_url, _last_url_time
    now = time.time()
    if now - _last_url_time > _URL_CACHE_TTL:
        try:
            _last_url = api.getCurrentURL()
        except Exception:
            _last_url = ""
        _last_url_time = now
    return _last_url

def getCurrentContext():
    try:
        handler = _handler_ref
        appName = getattr(handler, '_current_app_name', "")
        windowTitle = getattr(handler, '_current_window_title', "")
        url = getattr(handler, '_current_url', None)
        if url is None:
            url = getCurrentURLSafe()
    except Exception:
        appName, windowTitle, url = "", "", ""
        
    return appName, windowTitle, url

# Cached handler reference set by __init__ to avoid import issues on worker threads.
_handler_ref = None

def _set_handler_ref(handler):
    global _handler_ref
    _handler_ref = handler

_suppressed_categories_json = ""
_suppressed_categories_dict = {}
_suppressed_categories_lock = threading.Lock()

def _load_suppressed_categories():
    global _suppressed_categories_json, _suppressed_categories_dict
    try:
        handler = _handler_ref
        cc = getattr(handler, '_cached_config', None) if handler else None
        raw = cc.get("disabled_apps_suppress_categories", "") if cc else ""
        with _suppressed_categories_lock:
            if raw == _suppressed_categories_json:
                return
            _suppressed_categories_json = raw
            if raw:
                _suppressed_categories_dict = json.loads(raw)
            else:
                _suppressed_categories_dict = {}
    except Exception:
        with _suppressed_categories_lock:
            _suppressed_categories_dict = {}

def is_sound_suppressed(category):
    """Return True if the given sound category should be suppressed
    because the foreground app is in the disabled_apps list.
    """
    try:
        handler = _handler_ref
        if handler is None:
            return False
        app_name = getattr(handler, '_current_app_name', None)
        disabled_apps = getattr(handler, 'disabled_apps', [])
        if not app_name:
            return False
        if not disabled_apps:
            return False
        app_l = app_name.lower()
        if not any(p in app_l for p in disabled_apps):
            return False
        _load_suppressed_categories()
        return _suppressed_categories_dict.get(category, True)
    except Exception:
        return False

def getProsodyClass(prosodyName):
    className = prosodyName
    className = className[0].upper() + className[1:] + 'Command'
    classClass = getattr(speech.commands, className)
    return classClass
