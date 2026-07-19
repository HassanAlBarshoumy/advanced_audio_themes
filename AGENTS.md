# Summary

## Objective
Complete a performance, disk I/O, thread‑safety, and memory audit of all files under `globalPlugins/audiothemes/` and fix every issue found.

## Important Instructions
- "لا تكسر اي وظيفة" — do not break any existing functionality.
- Every `.py` file in the addon has been examined.
- Three rounds of fixes completed, all committed to `master`.

## Commit History

### Round 1 (`f590732`): config.conf → _cached_config in hot‑paths
- `__init__.py:181` — `_snapshot_obj()` uses `fl_cfg` cached dict.
- `handler.py:915-965` — added `audio_ducking_enabled`, `audio_ducking_volume`, `ducking_categories` to `_cached_config`.
- `frenzy.py:339-370` — `get_ducking_factor()` accepts optional `cached_config`.
- `unspoken/__init__.py:550,752` + `__init__.py:779` — pass `self._cached_config` to `get_ducking_factor()`.
- `unspoken/__init__.py:383-387` — `create_wave_player()` uses `.get()` fallback.

### Round 2 (`30c6afd`): module‑level I/O, leaky observers, unbounded caches
- `gen_map.py:125-129` — file write moved under `if __name__ == "__main__"`.
- `phoneticPunctuation.py:836` — `register(reloadRules)` + `unregister()` in `restoreMonkeyPatches()`.
- `handler.py:692-698` — `close()` unregisters all extensions and clears `_theme_cache`.
- `handler.py` — `_theme_cache` capped at 64 (LRU).
- `commands.py:30-47` — `_wave_player_pool` capped at 16 (LRU).
- `emoji_handler.py:358` — removed `@lru_cache` from `is_emoji_blacklisted()`.

### Round 3 (`e6a08bc`): remaining config reads, thread safety, queue cap
- `frenzy.py:94,118,1167,1210` — deduplicated `speak_roles`/`announceFormat` reads.
- `__init__.py:837,850-852,925,928,945,972,975` — keyDown/typedChar/progress‑bar use cached config.
- `handler.py:938-952` — added `typing_sounds_edit_only`, `clipboard_enabled`, `progress_pan_mode/range/pitch_shift`.
- `emoji_handler.py` — `_cached_emoji_config` + `refreshCachedConfig()`; 20 functions use cache.
- `phoneticPunctuation.py` — `_cached_speech_symbolLevel` + `refreshCachedConfig()`; `preSpeak()` and `new_processSpeechSymbol()` use it.
- `handler.py:987` — `configure()` calls `refreshCachedConfig()` for both modules.
- `steam_audio.py:332-354` — `_steam_audio_lock` (double‑checked locking) for `get_steam_audio()` / `cleanup_steam_audio()`.
- `unspoken/__init__.py:252` — `_audio_queue = Queue(maxsize=32)`; `_play_audio_data()` + `_play_typing_audio()` use `put_nowait()` with `except queue.Full: pass`.

### Post‑audit fixes (uncommitted)
- `browserNavEngine/beeper.py` — added `_spc_lock` around `skippedParagraphChime()` lazy init.
- `frenzy.py` — added `_frenzy_cached_config` + `refreshFrenzyCachedConfig()`; `new_getObjectPropertiesSpeech()`, `new_getPropertiesSpeech()`, and `_get_blacklisted_roles()` use it.
- `handler.py:configure()` — calls `refreshFrenzyCachedConfig()` and `refreshCommandsCachedConfig()`.
- `commands.py` — added `_commands_cached_config` + `refreshCommandsCachedConfig()`; `PpBeepCommand.run()` and `PpWaveFileCommand.run()` use it.
- `emoji_handler.py` — added `_raw` snapshot to `_cached_emoji_config`; `is_emoji_sound_category_enabled()`, `_get_json_config()`, and `is_category_enabled()` use it.

## Files verified safe
- `settings.py` — config reads only in user‑action handlers.
- `browserNavEngine/__init__.py` — `selectionHistory` is dead code; `updateURLLock` correct.
- `browserNavEngine/quickJump.py` — no `config.conf` under `@lru_cache`.
- `browserNavEngine/beeper.py` — JIT‑fix applied.
- `sentenceNavEngine.py` — no lock ordering issue.
- `emoji_cldr_data.py` — lazy load with lock, background thread.
- `decoders/*.py` — DLL loading at import is acceptable.
- `navLayer.py`, `clipboard.py`, `systemStatus.py`, `update_checker.py`, `studio/`, `phoneticPunctuationGui.py`.

## No known remaining issues
