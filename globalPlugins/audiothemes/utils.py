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
	try:
		arr = array.array('h')
		arr.frombytes(audio_bytes)
	except Exception:
		return audio_bytes
	n = len(arr) // 2
	result = array.array('h', (int((arr[i * 2] + arr[i * 2 + 1]) * 0.5) for i in range(n) for _ in range(2)))
	return result.tobytes()


# Rate-limited reporting of dropped sound tasks.
# These drops used to be logged at DEBUG only, which is invisible at NVDA's default
# INFO log level, so an overflowing queue produced "no sounds at all" with no trace
# left in the log.  WARNING keeps them visible without flooding (one line / 2 seconds).
_drop_report_lock = threading.Lock()
_drop_report_last = 0.0
_drop_report_count = 0


def report_dropped_task(pool_name, func, tasks):
    """Report a sound task that had to be dropped because a worker queue was full.

    pool_name: human readable name of the queue (shown in the log).
    func:      the callable that was dropped (may be None for buffer-only queues).
    tasks:     the Queue the task could not be enqueued into (used for qsize()).
    """
    global _drop_report_last, _drop_report_count
    if func is None:
        name = "<audio buffer>"
    else:
        try:
            name = (
                getattr(func, "__qualname__", None)
                or getattr(func, "__name__", None)
                or repr(func)
            )
        except Exception:
            name = "<unknown>"
    with _drop_report_lock:
        _drop_report_count += 1
        now = time.monotonic()
        if now - _drop_report_last < 2.0:
            return
        _drop_report_last = now
        count = _drop_report_count
    pending = 0
    try:
        pending = tasks.qsize()
    except Exception:
        pass
    log.warning(
        "%s: queue full - sound task %s dropped (%d dropped so far, %d still queued)"
        % (pool_name, name, count, pending)
    )


# --- Base-profile config writes -------------------------------------------
# NVDA's config.AggregatedSection.__setitem__ writes through to the MOST
# recently activated configuration profile that contains the section, and if
# NO profile contains the section it CREATES it in the most recently activated
# profile (config/__init__.py _getUpdateSection).  Sections that exist in
# nvda.ini (e.g. [audiothemes]) always land in nvda.ini, but a section that is
# missing from nvda.ini (e.g. [browsernav], [unspoken]) is silently redirected
# into the active configuration profile - and the value disappears again as
# soon as that profile is deactivated or removed.  This is why the settings
# dialog's BrowserNav volumes/options did not retain when a profile was
# active.  write_config_to_base() writes straight into the base (nvda.ini)
# profile so the value persists regardless of active profiles.


def write_config_to_base(section, key, value):
    """Persist *value* under *key* in *section* of the base nvda.ini config.

    The base profile is config.conf.profiles[0]; NVDA always writes it back to
    disk on config.save().  The aggregate section cache is cleared for *section*
    so both NVDA's own leaf cache and the addon's runtime caches re-read the new
    value.  Falls back to the standard aggregate write on any failure.
    """
    try:
        base = config.conf.profiles[0]
    except Exception:
        base = None
    if base is not None:
        try:
            sect = base.get(section)
            if sect is None:
                sect = base[section] = {}
            sect[key] = value
            try:
                root = config.conf.rootSection
                root._cache.pop(section, None)
            except Exception:
                pass
            return True
        except Exception:
            try:
                config.conf[section][key] = value
            except Exception:
                log.debug("AudioThemes: swallowed Exception in utils.write_config_to_base")
            return False
    try:
        config.conf[section][key] = value
    except Exception:
        log.debug("AudioThemes: swallowed Exception in utils.write_config_to_base")
    return False


# --- Say All detection ----------------------------------------------------
# SayAllHandler.isRunning() is only "a Say All reader object exists".  A Say
# All that dies inside NVDA (speech.sayAll._onLineReached OSError in the log)
# never calls stop(), so the reader can stay referenced and isRunning() stays
# True.  Both theme-sound muting gates read it, so a crashed Say All silently
# muted every theme sound while normal navigation kept working - and because
# the gate logged nothing, it left no trace.
# We therefore additionally require that Say All driven speech was produced
# recently; once it stops, the gate opens again within SAY_ALL_STALE_AFTER.
SAY_ALL_STALE_AFTER = 15.0

_say_all_state_lock = threading.Lock()
_last_say_all_speech = 0.0
_first_say_all_seen = 0.0
_last_non_sayall_speech = 0.0


def note_say_all_speech(reason=None):
    """Remember that NVDA just produced speech driven by a Say All."""
    try:
        if reason is None:
            return
        name = getattr(reason, "name", None)
        if name != "SAYALL":
            global _last_non_sayall_speech
            with _say_all_state_lock:
                _last_non_sayall_speech = time.monotonic()
            return
        global _last_say_all_speech
        with _say_all_state_lock:
            _last_say_all_speech = time.monotonic()
    except Exception:
        log.debug("AudioThemes: swallowed Exception in utils.note_say_all_speech")


