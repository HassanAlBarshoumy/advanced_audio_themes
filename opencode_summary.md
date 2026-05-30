## Goal
Complete and stabilize the advanced audio themes NVDA addon: fix audio routing, mono mode, 3D spatialization, translations, and resolve runtime errors.

## Constraints & Preferences
- Must work without external Python packages (use only Win32 API via ctypes).
- All file changes must compile with Python 3.13 (NVDA 2026.1.1).
- User interface language: Arabic, codebase uses `_()` for translations.
- All fixes must be non‑destructive: preserve cached buffers, reverb, and 3D spatialization paths.

## Progress
### Done
- **3D spatialization for earcon/speech‑rule sounds (NVDA+Alt+P)**: `PpBeepCommand.run()` and `PpWaveFileCommand.run()` in `commands.py` now use `handler.get_earcon_angles()` to compute focus‑based 3D position, applied both in the reverb path (Steam Audio `process_sound`) and the fallback path (direct Steam Audio processing before `ensure_mono`). Reverb path angles changed from hardcoded `(0,0)` to actual focus angles.
- **New `handler.get_earcon_angles()`**: Computes `angle_x`/`angle_y` from current focus object location using the same formula as `UnspokenPlayer.play()` in `unspoken/__init__.py` (center of object, mapped to ±90°).
- **Translations 100%**: all 4 locales (en, ar, ru, zh_CN) now match at 598 strings each; no untranslated or extra strings.
- **English `.po` updated**: 17 missing source strings added (`Check for &Updates...`, `Move to next phrase.`, `Speak current sentence.`, `Unknown`, etc.).
- **Arabic translation**: `Smooth 3D Panning (Glide effect for moving objects)` translated; duplicate `&About` entry removed from `ar/nvda.po`.
- **Russian/Chinese translations**: 3 missing strings added (`(Plays 3D sound...)`, `About Typing Sound Pack`, `Unknown`).
- **`.mo` binary format fix**: regenerated with correct 7-field header (was missing `hash_size`/`hash_offset`) and `\n` → actual newline 0x0A in header metadata.
- **Git push**: all changes committed (`5c13b5c`) and pushed to `origin/master`.
- **FFmpeg slowness fix**: native decoders (OGG, FLAC, MP3, WAV) tried first, FFmpeg only as fallback.
- **browserNavEngine crash**: `obj.parent` wrapped in `try/except` inside `getIA2DocumentInThread()`.
- **3D + Mono conflict**: `is_mono` forced to `False` when `audio3d` is enabled (3D overrides mono).
- **Mono downmix**: stereo files properly downmixed to mono before playback in both `play()` and `play_file()`.
- **SmoothPanning**: re‑enabled with 30° threshold.
- **FLAC native decoder** via `libFLAC.dll`.
- **Audio filters**: Noise Gate + Bass Boost with settings UI.
- **Batch import folder** in Studio with automatic filename‑to‑role mapping.
- **Microphone recording removed**: button, handler, and `mic_recorder.py` deleted.
- **`frenzy.py` `UnboundLocalError` fixed**: `import controlTypes` at function top.
- **`themes_store.py` cleanup**: `PermissionError` on temp file deletion suppressed.
- **`event_gainFocus`**: `UnboundLocalError` silently caught.
- **Bundled sounds removed**: `.wav` files in `Themes/` and `typingSounds/` deleted.
- **Mono mode for earcon/BrowserNav sounds**: `commands.py`, `quickJump.py`, `beeper.py` now call shared `ensure_mono()` from `utils.py`.

### In Progress
- None

### Blocked
- **NVDA Add‑on Store submission**: PR [#9504](https://github.com/nvaccess/addon-datastore/pull/9504) (add submitter) still open; waiting for **seanbudd** review.
- **VisionAssistantPro CI failure**: PRs merged but `build` workflow fails (from fork, lacks secrets); v6.1.0 not yet published.

## Key Decisions
- **3D overrides mono**: HRTF spatialization needs stereo output; mono mode only applies when 3D is off.
- **Ensure non‑destructive mono mix**: original channel count preserved in cache; downmix only at playback time via `ensure_mono()` (returns new bytes, never mutates cache).
- **Reverb paths unchanged**: already feed mono float samples into Steam Audio; reapplying `ensure_mono()` would be redundant.
- **Earcon 3D via handler, not UnspokenPlayer directly**: `commands.py` already imports `steam_audio` for reverb; adding `handler.get_earcon_angles()` avoids circular imports and duplicates no positioning code.
- **Position from current focus object**: same formula as `UnspokenPlayer.play()` — maps screen coordinates to `angle_x`/`angle_y` using desktop bounds and `_display_width`/`_display_height_min`/`_display_height_magnitude`.
- **Reverb path also gets positional angles**: changing hardcoded `(0,0)` to actual focus‑derived angles so reverb‑enhanced earcons also follow spatial position.
- **Cached reverb sounds do not include position**: cache key omits angles to avoid cache bloat; the first playback caches at the current position, subsequent identical sounds reuse the cached (potentially different position) version. Acceptable given 50‑entry LRU cache.

## Relevant Files
- `globalPlugins/audiothemes/handler.py:605-628`: `get_earcon_angles()` — focus‑based angle calculation.
- `globalPlugins/audiothemes/commands.py:77-163`: `PpBeepCommand.run()` — 3D processing path added before `ensure_mono`.
- `globalPlugins/audiothemes/commands.py:273-356`: `PpWaveFileCommand.run()` — 3D processing path added before `ensure_mono`.
- `globalPlugins/audiothemes/unspoken/__init__.py`: `play()` lines 565–612 — reference formula for angle calculation.
- `globalPlugins/audiothemes/utils.py`: `ensure_mono()` — shared downmix function; no changes needed.
- `locale/*/LC_MESSAGES/nvda.po` and `.mo`: all 4 locales 598 strings, fully translated, correctly compiled.
- `globalPlugins/audiothemes/browserNavEngine/beeper.py`: lines 136, 171 — existing pattern for accessing `GlobalPlugin._instance_handler`.
- `nvaccess/addon-datastore` issues/PRs: [#9503](https://github.com/nvaccess/addon-datastore/issues/9503) (submission), [#9504](https://github.com/nvaccess/addon-datastore/pull/9504) (PR, blocked on seanbudd).
