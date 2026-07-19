# Summary

## Objective
Complete a performance, disk I/O, thread‑safety, and memory audit of all files under `globalPlugins/audiothemes/` and fix every issue found.

## Important Instructions
- "لا تكسر اي وظيفة" — do not break any existing functionality.

## Status
All known issues fixed (rounds 1–11, 13A). No known remaining issues.

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

### Round 13A: AggregatedSection isinstance(dict) false negatives
- `frenzy.py:90-93`, `sentenceNavEngine.py:42-45`, `browserNavEngine/__init__.py:64-67` — removed `isinstance(src, dict)` guard that **silently rejected** `AggregatedSection` (which does not inherit from `dict`), leaving `_cached_doc_formatting` as `{}`.
  - **Result**: `_cached_doc_formatting` now stores the `AggregatedSection` directly, providing spec‑default fallback for keys like `detectFormatAfterCursor` and `reportLineIndentation`.
  - **Impact**: Fixed `KeyError: 'detectFormatAfterCursor'` in `FakeTextInfo.__init__` (line 546) and `KeyError: 'reportLineIndentation'` in `original_getTextInfoSpeech` (line 1123) — both caused by passing a bare plain‑dict `formatConfig` (from `Section.copy()` → `dict`) to NVDA natives that expect ConfigObj‑default resolution.
- `utils.py:179-180` — removed the same `isinstance(section, dict)` check in `refreshPpConfigCache()` so `_pp_config_cache` is populated from the `AggregatedSection` on first refresh instead of remaining empty until the first `KeyError` fallback in `getConfig()`.

## Files verified safe (no config.conf reads in hot paths)
- `settings.py`, `emoji_cldr_data.py`, `decoders/*.py`, `systemStatus.py`, `update_checker.py`, `studio/`, `phoneticPunctuationGui.py`
- All files in `globalPlugins/audiothemes/` now use `_cached_config` dicts or module-level caches for hot-path reads.

## No known remaining issues