def say_all_running():
    """True while a Say All is genuinely running.

    Same as SayAllHandler.isRunning(), but also expires if Say All has stopped
    producing speech for SAY_ALL_STALE_AFTER seconds, so a crashed/stuck Say
    All can no longer keep theme sounds muted indefinitely.

    Additionally, if non-SAYALL speech occurred after the last SAYALL speech,
    treat the Say All as stale (gate opens immediately) to unlatch on navigation
    after a crash.
    """
    try:
        from speech.sayAll import SayAllHandler
        running = SayAllHandler.isRunning()
    except Exception:
        running = False
    now = time.monotonic()
    global _first_say_all_seen, _last_non_sayall_speech, _last_say_all_speech
    with _say_all_state_lock:
        if not running:
            _first_say_all_seen = 0.0
            return False
        if _last_non_sayall_speech > _last_say_all_speech and _last_non_sayall_speech <= now:
            # Navigation/speech not from Say All happened after last SAYALL speech
            return False
        last = _last_say_all_speech
        if last <= 0.0:
            # No Say All driven speech recorded yet (Say All just started, or
            # it ran before this hook existed). Fall back to when we first saw
            # isRunning() == True so a stale value still expires.
            if _first_say_all_seen <= 0.0:
                _first_say_all_seen = now
            last = _first_say_all_seen
        else:
            _first_say_all_seen = 0.0
        return (now - last) <= SAY_ALL_STALE_AFTER


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
            except (KeyboardInterrupt, SystemExit):
                raise
            finally:
                self.is_busy = False
                self.tasks.task_done()


