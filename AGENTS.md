# Advanced Audio Themes - AGENTS.md

## Architecture

### Hot-path call chain (per focus event, ~every 100ms)
```
event_gainFocus (__init__.py:1100)
  → _unspoken_play_role (__init__.py:1114)       — no config.conf reads
    → handler.play()                              — uses self._cached_config
      → play_theme_sound                          — uses self._cached_config
      → play_typing_sound                         — uses self._cached_config
      → _play_system_sound                        — uses self._cached_config
      → play_clipboard_sound                      — uses self._cached_config
        → get_theme_for_app                       — uses self._cached_config
        → get_typing_pack_for_app                 — uses self._cached_config
        → player.play(obj_info, sound_data)       — uses self._cached_config
          → player._ensure_processed(sound_data)  — uses cached player attrs
          → player._compute_volume()              — uses self._cached_config
          → player.make_sound_object(path)        — uses self._cached_config
```

### Config caching strategy
- `handler.configure()` is registered to `post_configSave`, `post_configReset`, `post_configProfileSwitch`, `audiotheme_changed` — so `_cached_config` is always fresh
- The cached dict ref is shared with `self.player._cached_config` to avoid any `config.conf` reads in hot paths
- Processing-effect bools/params are additionally stored as `self.player._*` attributes so `_ensure_processed` doesn't even need dict lookups

### All refactors completed (18 items)
1. **audioop → pure-Python fallback** (`frenzy.py:11-14`): `try/except ImportError` with `array('h'), array('i'), array('b')` loops
2. **Module-level constants** (`emoji_handler.py`): `_EMOJI_RANGES`, `_CATEGORY_CONFIG_KEYS` promoted from local vars
3. **Unified `_is_app_disabled_for_category`** (`handler.py:920-927`): replaced 4 duplicate patterns
4. **Dead code removed**: `_fl_config` fallbacks, OGG early return, `is_ogg` dead paths
5. **24-bit ducking** (`frenzy.py:369-382`): `sample_width == 3` support in `apply_ducking_to_pcm`
6. **Thread safety**: `_typing_player_lock`, `_last_played_lock` added
7. **Inline imports lifted**: `STATE_OFFSET`, `is_emoji_suppress_role_flag_set`, `_frenzy` alias, `_audio_filters` alias
8. **log.debug guards**: both hot-path f-string evals wrapped in `isEnabledFor(log.DEBUG)`
9. **Debounce attrs initialized**: `_last_typing_time = 0.0`, `_last_typing_vk = 0` — removes `hasattr` check
10. **NameError fix**: `foreground_app` → `getattr(self, '_current_app_name', None)`
11. **Processing config on player**: `_trim_silence`, `_smart_volume`, `_smooth_envelope`, `_noise_gate`, `_bass_boost` and thresholds — set via configure(), used in `_ensure_processed()`
12. **`_fl_config` → `_cached_config`**: renamed, expanded with all hot-path keys, shared with `self.player._cached_config`
13. **`_cached_config` initialised in `__init__`** before `configure()` call; player ref set after dict build
14. **Circular import fixed**: `_frenzy`/`_audio_filters` imported inside function bodies (not module-level)
15. **Removed `hasattr`** in `play_typing_sound` (uses initialised attrs directly)
16. **All hot-path handler methods** use `_cached_config`: `play_theme_sound`, `play_typing_sound`, `_play_system_sound`, `play_clipboard_sound`, `get_theme_for_app`, `get_typing_pack_for_app`
17. **All hot-path player methods** use `_cached_config`: `play()`, `play_file()`, `_compute_volume()`, `make_sound_object()`
18. **`_ensure_processed`** uses cached player attrs, no `config.conf` reads

### Remaining config.conf reads (all non-hot-path)
- `unspoken/__init__.py`: 13 reads, all in `__init__()` (one-time) and `on_synthChanged` (rare)
- `handler.py`: 15 reads, all in `configure()` (one-time) and config migration code
- `__init__.py`: many reads, all in toggle handlers and GUI code — not hot-path
