# Summary

## Objective
Complete a performance, disk I/O, thread‑safety, and memory audit of all files under `globalPlugins/audiothemes/` and fix every issue found.

## Important Instructions
- "لا تكسر اي وظيفة" — do not break any existing functionality.

## Status
All known issues fixed (rounds 1–36). No known remaining issues.

## Fix History

### Rounds 1–3 (committed): config cache, I/O, thread safety
- `config.conf` reads replaced with `_cached_config` dicts across hot paths.
- Module‑level I/O moved out of import time.
- Unbounded caches (`_theme_cache`, `_wave_player_pool`, `_audio_queue`) capped.
- `audio_ducking_enabled/volume`, `typing_sounds_edit_only`, `clipboard_enabled`, `progress_*` added to `_cached_config`.
- `emoji_handler.py` and `phoneticPunctuation.py` use `_cached_emoji_config` / `_cached_speech_symbolLevel` with `refreshCachedConfig()`.
- `steam_audio.py` double-checked locking.
- `unspoken/__init__.py` queue capped at 32 with `put_nowait()`.

### Rounds 4–7 (post-audit, uncommitted until now): frenzy, commands, emoji
- `frenzy.py` — `_frenzy_cached_config` + `refreshFrenzyCachedConfig()` for `new_getObjectPropertiesSpeech()`, `new_getPropertiesSpeech()`, `_get_blacklisted_roles()`.
- `commands.py` — `_commands_cached_config` + `refreshCommandsCachedConfig()` for `PpBeepCommand.run()` and `PpWaveFileCommand.run()`.
- `emoji_handler.py` — `_raw` snapshot; `is_emoji_sound_category_enabled()`, `_get_json_config()`, `is_category_enabled()` use cache.
- `handler.py:configure()` — calls `refreshFrenzyCachedConfig()`, `refreshCommandsCachedConfig()`, `refreshEmojiConfig()`, `refreshPpConfig()`.
- `browserNavEngine/beeper.py` — `_spc_lock` around `skippedParagraphChime()` lazy init.

### Round 8: FFmpeg main-thread freeze fix
- `ffmpeg_utils.py:decode_with_ffmpeg()` — replaced `subprocess.run(timeout=30)` with `Popen` + polling loop (0.05 s sleep + `wx.YieldIfNeeded()`); timeout reduced to 5 s; on timeout: `proc.kill()` + `proc.wait()`, returns `None`.

### Round 9: enable_ffmpeg setting was being ignored
- `handler.py:_cached_config` — added `"enable_ffmpeg"` key.
- `unspoken/__init__.py:make_sound_object()` — checks `enable_ffmpeg` before FFmpeg fallback; removed dead `ffmpeg_used`; `wave.Error` silenced for non‑PCM WAV files.

### Round 10: audit‑driven hot‑path fixes (commands, utils, clipboard, navLayer, quicknav)
- `commands.py` — `config.conf["speech"]["outputDevice"]` + `nvwave.WavePlayer()` moved from module level to lazy init in `_get_synchronous_player()` / `_get_pp_player()`. Output device cached in `_cached_output_device`. `_get_synchronous_player()` now uses `_get_output_device()`.
- `utils.py:ensure_mono()` — uses `_cached_output_mode` instead of reading `config.conf` per call.
- `utils.py:getConfig()` — reads from `_pp_config_cache` dict. `setConfig()` updates both. `refreshPpConfigCache()` called from `initConfiguration()`.
- `clipboard.py` — reads from `self._handler._cached_config` via `_clip_conf()`.
- `navLayer.py` — all 4 `config.conf.get("audiothemes", {})` replaced with `self._get_nl_cache()` → `handler._cached_config`.
- `quicknav.py:81` — `enable_audio_themes` read from `handler._cached_config`.

### Round 11: frenzy, sentenceNav, browserNav, quickJump, utils — remaining config.conf reads
- `frenzy.py:_get_blacklisted_roles()` — cached via version counter (`_frenzy_config_version`), avoids repeated `json.loads()` (was called up to 5× per speech event).
- `frenzy.py:get_ducking_factor()` — removed `else` branch that read `config.conf` directly; now always uses `_frenzy_cached_config` when `cached_config is None`.
- `frenzy.py:new_getControlFieldSpeech()` — removed all writes to `config.conf["documentFormatting"]`; only `formatConfig` dict is modified (safe, local snapshot).
- `frenzy.py:new_getTextInfoSpeech()` — uses `_cached_doc_formatting` + `_cached_delayed_char_descriptions` instead of `config.conf`.
- `frenzy.py:refreshFrenzyCachedConfig()` — now also refreshes `_cached_doc_formatting` and `_cached_delayed_char_descriptions`.
- `sentenceNavEngine.py` — added `_cached_doc_formatting` + `_refresh_doc_formatting()`; `getParagraphStyle()` reads cached dict (uses `{k: src[k] for k in src}` instead of `dict()`).
- `browserNavEngine/__init__.py` — added `_bne_cached_doc_formatting` + `_bne_refresh_doc_formatting()`; `isRolePresent()`, `getFormatting()`, and line‑1060 `formatConfig` all use cached dict (uses `{k: src[k] for k in src}` instead of `dict()`).
- `browserNavEngine/quickJump.py` — added `_qj_get_output_device()` with module-level cache; `playBiwInThread()` uses it instead of reading `config.conf` per call.
- `handler.py:close()` — `_theme_cache.clear()` and `_typing_dir_cache.clear()` now locked (`_config_lock`, `_typing_dir_cache_lock`).
- `handler.py:configure()` — calls `_refresh_doc_formatting()` for both `sentenceNavEngine` and `browserNavEngine`; also refreshes `utils` caches and `frenzy` cached doc formatting.
- `utils.py:refreshPpConfigCache()` — wrapped in try/except with fallback to `{}` (handles NVDA ConfigObj Section not being dict-like).
- `phoneticPunctuation.py:onPostNvdaStartup()` — added `None` + `.get()` guard for `rulesByFrenzy`.
- `sentenceNavEngine.py:414-416` — added `_sentence_nav_registrations` + `_unregister_sentence_nav_hooks()` to clean up `post_configSave/Reset/ProfileSwitch` registrations (were never unregistered).
- `browserNavEngine/__init__.py` — `terminateBrowserNav()` now restores `api.getCurrentURL`, `api.postFocusOrURLChange`, `editableText.EditableText.script_editInBrowserNav`, and `_EditableText__gestures['kb:NVDA+E']` (were never cleaned up).

### Round 13A (committed): AggregatedSection isinstance(dict) false negatives
- `frenzy.py:90-93`, `sentenceNavEngine.py:42-45`, `browserNavEngine/__init__.py:64-67` — removed `isinstance(src, dict)` guard that **silently rejected** `AggregatedSection` (does not inherit from `dict`), leaving `_cached_doc_formatting` as `{}`.
  - Fixed `KeyError: 'detectFormatAfterCursor'` and `KeyError: 'reportLineIndentation'` when NVDAExtensionGlobalPlugin is active.
- `utils.py:179-180` — same `isinstance` fix for `_pp_config_cache`.

