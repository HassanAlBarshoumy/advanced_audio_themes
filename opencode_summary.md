## Goal
Harden per‑app sound suppression, fix `blacklisted_roles` config validation, add auto‑creation of missing theme resources (info.json, sound files), support 24‑bit WAV, and eliminate the multi‑second freeze when opening the settings panel.

## Constraints & Preferences
- Must work without external Python packages (only Win32 API via ctypes).
- Compatible with Python 3.13 (NVDA 2026.1.1).
- UI language: Arabic; codebase uses `_()` for translations.
- Non‑destructive: preserve cached buffers, reverb, 3D spatialization paths.
- `speech.commands.BeepCommand` (indentation tones) must NOT be ducked.
- `blacklisted_roles` saved in config must never trigger `VdtTypeError` – use `string` spec with JSON instead of `int_list`.
- Any folder under `audio-themes/` without `info.json` must be auto‑discovered.
- Sound files with 24‑bit sample width (sample_width=3) must be accepted.
- ZIP files inside `audio-themes/` must be silently skipped.
- Missing sound files for staple UI roles (e.g. `listitem`, `first`, `last`) should be auto‑created by duplicating an existing sound from the same theme.

## Progress
### Done
- **v9.14 — suppression root cause + fixes**: stale `foreground_app` in snapshot, `from . import __init__` resolving to `method-wrapper` on worker threads, missing `log` import. Fixed via `_handler_ref` cache, `_current_app_name` direct read, `from logHandler import log`.
- **v9.15→v9.17 — blacklisted_roles VdtTypeError**: final fix uses `"string(default='[19]')"` spec, stores as JSON string, `_get_blacklisted_roles()` parses with `json.loads()` and handles both `str`/`list` legacy values.
- **v9.17 — auto‑create info.json**: `get_theme_from_folder()` writes `info.json` for folders that lack it.
- **v9.18 — skip non‑directories + 24‑bit WAV**: `os.path.isdir()` gate for ZIP files; `sample_width == 3` block reads 3‑byte little‑endian samples with sign‑extension.
- **v9.19 — auto‑create missing staple sounds + controlTypes.Role.EDIT→EDITABLETEXT fix**: `AudioTheme._auto_create_missing_sounds()` copies existing theme files for 10 staple roles. Startup crash fixed by using correct `EDITABLETEXT`.
- **v9.19 — lazy loading for Rules + QuickJump tabs**: replaced synchronous construction with `wx.Panel` placeholders; page‑swap on first tab selection. Added `_suppressPreview` flag and `_installed_themes_cache`.
- **v9.20 — lazy loading for Speech Order tab**: 130+ `wx.Choice` (combobox) controls moved from eager `setupSpeechOrderPage()` to deferred `_createRoleGrid()`. Tab creates only header/controls eagerly (~10ms); per‑role grid (~130 comboboxes) created on first tab selection via `_loadSpeechOrderPage()`. Guards added in `onSave`, `_initialize_at_state`, `onRoleSearch`. Result: settings panel opens instantly.

### In Progress
- None

### Blocked
- None

## Key Decisions
- **`string` spec over `int_list` for `blacklisted_roles`**: configobj’s `int_list` validator fails on the default string `"[19]"` stored by configobj’s own spec parser. Storing as JSON string bypasses NVDA’s config validation entirely.
- **`os.path.isdir()` gate before auto‑creating `info.json`**: prevents crash when `os.listdir()` returns files (especially `.zip` archives) inside `THEMES_DIR`.
- **24‑bit WAV fallback uses manual struct unpack**: Python’s `wave` module does not support `sample_width == 3` natively.
- **Auto‑create missing sounds by file‑level `shutil.copy2()`**: simplest approach, preserves source format, no external dependency.
- **Page‑swap lazy loading for Rules/QuickJump**: delete placeholder page, insert real dialog at the same notebook index, then `SetSelection` to that index via `wx.CallAfter`.
- **In‑place lazy loading for Speech Order**: instead of page‑swap, refactored `setupSpeechOrderPage` to create only fast controls eagerly; heavy grid deferred to `_createRoleGrid()` called on first tab select via `_loadSpeechOrderPage()`.

## Relevant Files
- `globalPlugins/audiothemes/settings.py:577-630` — `setupSpeechOrderPage()` now creates only eager controls (header, announce format, search box).
- `globalPlugins/audiothemes/settings.py:690-717` — `_createRoleGrid()` creates the per‑role 130‑combobox grid (deferred).
- `globalPlugins/audiothemes/settings.py:1198-1262` — `_onLazyLoadTab`, `_loadSpeechOrderPage`, `_initSpeechOrderFormats`.
- `globalPlugins/audiothemes/settings.py:1062-1068` — guarded per‑role init loop in `_initialize_at_state`.
- `globalPlugins/audiothemes/settings.py:1318-1327` — guarded per‑role save loop in `onSave`.
- `globalPlugins/audiothemes/handler.py:222-245` — `_STAPLE_ROLES` tuple and `_auto_create_missing_sounds()`.
- `globalPlugins/audiothemes/handler.py:436-438` — `AudioThemesHandler` class with `_installed_themes_cache`.
- `globalPlugins/audiothemes/handler.py:841-855` — cached `get_installed_themes()` and `_invalidate_themes_cache()`.
- `globalPlugins/audiothemes/unspoken/__init__.py:432-445` — 24‑bit WAV decoder.