class ThreadPool:
    """
    Pool of threads consuming tasks from a bounded queue.

    Key fixes vs. the original:
    * Queue is **bounded** (maxsize=30) and add_task() drops the task when the
      queue is full -- a bounded queue with capacity == num_threads would block
      the NVDA main thread whenever all workers were busy, causing the watchdog
      freezes observed in the log.
    * add_task() is non-blocking by design (no timeout on put) and returns a
      bool: False means the task was refused because the queue was full.
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
            return True
        except queue.Full:
            # Queue is full (user moved mouse/keyboard too fast) -> drop the task
            # gracefully, but report it so silent sound loss stays diagnosable.
            report_dropped_task("AudioThemes ThreadPool", func, self.tasks)
            return False

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
            try:
                self.tasks.put(_WORKER_STOP, timeout=2.0)
            except Exception:
                log.debug("AudioThemes: swallowed Exception in utils.shutdown")
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

_threadPool = None
def _get_threadPool():
    global _threadPool
    if _threadPool is None:
        _threadPool = ThreadPool(1)
    return _threadPool

class _ThreadPoolProxy:
    """Lazy proxy that creates the real ThreadPool on first attribute access."""
    def __getattr__(self, name):
        return getattr(_get_threadPool(), name)

threadPool = _ThreadPoolProxy()

phoneticPunctuationConfigKey = "phoneticpunctuation"
_pp_config_cache = {}
_pp_config_lock = threading.Lock()

def refreshPpConfigCache():
    global _pp_config_cache
    try:
        section = config.conf.get(phoneticPunctuationConfigKey, {})
        new_cache = dict(section)
    except Exception:
        new_cache = {}
    with _pp_config_lock:
        _pp_config_cache = new_cache

def getConfig(key):
	# Lock-free fast path: _pp_config_cache is an atomic reference swap (GIL-safe).
	cache = _pp_config_cache
	try:
		return cache[key]
	except KeyError:
		log.debug("AudioThemes: swallowed KeyError in utils.getConfig")
	# Cache miss — acquire lock for the fallback path.
	with _pp_config_lock:
		try:
			return _pp_config_cache[key]
		except KeyError:
			log.debug("AudioThemes: swallowed KeyError in utils.getConfig")
	try:
		val = config.conf[phoneticPunctuationConfigKey].get(key)
	except KeyError:
		return None
	with _pp_config_lock:
		_pp_config_cache[key] = val
	return val

def setConfig(key, value):
	try:
		config.conf[phoneticPunctuationConfigKey][key] = value
	except KeyError:
		try:
			config.conf[phoneticPunctuationConfigKey] = {}
			config.conf[phoneticPunctuationConfigKey][key] = value
		except Exception:
			log.debug("AudioThemes: swallowed Exception in utils.setConfig")
	with _pp_config_lock:
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

_sounds_path_cache = os.path.join(
    os.path.split(os.path.split(os.path.abspath(os.path.dirname(__file__)))[0])[0],
    "sounds"
)

def getSoundsPath():
    return _sounds_path_cache

# The browser navigation sounds live in a sub folder of the built-in sounds.
# Several wave packs (3d, chimes, classic, pan-chimes, punctuation) are shared
# between the browser navigation engine and the earcon rules, and are stored
# ONLY once, under "sounds\\browsernav". The helpers below resolve a stored
# relative path (for example "classic\\news.wav") against both locations so old
# saved rules keep working and nothing is duplicated inside the package.
_browsernav_sounds_path_cache = os.path.join(_sounds_path_cache, "browsernav")

def getBrowsernavSoundsPath():
    return _browsernav_sounds_path_cache

def _soundsSearchPaths():
    return (_sounds_path_cache, _browsernav_sounds_path_cache)

def resolveSoundsCategoryPath(category):
    """Return the folder that holds the wave files of a built-in sound category.

    The main sounds folder wins; the browser navigation sounds folder is used as
    a fall back, so removing the duplicated packs never hides a category.
    """
    if not category:
        return None
    fallbackPath = None
    for basePath in _soundsSearchPaths():
        candidatePath = os.path.join(basePath, category)
        if not os.path.isdir(candidatePath):
            continue
        if fallbackPath is None:
            fallbackPath = candidatePath
        try:
            entries = os.listdir(candidatePath)
        except OSError:
            continue
        for entry in entries:
            if not entry.lower().endswith(".wav"):
                continue
            if os.path.isfile(os.path.join(candidatePath, entry)):
                return candidatePath
    return fallbackPath

def resolveSoundsRelPath(relPath):
    """Return the full path of a stored built-in wave file, or None if missing."""
    if not relPath:
        return None
    try:
        cleanRelPath = str(relPath).replace("/", os.sep)
    except Exception:
        return None
    for basePath in _soundsSearchPaths():
        candidatePath = os.path.join(basePath, cleanRelPath)
        if os.path.isfile(candidatePath):
            return candidatePath
    return None

_cached_blacklist_string = None
_cached_blacklist_set = set()
_blacklist_lock = threading.Lock()

def isAppBlacklisted():
    global _cached_blacklist_string, _cached_blacklist_set
    try:
        handler = _handler_ref
        appName = getattr(handler, '_current_app_name', "")
    except Exception:
        appName = ""
    if not appName:
        return False
        
    current_blacklist = getConfig("applicationsBlacklist")
    # Double-checked locking: skip lock when blacklist hasn't changed.
    if current_blacklist != _cached_blacklist_string:
        with _blacklist_lock:
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

_pp_enabled_result = None

def isPhoneticPunctuationEnabled():
    global _pp_enabled_result
    if _pp_enabled_result is not None:
        return _pp_enabled_result
    _pp_enabled_result = not isAppBlacklisted() and getConfig("enabled")
    return _pp_enabled_result

def _reset_pp_enabled_cache():
    global _pp_enabled_result
    _pp_enabled_result = None

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

def getCurrentContext(fetch_url=False):
    try:
        handler = _handler_ref
        appName = getattr(handler, '_current_app_name', "")
        windowTitle = getattr(handler, '_current_window_title', "")
        url = getattr(handler, '_current_url', None)
        if fetch_url and url is None:
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
        raw = cc.get("disabled_apps_suppress_categories", '{"theme_sounds":true,"typing_sounds":true,"earcons":true,"browsernav":true,"sentencenav":true,"textnav":true,"ui_beeps":true}') if cc else ""
        with _suppressed_categories_lock:
            if raw == _suppressed_categories_json:
                return
            if raw:
                parsed = json.loads(raw)
            else:
                parsed = {}
            _suppressed_categories_json = raw
            _suppressed_categories_dict = parsed
    except Exception:
        with _suppressed_categories_lock:
            _suppressed_categories_dict = {}

_needs_window_title = False

def refresh_needs_window_title():
    """Recompute whether any loaded rule uses a non-empty windowTitleRegex.

    The main thread must never call obj.name (blocking IAccessible COM) unless
    a rule can actually consume the window title. Default rules all use an
    empty windowTitleRegex, so this stays False and the COM call is skipped.
    """
    global _needs_window_title
    found = False
    try:
        from . import frenzy
        from . import phoneticPunctuation as pp
        for d in (
            getattr(frenzy, 'roleRules', None) or {},
            getattr(frenzy, 'stateRules', None) or {},
            getattr(frenzy, 'formatRules', None) or {},
            getattr(frenzy, 'numericFormatRules', None) or {},
            getattr(frenzy, 'otherRules', None) or {},
        ):
            for lst in d.values():
                for r in lst:
                    if getattr(r, 'windowTitleRegex', ''):
                        found = True
                        break
                if found:
                    break
            if found:
                break
        if not found:
            rbf = getattr(pp, 'rulesByFrenzy', None) or {}
            for lst in rbf.values():
                for r in lst:
                    if getattr(r, 'windowTitleRegex', ''):
                        found = True
                        break
                if found:
                    break
    except Exception:
        found = False
    _needs_window_title = found

def needs_window_title():
    """True when at least one rule can consume the navigator window title."""
    return _needs_window_title


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