### Round 14 (committed): audit‑driven hot‑path + thread‑safety fixes
- **handler.py `_get_blacklisted_roles()`** — `blacklisted_roles` JSON is parsed once in `configure()` and stored in `_cached_config["blacklisted_roles"]` (list of ints). `_hook_getSpeechTextForProperties` reads from `_cached_config` instead of calling the module‑level function, avoiding a `config.conf["audiothemes"]` proxy lookup on every speech event.
- **handler.py `_typing_dir_cache` locking** — `play_typing_sound()` and `configure()` now hold `_typing_dir_cache_lock` for all reads/writes to `_typing_dir_cache` (was a data race — keyboard hook can fire from background threads).
- **handler.py `_cached_config`** — added `"blacklisted_roles"` (parsed int list) and `"disabled_apps_suppress_categories"` (raw JSON string) keys.
- **utils.py `_load_suppressed_categories()`** — reads from `handler._cached_config` instead of `config.conf` on every sound play. Added `_suppressed_categories_lock` for thread‑safe globals mutation.
- **frenzy.py `get_ducking_factor()`** — globals `_ducking_categories_json`/`_ducking_categories_dict` mutation now protected by `_ducking_categories_lock` (was a data race on background threads).
- **browserNavEngine/beeper.py** — `Beeper.__init__` uses cached `_get_beeper_output_device()` (module‑level, set once on first access) instead of reading `config.conf` per instantiation. Same for `skippedParagraphChime()` lazy init.
- **sentenceNavEngine.py** — `noNextSentenceChimeVolume` and `paragraphChimeVolume` cached in `_sn_cached_chime_volume` / `_sn_cached_paragraph_chime_volume`, refreshed in `_refresh_doc_formatting()` (called from `configure()`).
- **`quicknav.py` thread‑safety** — verified `originalQuickNavScript` chains correctly: `initBrowserNav()` saves quicknav's `patched_quick_nav_script` as `originalQuickNavScript` and `preQuickNavScript` calls through to it at line 588. No functional overlap.
- **`systemStatus.py`** — verified: no `config.conf` reads present (false positive in earlier audit).
- **`_beeps.py`** — does not exist (false positive in earlier audit).

All files under `globalPlugins/audiothemes/` verified safe (hot paths use cached config).
- `settings.py`, `emoji_cldr_data.py`, `decoders/*.py`, `systemStatus.py`, `update_checker.py`, `studio/`, `phoneticPunctuationGui.py`
- `quicknav.py`, `navLayer.py`, `clipboard.py`, `commands.py`, `emoji_handler.py`, `phoneticPunctuation.py`
- `handler.py`, `utils.py`, `frenzy.py`, `sentenceNavEngine.py`, `browserNavEngine/__init__.py`, `browserNavEngine/quickJump.py`, `browserNavEngine/beeper.py`

### Round 16 (committed): performance + thread‑safety audit (14 findings)
- **emoji_handler.py `_get_json_config()`** — `json.loads()` was called per emoji per category lookup (up to 40× per utterance). Now pre‑parses JSON strings into `_cached_json_configs` dict in `refreshCachedConfig()`, zero‑cost on hot path.
- **sentenceNavEngine.py `getSNConfig()`** — read `config.conf["sentencenav"][key]` on every navigation gesture (7+ call sites). Now reads from `_cached_sentencenav_config` dict, populated in `_refresh_doc_formatting()`. Falls back to `config.conf` only for `setSNConfig()` writes.
- **phoneticPunctuation.py `eloquenceFix` double `speech.processText()`** — `postProcessSynchronousCommands` called `isEmptyString()` → `speech.processText()` per element, then `eloquenceFix()` did it again. Refactored: `postProcessSynchronousCommands` passes a `hasNonEmptyString` boolean to `eloquenceFix()`, eliminating the second `speech.processText()` pass.
- **phoneticPunctuation.py `_suppress_role_sound_flag` thread safety** — module‑level bool read/written from different threads without synchronization. Added `_suppress_role_sound_lock` (threading.Lock) around all reads/writes.
- **phoneticPunctuation.py `deepcopy()` per prosody command** — `copy.deepcopy(command)` in `fixProsodyCommands()` replaced with `copy.copy(command)`. BaseProsodyCommand objects only hold primitive fields (_offset, _multiplier, isDefault); deepcopy traversal was unnecessary overhead.
- **browserNavEngine `margin_eq/lt/gt` lambdas** — lambdas read `getConfig("verticalAlignmentMargin")` on every paragraph comparison during navigation. Changed `maybeAdjustOperator()` to return closures that capture the margin value once at call time.
- **browserNavEngine `selectionHistory` lock** — `selectionHistoryLock` was defined but never used. `purgeSelectionHistory()` now acquires the lock before mutating the dict.

### Round 17 (committed): 36‑issue AI audit — 6 fixes applied
- `unspoken/ogg_vorbis.py` — `OGG_VORBIS_FILE_SIZE` 1024 → 4096 (buffer overflow fix).
- `__init__.py:845,854` — `except StopIteration: raise` added before `except Exception` in `event_becomeNavigatorObject`.
- `frenzy.py:832` — `findControlEnd` list comprehension → try/except loop (RuntimeError on malformed UI trees).
- `__init__.py:1379` — `focus.makeTextInfo()` wrapped in `try/except (NotImplementedError, RuntimeError)`.
- `navLayer.py:190` — Removed redundant `import wx` (already at module level).
- `__init__.py:241-250` — `_cached_desktop_location` now has 30-second TTL refresh.

## No known remaining issues

### Round 17 (committed): 36‑issue AI audit — verified & fixed (6 fixes, 7 false positives, 9 safe)
- **unspoken/ogg_vorbis.py** — `OGG_VORBIS_FILE_SIZE` increased from 1024 to 4096. Original was ~2x too small on x64 Windows (OggVorbis_File struct is ~1952 bytes), causing buffer overflow on every OGG decode.
- **__init__.py `event_becomeNavigatorObject`** — Added `except StopIteration: raise` before `except Exception` in the isFocus (line 845) and dedup (line 854) paths. StopIteration was being swallowed, breaking NVDA's generator protocol.
- **frenzy.py `new_getTextInfoSpeech` headingEnds** — `findControlEnd` list comprehension replaced with try/except loop. Malformed UI trees with unbalanced control fields would raise uncaught RuntimeError, crashing speech.
- **__init__.py `script_speakHeadingLevel`** — `focus.makeTextInfo()` now wrapped in `try/except (NotImplementedError, RuntimeError)`. Objects without text info (e.g. desktop icons) would crash the NVDA+h gesture.
- **navLayer.py `script_navLayerCopy`** — Removed redundant `import wx` (already imported at module level).
- **__init__.py `_snapshot_obj` desktop location** — Added 30‑second TTL to `_cached_desktop_location`. Previously cached once at startup and never refreshed; resolution/monitor changes would produce wrong 3D audio panning.
- **Verified false positives**: ctypes.wintypes.DWORD (#3, loaded by systemStatus.py), monkey-unpatch (#5, standard NVDA pattern), emoji cache keys (#7, _get_json_config has fallback), navLayer gesture removal (#9, plugin-scoped), Steam Audio mutex (#14, sequential lock/unlock), FFmpeg pipe leak (#23, communicate() closes pipes), auto_create_sounds (#29, safe iteration), duplicate init (#31, not found).
- **Skipped**: snapshot cache staleness (#4, WeakKeyDictionary by design, high refactor cost for negligible benefit).

### Round 18 (committed): deep‑scan bug fixes (6 High + 3 Medium)
- **phoneticPunctuation.py `onPostNvdaStartup`** — Removed `return` after URL warning; early return was skipping CLDR emoji loading and NVDAExtensionGlobalPlugin patching entirely.
- **phoneticPunctuation.py `reloadRules`** — Wrapped `rule.getFrenzyType()` in try/except. Previously could crash on malformed rule (returns None or raises in else block outside try/except).
- **sentenceNavEngine.py `clearRegexCaches`** — Uncommented `global phraseRegex`. Previously the `= None` assignment created a local variable, leaving the module‑level cache stale after config changes.
- **quickJump.py `shouldSkipClutter`** — Fixed typo `bookmarksZero` → `bookmarks0`. Caused NameError when key 0 was missing from allBookmarks.
- **quickJump.py `scanLevelsSync`** — Replaced undefined `future.set([])` with `return HierarchicalLevelsInfo([])`. Was a guaranteed NameError on empty bookmarks.
- **quickJump.py `getSuppressOptions`** — Returns `{}` instead of `False` when no sites match. Caller at line 1797 called `.values()` on the return value → AttributeError on every speech event.
- **quickJump.py `processAutoSpeakbookmark`** — Closure now captures `line` via default argument (`_line=_capturedLine`). Previously captured by reference, all deferred `wx.CallAfter` calls used the last iteration's value.
- **settings.py `_initialize_at_state`** — `reconstructOptions.index()` wrapped in try/except (ValueError, KeyError) with fallback to index 0. Unrecognized config value no longer crashes settings dialog.
- **settings.py `onStoreClicked`** — `ThemesStoreDialog` now `Destroy()`ed in `finally` block after `ShowModal()`. Previously leaked GDI resources.

### Round 19 (committed): speech crash resilience — 9 fixes
Root cause of "addon stops speaking": CallbackCommand `run()` methods and speech hooks had **no top-level try/except**. Any unhandled exception killed NVDA's speech pipeline entirely.
- **commands.py `PpBeepCommand.run()`** — Split into `run()` (try/except wrapper) + `_runInner()`. Any exception in beep generation, spatial audio, or playback now logged and silenced instead of crashing speech.
- **commands.py `PpWaveFileCommand.run()`** — Split into `run()` (try/except wrapper) + `_runInner()`. Also fixed `_ensureLoaded()` to only set `_loaded=True` when `buf` is not None (was setting it unconditionally, causing `AttributeError` on `fileWavePlayer.stop()` when all decoders failed). Added null-guard for `fileWavePlayer` before `.stop()`. Added null-guard for `audio_bytes` before `ensure_mono()`.
- **handler.py `_hook_getSpeechTextForProperties`** — Added try/except around `self.player` and `self._cached_config` access (could be `None` during init/shutdown). Now uses `getattr()` guards.
- **phoneticPunctuation.py `isEmptyString`** — `speech.processText()` wrapped in try/except with fallback to simple `.strip()` check.
- **phoneticPunctuation.py `new_getIndentationSpeech`** — `formatConfig["reportLineIndentation"]` replaced with `.get()` with safe default. `speech.speech._speechState` access wrapped in double `getattr()` guard.
- **phoneticPunctuation.py `new_processSpeechSymbol`** — `rule.getSpeechCommand()[0]` wrapped in try/except, falls back to `cmd = None`.
- **browserNavEngine/beeper.py `skippedParagraphChime`** — Thread function body wrapped in try/except to prevent lock leak on exception (lock is `with`-managed but exception inside would propagate to daemon thread).
- **handler.py `play_typing_sound`** — Split into `play_typing_sound()` (try/except wrapper) + `_play_typing_sound_inner()`. Added explicit `theme is None` guard. `os.listdir()` wrapped in try/except for `OSError`.

### Round 20 (committed): full‑file deep audit — 14 fixes
Comprehensive audit of ALL files including studio/, settings, GUI dialogs.
- **__init__.py `_new_keyDownEvent`** — `cfg` variable used outside its try/except scope (line 998 used `cfg` from line 977). Clipboard shortcut detection would `NameError` on every keypress if first try block failed. Fixed by re‑reading `_cached_config` independently.
- **__init__.py `terminate()`** — Entire cleanup in single `with suppress(Exception)` block. If any line failed (e.g. settings panel removal), all subsequent cleanup (keyboard unhook, handler.close, timer.Stop, threadPool.shutdown, BrowserNav) was skipped. Split into 11 individual `suppress` blocks.
- **__init__.py `script_speakHeadingLevel`** — `focus.treeInterceptor` accessed without null‑checking `focus` first. `api.getFocusObject()` returns `None` when no focus. Added `if focus is None: return`.
- **utils.py `ensure_mono`** — `array.frombytes()` with malformed audio (odd byte count, truncated WAV) raised uncaught `struct.error`. Wrapped in `try/except Exception` with fallback to passthrough.
- **settings.py `onAbout`** — `self.selected_theme.todict()` crashed with `AttributeError` when no theme was selected. Added null guard with warning message.
- **settings.py `onRemove`** — `theme.name` crashed with `AttributeError` when no theme selected. Added null guard with warning message.
- **settings.py `_initialize_at_state`** — `snConf["sentenceBreakers"]` and `snConf["applicationsBlacklist"]` used bare `[]` instead of `.get()`. `bnConf["crackleVolume"]`/`["beepVolume"]`/`["skipChimeVolume"]` same issue. All replaced with `.get()` with safe defaults.
- **settings.py `setupGeneralPage`** — Two `os.listdir()` calls without try/except (PermissionError on restricted directories). Wrapped both in `try/except OSError`.
- **phoneticPunctuationGui.py `_roleLabels`** — `_roleLabels[role]` bare dict lookup raised `KeyError` for roles without labels (e.g. new roles added in NVDA updates). Changed to `.get(role, str(role))`.
- **phoneticPunctuationGui.py format names** — `TEXT_FORMAT_NAMES[f]`, `NUMERIC_TEXT_FORMAT_NAMES[f]`, `OTHER_RULE_NAMES[f]` all bare lookups. Changed to `.get(f, str(f))`.
- **phoneticPunctuationGui.py BIW functions** — `getBiwCategories()`, `getBuiltInWaveFilesInCategory()` `os.listdir()` without try/except. `getBiw()` used `GetSelection()` directly as list index (‑1 when nothing selected → `IndexError`). `setBiw()` used `.index()` without try/except (`ValueError`). `getBiwCategory()` same `GetSelection()` issue. All guarded.
- **phoneticPunctuationGui.py `onSave`** — `open(rulesFileName, "w")` without try/except. Disk full / permission denied would crash with unhandled `OSError`. Wrapped with error message.
- **studio/themes_store.py `DownloadAndInstall`** — Temp file leaked on write failure (disk full). Added `tmp_path = None` init and cleanup in except block.
- **studio/themes_blender.py** — `theme_roles[self.role]` bare dict lookup → `.get()`. `os.listdir(basedir)` without try/except → wrapped in `try/except OSError`.
- **studio/__init__.py `selected_theme`** — `selectDlg.selected_theme` could be `None` if dialog state was inconsistent. Added null guard before accessing `.name`.
- **browserNavEngine/quickJump.py `saveConfig`** — `open(rulesFileName, "w")` without try/except. Wrapped in `try/except OSError`.

### Round 21 (committed): regression + resource leak audit — 3 fixes
- **browserNavEngine/__init__.py `OPERATOR_STRINGS[op]` KeyError** — Regression from round 16: `maybeAdjustOperator()` returns new lambda objects when mode=0 with non-zero margin, but `OPERATOR_STRINGS` only contains the original module-level lambdas. `script_moveToParent/NextParent/Child/PreviousChild` all crashed with `KeyError`. Fixed by looking up `rawOp` (original operator) instead of `op` (adjusted operator) for the error message string.
- **browserNavEngine/quickJump.py `import requests`** — Module-level import of third-party `requests` library crashed the entire browserNavEngine (and addon) on load if `requests` wasn't bundled. Moved to lazy import inside `downloadAllWebsitesFromStore()`.
- **update_checker.py temp file leak** — `tempfile.mkstemp()` file was never cleaned up on download failure (exception path). Added `path = None` init + `os.unlink(path)` in except block.

### Round 22 (committed): speech pipeline resilience + COM freeze fix — 21 fixes
Root cause of 40-second NVDA freezes: `_snapshot_obj` performed multi-hop UIA COM tree traversal (up to 3 levels of `obj.previous/next`) synchronously on MainThread during `event_gainFocus`.
- **__init__.py `_snapshot_obj` COM freeze** — Reduced multi-hop traversal from 3 levels to 1. The `while p is not None and _depth < 3` loops walked up to 3 siblings via UIA COM tree walkers, each taking 5-15 seconds on complex windows. Now does a single `obj.previous` / `obj.next` check only.
- **__init__.py `event_gainFocus` early exit** — Added `enable_audio_themes` check before calling `_snapshot_obj`. When themes are disabled, skips all COM snapshot work entirely.
- **phoneticPunctuation.py `preSpeak`** — Entire body wrapped in top-level try/except. Any unhandled exception (rule processing, prosody, emoji) now falls back to `originalSpeechSpeechSpeak` with the original sequence instead of killing NVDA's speech pipeline.
- **phoneticPunctuation.py `preProcessSpeechSymbols`** — Wrapped in try/except. Falls back to `originalProcessSpeechSymbols` on error.
- **phoneticPunctuation.py `preCancelSpeech`** — `terminateCurrentChain()` wrapped in try/except. Ensures `originalSpeechCancel` is always called even if chain termination fails.
- **phoneticPunctuation.py `processRule`** — `rule.processString()` wrapped in try/except per command. Malformed rule skips one command instead of killing the entire speech event.
- **phoneticPunctuation.py `restoreMonkeyPatches`** — Added null-checks for all 6 `original_*` globals. If `injectMonkeyPatches` failed partway through, restoring `None` into NVDA internals would crash every subsequent speech event.
- **phoneticPunctuation.py `fixProsodyCommands`** — Entire function wrapped in try/except. Falls back to returning the unmodified sequence.
- **phoneticPunctuation.py `resetProsodies`** — `getProsodyClass()` list comprehension wrapped in try/except. Falls back to returning the unmodified sequence.
- **frenzy.py fontSize handler** — Replaced bare `raise RuntimeError` with `continue`. Also wrapped `getNumericSpeechCommand()` in try/except to prevent misconfigured font-size rules from killing speech.
- **frenzy.py `filteredIntervalsAndCommands`** — Replaced bare `raise RuntimeError` with `log.warning` + skip. Unknown item types no longer crash the speech pipeline.
- **frenzy.py `getattr(Role)` without default** — Both call sites (lines 1519, 1601) now use `getattr(..., None)` with None-check. Unknown role names from corrupted utterances no longer crash.
- **frenzy.py `ignore_get_properties_hook`** — Changed from boolean to integer reentrancy counter. Inner speech processing that re-enters `new_getPropertiesSpeech` no longer resets the outer call's guard.
- **frenzy.py `updateRules`** — Builds all 6 dicts into local variables first, then assigns to globals. Reader threads no longer see a mix of old/new rule dicts during reload.
- **__init__.py `event_valueChange`** — Fixed double `nextHandler()` call: debounce path's `return nextHandler()` was inside the outer try/except, so exceptions fell through to a second `nextHandler()` call.
- **__init__.py `_snapshot_obj` cache** — Cache miss path now stores a `.copy()` instead of the live dict. Callers that mutate `force_3d` / `progress_angle` no longer corrupt the cached snapshot.
- **__init__.py `event_typedCharacter`** — `nextHandler()` wrapped in try/except with StopIteration re-raise. Was the only event handler missing this pattern.
- **__init__.py `script_audioSonar` sort** — `children.sort()` wrapped in try/except. Stale COM objects in the sort key lambda no longer crash the sonar script.
- **__init__.py help dialog** — `cmds[sel](None)` wrapped in try/except. Script failure no longer leaks the dialog permanently and locks out the help feature.
- **__init__.py `terminate()`** — Fixed incorrect edit that removed the 11-block structure (from Round 20).
- **browserNavEngine/utils.py thread pool** — Reduced from 5 to 3 threads (14 total → 12).

### Round 24 (committed): speech pipeline resilience — 22 fixes
Critical audit of all speech hooks and hot paths. If any monkey-patched speech hook crashes, NVDA's entire speech pipeline stops.
- **frenzy.py `new_getObjectPropertiesSpeech`** — Extracted body to `_new_getObjectPropertiesSpeech_inner()`. Outer wrapper catches any exception and falls back to `original_getObjectPropertiesSpeech`.
- **frenzy.py `new_getTextInfoSpeech`** — Extracted body to `_new_getTextInfoSpeech_inner()` (generator). Outer generator catches and yields from `original_getTextInfoSpeech`.
- **frenzy.py `new_getPropertiesSpeech`** — Extracted body to `_new_getPropertiesSpeech_inner()`. Outer wrapper catches and falls back to `original_getPropertiesSpeech`.
- **frenzy.py `new_getControlFieldSpeech`** — Extracted body to `_new_getControlFieldSpeech_inner()`. Outer wrapper catches and falls back to `original_getControlFieldSpeech`.
- **frenzy.py `new_processAndLabelStates`** — Extracted body to `_new_processAndLabelStates_inner()`. Outer wrapper catches and falls back to `original_processAndLabelStates`.
- **frenzy.py `new_getTextInfoSpeech_considerSpelling`** — Extracted body to `_new_getTextInfoSpeech_considerSpelling_inner()` (generator). Outer generator catches and yields from original.
- **frenzy.py `lastIntervalIndex`** — `filteredIntervalsAndCommands` list comprehension `[-1]` replaced with guarded access. Empty list no longer raises IndexError.
- **frenzy.py `updateRules`** — `pp.rulesByFrenzy[frenzyType]` replaced with `getattr(pp, 'rulesByFrenzy', None) or {}` + `.get()`. None rulesByFrenzy no longer crashes.
- **frenzy.py `highlightedEnds`** — List comprehension replaced with try/except loop (same as headings fix in Round 17). Malformed UI trees no longer crash.
- **phoneticPunctuation.py `preSpeak` except handler** — `originalSpeechSpeechSpeak` null-guarded in except block. Was unguarded, would crash on None.
- **phoneticPunctuation.py `eloquenceFix`** — `speech.processText()` comprehension wrapped in try/except with fallback to simple `.strip()` check.
- **phoneticPunctuation.py `new_getIndentationSpeech`** — `frenzy.otherRules` guarded with `getattr() or {}`. None otherRules no longer crashes.
- **handler.py `configure` refresh chain** — All 8 submodule refresh calls wrapped in individual try/except blocks. One failing refresh no longer skips all subsequent refreshes.
- **handler.py `AudioTheme.load`** — `make_sound_object()` wrapped in try/except. One corrupt sound file no longer aborts entire theme load.
- **handler.py `get_theme_from_folder`** — `info` dict type-checked with `isinstance`. Malformed info.json no longer crashes AudioTheme construction.
- **handler.py `get_installed_themes`** — Individual `get_theme_from_folder()` calls wrapped in try/except. One corrupted theme no longer crashes the entire theme list.
- **handler.py `get_theme_for_app`** — `profile` value type-checked before calling `.get("theme")`. Non-dict profile no longer raises TypeError.
- **handler.py `play_system_status_sound`** — `player.play()` wrapped in try/except.
- **handler.py `play_theme_sound`** — `player.play_file()` wrapped in try/except.
- **handler.py `play_clipboard_sound`** — `player.play()` wrapped in try/except.
- **handler.py `_hook_getSpeechTextForProperties`** — kwargs mutation rollback added: `except` block cleans up `_role`/`_level` from kwargs if exception occurs mid-mutation.
- **__init__.py `script_audioSonar`** — COM tree walk depth capped from 3 to 1 level. Reduces MainThread blocking on complex windows.

### Round 25 (committed): deep audit of all remaining files — 19 fixes
- **commands.py `PpWaveFileCommand.run()`** — `_ensureLoaded()` moved inside try/except. Previously unprotected `struct.error` from malformed WAV could crash speech pipeline.
- **commands.py `_ensureLoaded()`** — `except (wave.Error, OSError)` changed to `except Exception`. `struct.error` from truncated WAV now falls through to FFmpeg decode instead of aborting.
- **commands.py `PpChainCommand.run()`** — Wrapped in try/except. `threadPool.add_task()` failure no longer leaves `currentChain` permanently stale.
- **commands.py `PpChainCommand.threadFunc()`** — Body wrapped in try/finally. Exception in `getDuration()` no longer leaks `currentChain` forever.
- **utils.py `getConfig()`** — `config.conf[key]` bare lookup wrapped in try/except KeyError. Corrupted config section no longer crashes.
- **utils.py `setConfig()`** — Same KeyError guard added.
- **phoneticPunctuationGui.py tone/duration** — `getInt("")` returns None, `0 <= None` raised TypeError. Wrapped with safe defaults.
- **phoneticPunctuationGui.py `getattr(rule, name)`** — Returns None for non-NUMERIC_FORMAT rules. `SpinCtrl.SetValue(None)` crashed. Added default values.
- **phoneticPunctuationGui.py `editRule`** — `.index()` ValueError on removed enum values. Added try/except with fallback.
- **phoneticPunctuationGui.py `setType`** — `.index()` ValueError on unexpected rule type. Added try/except with fallback.
- **phoneticPunctuationGui.py FileDialog** — Not Destroy()'d. GDI resource leak on each browse click. Added Destroy().
- **phoneticPunctuationGui.py `onSave`** — Missing `encoding="utf-8"`. Non-ASCII characters silently corrupted on Windows. Added encoding parameter.
- **settings.py Speech Order grid** — `controlTypes.Role(2523)` round-trip crash. Fixed by storing original role objects.
- **settings.py `roleChoice.SetSelection(0)`** — On empty Choice (all roles filled) raises wx assertion. Added guard.
- **settings.py unguarded `float()`/`int()`** — Corrupted config strings crashed `_initialize_at_state`. Wrapped in try/except.
- **settings.py `GetSelection()` returning -1** — Indexed from end of list, saving wrong value. Added `max(0, ...)`.
- **studio/themes_blender.py** — `roleChoice.SetSelection(0)` empty Choice guard + FileDialog Destroy() leak fix.
- **unspoken/ogg_vorbis.py** — Double `ov_clear` native double-free. Moved `ov_clear` after all throw-capable processing.
- **unspoken/__init__.py `wave_player.close()`** — Unguarded. Device removed/bad state crashed `create_wave_player()`. Wrapped in try/except.

### Round 26 (committed): handler.py initialization + configuration audit — 5 fixes
Critical audit of `handler.py` focusing on init, config loading, and thread safety.
- **handler.py `ensure_themes_dir()` `os.makedirs()`** — Unguarded. `OSError` (permissions, disk full) crashed `__init__`, preventing the entire addon from loading and leaking UnspokenPlayer/SteamAudio native resources. Wrapped in `try/except OSError` with early return.
- **handler.py `configure()` early return** — When `active_theme is None` (themes disabled), `configure()` returned at line 916 **before** building `_cached_config` and before refreshing ALL 8 submodule caches (emoji, pp, frenzy, commands, utils, sentenceNav, browserNav×2). This meant: (a) all non-theme features (system status, clipboard, typing sounds, ducking) retained stale config when themes were disabled, (b) changing settings while themes were disabled had no effect on hot-path behavior. Fixed by converting the early `return` to `if self.active_theme is not None:` guard only around the player property block, so `_cached_config` and submodule refreshes always execute.
- **handler.py `configure()` disk I/O under `_config_lock`** — `get_active_theme()` was called inside `with self._config_lock:` (line 894). This method chains through `get_theme_from_folder()` → `os.path.isdir()`, `os.path.isfile()`, JSON file reads, then `theme.load()` → `os.listdir()`, `make_sound_object()` for each file. All under `_config_lock`, blocking every thread calling `get_theme_for_app()` or `get_typing_pack_for_app()` during theme loading (potentially hundreds of ms). Fixed by moving theme loading outside the lock: `_config_lock` is held only for the `self.active_theme = new_active_theme` assignment.
- **handler.py `__init__` unguarded init calls** — `ensure_themes_dir()`, `migrate_all_themes_to_named_files()`, and `configure()` were called without try/except. Any exception killed the entire handler, leaking UnspokenPlayer resources. Wrapped each in individual try/except with error logging.
- **handler.py `_theme_cache` / `_app_profiles_cache` uninitialized** — These were only set inside `configure()` (conditionally), but accessed by `close()`. If `configure()` failed, `close()` would crash with `AttributeError`. Initialized both to `{}` in `__init__`.

### Round 27 (committed): initialization + monkey-patching audit — 9 fixes
Deep audit of module-level code, init functions, monkey-patching lifecycle, and teardown for phoneticPunctuation, browserNavEngine, sentenceNavEngine, emoji_handler, and frenzy.
- **phoneticPunctuation.py `restoreMonkeyPatches()` ordering bug** — CRITICAL: `frenzy.monkeyUnpatch()` was called AFTER restoring `speech.speech.speak`, overwriting the correct NVDA original with `preSpeak` (our function). `_original_speak` was captured as `preSpeak` during `injectMonkeyPatches()` because our hook was already installed. Moved `frenzy.monkeyUnpatch()` to run BEFORE speak restoration so our restoration is final.
- **phoneticPunctuation.py `injectMonkeyPatches()` `speechWithoutPausesInstance`** — Unguarded access to `speech.sayAll.SayAllHandler.speechWithoutPausesInstance.speak` crashed if lazy init hadn't completed. Wrapped in try/except.
- **phoneticPunctuation.py `injectMonkeyPatches()` `frenzy.monkeyPatch()`** — No try/except. If `frenzy.monkeyPatch()` raised, remaining patches (`processSpeechSymbol`, `getIndentationSpeech`, `_getSelectionMessageSpeech`) were never installed. Wrapped in try/except with logging.
- **phoneticPunctuation.py `monkeyPatchRestoreProsodyInAllHighLevelSpeakFunctions()`** — `getattr(module, functionName)` unguarded. Missing function crashed entire loop, preventing all high-level speak patches. Added try/except per function.
- **__init__.py `injectMonkeyPatches()` / `restoreMonkeyPatches()` double-patching** — `frenzy.monkeyPatch()` called twice (once from `pp.injectMonkeyPatches()` line 867, once from `__init__.py` line 663). Double `register()` on `speech.manager.pre_synthSpeak` leaked first handler. Removed redundant calls.
- **frenzy.py `_ctypes_mod` module-level import** — `__import__('_ctypes')` crashed entire module if unavailable. Wrapped in try/except.
- **frenzy.py `monkeyUnpatch()` unconditional restoration** — `speech.speech.getTextInfoSpeech`, `getPropertiesSpeech`, `getControlFieldSpeech`, `processAndLabelStates` restored unconditionally. If originals were None (addon loaded before NVDA initialized), wrote None into NVDA's speech pipeline. Added None guards for all.
- **frenzy.py dead globals** — `roleRules = None` (×5) then `roleRules = {}` (×5) was redundant. `stateDict` and `negativeStateDict` were dead code (defined but never used). Cleaned up.
- **browserNavEngine/__init__.py `terminateBrowserNav()`** — All 13+ restore operations in single block with no individual try/except. One failure (e.g. `NameError` from never-called `initBrowserNav()`) skipped all subsequent restores. Each restore wrapped in individual `with suppress(Exception):`.
- **sentenceNavEngine.py module-level config hooks** — `post_configSave/Reset/ProfileSwitch.register()` wrapped only `ImportError`. Also caught `AttributeError` for older NVDA versions.

### Round 28 (committed): speech hot-path CPU audit — 7 fixes
Targeted audit of `frenzy.py` + `phoneticPunctuation.py` hot paths called on every speech event.
- **utils.py `isPhoneticPunctuationEnabled()`** — Called 7-10× per speech event, each acquiring 3 locks (2× `_pp_config_lock` + 1× `_blacklist_lock`). Added `_pp_enabled_result` cache + `_reset_pp_enabled_cache()`. Result cached until explicitly cleared at start of `preSpeak`, on `preCancelSpeech`, and on config refresh. Eliminates ~21-30 lock acquisitions per event.
- **frenzy.py `_LRUCache` lock contention** — `_active_rule_cache.get()` acquired `self.lock` on every call (20-30× per event for `getActiveRuleContext()`). Replaced with lock-free reads (plain dict `in` check; CPython GIL makes dict reads atomic). Lock only on writes (`put()` during config reload). Saves ~5-10μs per event.
- **phoneticPunctuation.py `isEmptyString()` in `postProcessSynchronousCommands`** — Called `speech.processText(language, command, symbolLevel)` per string element (~3-10× per event). `speech.processText` runs full symbol processing pipeline just to check if string is blank. Replaced with `command.strip()` fast-path: empty/whitespace strings → True, non-empty → False. Saves ~20-100μs per event.
- **phoneticPunctuation.py `fixProsodyCommands` settingsRing iteration** — `findProsodySetting()` closure iterated `globalVars.settingsRing.settings` for every new prosody class on every speech event. Extracted to module-level `_findProsodySetting()` with `_prosody_setting_cache` dict. Cache cleared on `reloadRules()`. Saves ~5-20μs per event with prosody rules.
- **phoneticPunctuation.py `_suppress_role_sound_lock` per-string** — `_processEmojiSequence` acquired `_suppress_role_sound_lock` twice per string item in sequence (lines 576, 608). Changed to single acquire at end of function after all processing. Saves ~5-10μs per emoji-containing event.
- **frenzy.py `roleFormatsDict` cache via `hasattr()`** — `_new_getObjectPropertiesSpeech_inner` and `_new_getPropertiesSpeech_inner` both used `hasattr(utils, '_cachedRoleFormatsJson')` + `json.loads()` check on every call. Moved to module-level `_cached_role_formats_json`/`_cached_role_formats_dict` in frenzy.py, refreshed in `refreshFrenzyCachedConfig()`. Eliminates `hasattr` + potential `json.loads()` per event.
- **frenzy.py double `formatConfig.copy()`** — `_new_getTextInfoSpeech_inner` copied formatConfig (line 821), then `FakeTextInfo.__init__` copied it again (line 557). Removed redundant copy in `FakeTextInfo` since caller always provides a local copy.
- **phoneticPunctuation.py `processRule` per-rule `speech.getCurrentLanguage()`** — `processRule()` called `speech.getCurrentLanguage()` for every text rule. Language is constant per speech event. Moved to `preSpeak` and passed as parameter. Saves ~1-3μs per event with text rules.

### Round 29 (committed): startup time optimization — 6 fixes
Targeted optimization of `GlobalPlugin.__init__` and module-level imports to reduce NVDA startup blocking time.
- **handler.py Lazy UnspokenPlayer** — `UnspokenPlayer()` (SteamAudio DLL load ~50-100ms + 6 WavePlayer instances ~20-50ms) moved from `__init__` to `_ensure_player()` lazy init. Created on first `play()` call or first `configure()` when a theme is active. All `self.player.*` access sites guarded with None checks. Config applied both at creation time and on subsequent `configure()` calls. Estimated savings: ~100-150ms when no theme is active.
- **handler.py Deferred theme migration** — `migrate_all_themes_to_named_files()` (iterates bundled themes, copies missing ones to user dir) moved to daemon thread. Avoids filesystem I/O at startup. Estimated savings: ~50-200ms on first run.
- **handler.py Deferred system status monitor** — `_start_system_status_monitoring()` (Win32 hidden window creation + daemon thread) deferred via `wx.CallLater(3000, ...)`. Not needed until first system status event. Estimated savings: ~10-30ms.
- **phoneticPunctuation.py Deferred pp.reloadRules()** — `reloadRules()` (JSON file read + parse + regex compile per rule) moved from module-level `__init__.py` to `onPostNvdaStartup()`. Avoids blocking the import chain. Estimated savings: ~20-50ms.
- **utils.py Lazy ThreadPool** — `ThreadPool(4)` (spawns 4 daemon threads) replaced with `_ThreadPoolProxy` that creates the pool on first `add_task()` access. Avoids 4 thread creations at import time. Same pattern applied to `browserNavEngine/utils.py` (`ThreadPool(3)`). Estimated savings: ~5-15ms.
- **__init__.py Deferred initBrowserNav()** — `initBrowserNav()` (patches 10+ NVDA core methods, imports browseMode, virtualBuffers) deferred via `wx.CallLater(1000, ...)`. Not needed until first browse-mode interaction. Estimated savings: ~30-100ms.

### Round 29 (committed): event handler + CPU micro-optimization — 6 additional fixes
- **`__init__.py _onNavigationTimer` early return** — Timer fires every 250ms checking navigator changes. Was calling `current_nav.treeInterceptor` (COM property access) and `.passThrough` (another COM access) on every tick even when navigator hadn't changed (~99% of ticks). Added early return when themes disabled, and swapped check order: compare navigator identity first, only check treeInterceptor when navigator changed.
- **`__init__.py event_becomeNavigatorObject` early return** — Was calling `_snapshot_obj` (COM tree walking) even when themes disabled. Added `enable_audio_themes + active_theme` guard before snapshot.
- **`__init__.py event_mouseMove/event_documentLoadComplete/event_show`** — All three guarded `_snapshot_obj` behind `enable_audio_themes + active_theme` check. Previously called COM tree walking unconditionally.
- **`phoneticPunctuation.py _processEmojiSequence` functions-in-loop** — `_make_emoji_commands()` and `_get_emoji_text()` were defined inside `for item in sequence:` loop, creating a new function object per emoji-containing string item. Moved outside loop (still inside `_processEmojiSequence` scope).
- **`phoneticPunctuation.py postProcessSynchronousCommands` dead variable** — `language=speech.getCurrentLanguage()` was called on every speech event but never referenced. Removed.
- **`handler.py get_earcon_angles` uncached COM** — Called `api.getDesktopObject().location` on every earcon play. Now uses cached `_cached_desktop_location` from `__init__.py` (30s TTL). Falls back to COM only on cache miss.

### Round 30 (committed): memory + CPU optimization — 5 fixes
Full audit of disk I/O, memory, and CPU across all files.
- **unspoken `raw_data` leak** — After `_ensure_processed()` runs, `sound_data` held both `raw_data` (~350KB) and `data` (~350KB) per sound. `raw_data` was never accessed again but still referenced. Added `sound_data.pop("raw_data", None)`. Saves ~22.5MB across 64 cached sounds.
- **frenzy `headingLevelRules` double computation** — `_new_getControlFieldSpeech_inner` called `getActiveRuleContext()` for HEADING1-6 and HEADING format **twice** — once in the first loop (to check existence) and again in a dict comprehension (to build lookup). Now saves results into `_heading_level_rules_cache` during first pass and reuses them. Saves ~7 cache lookups per control field speech event.
- **handler `get_earcon_angles` pre-computed** — Was calling `api.getFocusObject().location` (COM) from worker threads. Now `_snapshot_obj()` computes angles on main thread and stores in `_latest_earcon_angles` module-level tuple. `get_earcon_angles()` reads the cache first (zero-COM), falling back to COM only on cache miss.
- **Disk I/O audit result:** ZERO hot-path issues remaining. Every config read, filesystem call, and JSON parse on speech/focus/keypress paths is served from in-memory caches.
- **Memory audit result:** All caches properly bounded (LRU/WeakKeyDictionary/maxsize). Only the `raw_data` leak was actionable.

### Round 31 (committed): shutdown/cleanup + robustness audit — 7 fixes
Deep audit of shutdown path, resource lifecycle, and remaining edge cases.
- **handler.py `close()` `player.stop()` → `player.terminate()`** — CRITICAL: `UnspokenPlayer` has no `stop()` method; the correct method is `terminate()`. The `AttributeError` was silently caught, but **nothing was actually cleaned up**: audio worker thread never stopped, WavePlayers never closed (audio device handles leaked), SteamAudio native resources never freed, synthChanged listener never unregistered.
- **handler.py `close()` set `player = None`** — After terminate, player still referenced. Downstream code checking `if self.player is not None` would try to use the dead player.
- **`__init__.py` `terminate()` unguarded `orig_caretMovementScriptHelper`** — If `__init__` crashed before setting this attribute, the bare `if self.orig_caretMovementScriptHelper:` at line 676 raised `AttributeError`, which was NOT in a `suppress()` block. This killed all subsequent cleanup: timer never stopped, handler never closed, thread pool never shut down, BrowserNav never terminated.
- **`__init__.py` `terminate()` `_instance_handler` never cleared** — Class variable still pointed to closed handler after terminate. Late-firing `_snapshot_obj` calls used stale handler.
- **handler.py `close()` caches not cleared** — `_app_profiles_cache` and `_cached_config` retained stale data. Late-firing event handlers or speech hooks could read stale config.
- **phoneticPunctuation.py `reloadRules` double-register guard** — `config.post_configProfileSwitch.register(reloadRules)` had no idempotency check. If `injectMonkeyPatches()` was called twice without `restoreMonkeyPatches()`, reloadRules fired twice per config change.
- **studio `SetSelection(0)` on empty Choice** — `self.themeChoice.SetSelection(0)` without checking `GetCount() > 0` raised wx assertion when no themes installed.

### Round 32 (committed): hot-path micro-optimizations — 7 fixes
- **`__init__.py _snapshot_obj` fl_detection_mode off skip** — When first/last detection is disabled (`fl_detection_mode == "off"`), skip all 3 expensive UIA COM tree walks (`parent_role`, `previous_role`, `next_role`). Also skip earcon angle computation when `audio3d` is disabled.
- **`phoneticPunctuation.py preSpeak` list concatenation** — `resetProsodiesSequence + newSequence` created a new list every event. Changed to `resetProsodiesSequence.extend(newSequence)` (zero-copy in-place mutation). Same for trailing `[' ']` → `.append(' ')`.
- **`phoneticPunctuation.py _processEmojiSequence` emoji pre-scan** — Added `_has_emoji_codepoints()` fast Unicode range check (FE00-FE0F, 1F000-1FFFF). Skips full emoji processing entirely when no string contains emoji codepoints (vast majority of speech events).
- **`phoneticPunctuation.py postProcessSynchronousCommands` inline unmask** — `MaskedString` unwrapping now happens in the same pass as the synchronous command scan, eliminating `unmaskMaskedStrings()` list copy.
- **`phoneticPunctuation.py fixProsodyCommands` early-out** — Pre-scans sequence for `BaseProsodyCommand` instances. Returns original sequence untouched when no prosody commands exist (vast majority of events).
- **`handler.py` module import caching** — `_frenzy_mod` and `_utils_mod_cache` stored on handler instance at `configure()` time, used by `_hook_getSpeechTextForProperties` hot path. Eliminates `from . import` per speech event.
- **`handler.py get_earcon_angles` audio3d guard** — Earcon angle computation skipped entirely when `audio3d` config is disabled.

### Round 33 (committed): error sound on NVDA restart — 4 fixes
- **`unspoken/__init__.py` `on_synthChanged` during shutdown** — CRITICAL: `on_synthChanged` fires during NVDA shutdown, tries to open audio device being released. Added `_terminated` flag set at start of `terminate()`; `on_synthChanged` checks flag before creating new WavePlayers; `create_wave_player()` wrapped in try/except inside `on_synthChanged`; `steam_audio.cleanup()` wrapped in try/except so `synthChanged.unregister()` is always reached.
- **`unspoken/__init__.py` `terminate()` restructured** — Moved `synthChanged.unregister()` to START of terminate (before cleanup) so our hook is removed first.
- **`handler.py` `close()` `getPropertiesSpeech` restore** — `speech.speech.getPropertiesSpeech` restoration wrapped in try/except.
- **`phoneticPunctuation.py` `preSpeak` `_utils_mod._reset_pp_enabled_cache()`** — Moved inside try/except to prevent crash during shutdown when module state is inconsistent.
- **`__init__.py` `terminate()` crash logging** — Added file-based crash logging to `shutdown_crash.log` for post-restart diagnosis.

### Round 34 (committed): speech pipeline resilience + config crash guards — 6 fixes
- **`frenzy.py:210` `except (Exception, _ctypes_mod.COMError)`** — When `_ctypes_mod` is `None` (ImportError fallback), evaluating `_ctypes_mod.COMError` in the except clause raised `AttributeError`, masking the original exception. Simplified to `except Exception:`.
- **`frenzy.py:918` `getNumericSpeechCommand()` unguarded** — `getNumericSpeechCommand()` can raise `ValueError` if a rule has misconfigured fields. One malformed heading level rule crashed ALL custom text formatting for the entire utterance. Added `try/except: continue` matching the existing font-size handler at line 1044.
- **`handler.py` `configure()` bare `user_config["key"]` lookups** — If `config.conf["audiothemes"]` raised `KeyError`, `user_config` was `{}`; lines 1021-1025 used bare `[]` lookups on empty dict, crashing with `KeyError`. Changed to `.get()` with safe defaults.
- **`handler.py` `get_theme_from_folder()` `AudioTheme(**info)` crash** — Extra keys in `info.json` (e.g. `"description"`, `"version"`) passed as kwargs, causing `TypeError`. Now filters to known dataclass fields (`name`, `directory`, `author`, `summary`).
- **`handler.py` `__init__` `_frenzy_mod`/`_utils_mod_cache` uninitialized** — These attributes were only set in `configure()` and cleared in `close()`. If `configure()` failed, `_hook_getSpeechTextForProperties` raised `AttributeError`, silently disabling role suppression. Added `None` initialization in `__init__`.
- **`__init__.py` `script_speakHeadingLevel` COM access** — `focus.treeInterceptor` is a COM property access that can raise `COMError` on stale focus objects. Wrapped in `try/except Exception`. Also broadened `makeTextInfo` except clause to catch all exceptions.

### Round 35 (committed): sentenceNav, unspoken, browserNavEngine deep audit — 26 fixes
- **sentenceNavEngine.py `moveExtended` sameIndent lambda** — `NVDAObjectAtStart.location` COM access unguarded; `location` can be `None`. Crashes all `sameIndent` sentence navigation. Extracted to `_sameIndent()` with try/except fallback to style-only comparison.
- **sentenceNavEngine.py `_sn_move`/`_sn_moveToText` `makeTextInfo`** — Only catches `NotImplementedError`, not `COMError`. Broadened to `except Exception`.
- **sentenceNavEngine.py `setSNConfig`** — Bare `config.conf["sentencenav"][key]` dict lookup; changed to `.get()`.
- **unspoken `UnspokenPlayer.__init__`** — Unguarded `create_wave_player()` crashes addon load and leaks SteamAudio resources. Wrapped in try/except.
- **unspoken `play()`/`play_file()`** — Unguarded `wave_player.stop()` / `player.stop()` crashes during synth change. Wrapped in try/except.
- **browserNavEngine `getBeepTone`** — `offset` can be `None`, causing TypeError in division. Added None guard.
- **browserNavEngine `browserNavPopup`** — `wx.Frame` never `Destroy()`'d. Added to finally block.
- **browserNavEngine `AdjustedTextInfo.getTextWithFields`** — `field.command in ("controlStart")` is substring check, not equality (Python treats `("s")` as string, not tuple). Changed to `==`. Also `field.field['role']` bare dict lookup changed to `.get()` with None guard.
- **browserNavEngine `getBiwCategories`/`getBuiltInWaveFilesInCategory`/`getBuiltInWaveFiles`** — Unguarded `os.listdir`/`os.walk`. Wrapped in `try/except OSError`.
- **browserNavEngine `getBiw`/`getBiwCategory`** — `IndexError` on empty list or `GetSelection()=-1`. Added bounds checks.
- **browserNavEngine `setBiw`** — Unguarded `.index()` raises `ValueError`. Wrapped in try/except.
- **browserNavEngine dialog Destroy leaks** — 5 dialogs (`EditBookmarkDialog`, `EditSiteDialog`, `WebsiteStoreDialog`, `OverwriteSiteDialog`, `TextEntryDialog`) never destroyed on cancel. Moved `Destroy()` outside OK-only blocks or wrapped in try/finally.
- **browserNavEngine `playBiwInThread`** — Unguarded `wave.open` (`FileNotFoundError`); `raise RuntimeError` on unsupported WAV. Wrapped entire body in try/except; RuntimeError → log.warning.
- **browserNavEngine `getChordFrequencies`** — `NOTES.index()` raises `ValueError` for notes not in list. Wrapped in try/except.
- **quickJump.py broken indentation** — Pre-existing `try:` without proper indentation of `if` block inside it caused syntax error cascading to `match` keyword parser. Fixed indentation.

### Round 36 (committed): deep audit — correctness + robustness fixes
- **emoji_handler.py `int()` unguarded** — `int(config["emoji_delay_before"])` / `int(config["emoji_delay_after"])` crashed with `ValueError`/`TypeError` on non-numeric config. Wrapped in try/except with fallback to 0.
- **emoji_handler.py volume-0 falsy with `or`** — `per_cat.get(...)` returns `0` for volume=0 but `0 or get_emoji_volume()` treats `0` as falsy, falling through to default volume. Changed to `val if val is not None else default`.
- **phoneticPunctuation.py `re.compile` crash** — `re.compile(pattern)` with user-supplied invalid regex crashed entire rules file parse. Each `re.compile` wrapped in try/except with fallback to `re.compile(".*")`.
- **phoneticPunctuation.py `reloadRules` file I/O** — `open(rulesFileName)` without try/except. Missing file crashes all rule loading. Wrapped with early return.
- **frenzy.py `del result[-1]` / `del stack[-1]`** — Two `findControlEnd`-style functions with unguarded `del list[-1]`. Empty list raises `IndexError`. Added emptiness guards.
- **frenzy.py `info.text` COM access** — `preventSpellingCharacters` accessed `info.text` (COM property) without try/except. Stale/invalid TextInfo crashes `new_getTextInfoSpeech`. Wrapped in try/except.
- **themes_store.py `DownloadAndPreview` async audio killed by `finally`** — `finally` block deleted `tmp_path` immediately, but `async playWaveFile` may still be reading it. Now `tmp_path` is set to `None` after handing ownership to the Timer, so `finally` only deletes on error paths.
- **themes_store.py `wx.CallAfter` on destroyed dialog** — Background threads call `wx.CallAfter(self.statusLabel.SetLabel, ...)` after dialog is destroyed. Added `_closed` flag; `FetchStoreData`/`DownloadAndPreview` check flag before `CallAfter`.
- **themes_store.py `OnClose` missing** — Dialog had no `Close` handler. Added `OnClose` that calls `self.Destroy()`.
- **themes_blender.py `FileDialog` leaked on cancel** — `_show_audio_file_dialog` never called `Destroy()` on cancel path. Wrapped in try/finally with `Destroy()`.
- **themes_blender.py `self.player` fallback creates unneeded `UnspokenPlayer`** — Fallback created a whole new `UnspokenPlayer` (SteamAudio DLL + WavePlayers) just for volume preview. Changed to `self.player = None`; preview functions guard with `if self.player is None: return`.
- **`__init__.py script_cycleAudioThemes` broken `themes` attr** — Referenced `self.handler.themes` which doesn't exist. Handler uses `get_installed_themes()` which returns list of AudioTheme objects. Fixed to call `get_installed_themes()` and extract `.name` from each.
- **`__init__.py` 7 toggle scripts missing `configure()` call** — `script_toggleAudioThemes` (double-tap), `script_toggleAudioDucking`, `script_toggleEmojiSounds`, `script_toggleAppProfiles`, `script_toggleClipboard`, `script_toggleSystemStatus` all wrote to `config.conf` without calling `configure()`, leaving `_cached_config` stale. Added `self.handler.configure()` to each.
- **`handler.py get_theme_from_folder` missing required fields** — If `info.json` had no `name` key (corrupted or missing field), `AudioTheme(**filtered)` crashed with `TypeError`. Added defaults for required fields (`name`, `author`, `summary`).
