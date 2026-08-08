# -*- coding: UTF-8 -*-
#A part of the Earcons and Speech Rules addon for NVDA
#Copyright (C) 2019-2022 Tony Malykh
#This file is covered by the GNU General Public License.
#See the file COPYING.txt for more details.

import array
import config
import os
from ctypes import create_string_buffer
import nvwave
import speech
import speech.commands
import threading
import time
import tones

from .utils import *

def _get_synchronous_player():
    return nvwave.WavePlayer(channels=2, samplesPerSec=int(tones.SAMPLE_RATE), bitsPerSample=16, outputDevice=_get_output_device(), wantDucking=True, purpose=nvwave.AudioPurpose.SOUNDS)

_pp_sync_player = None
_pp_player_lock = threading.Lock()

def _get_pp_player():
    global _pp_sync_player
    with _pp_player_lock:
        if _pp_sync_player is None:
            _pp_sync_player = _get_synchronous_player()
        return _pp_sync_player

# Global pool for WavePlayers keyed by (channels, sample_rate, ducking)
_wave_player_pool = {}
_wave_player_pool_lock = threading.Lock()

_DEFAULT_COMMANDS_CONFIG = {
    "audio3d": False,
    "reverb": False,
    "enable_ffmpeg": False,
    "output_mode": "stereo",
}

_commands_cached_config = dict(_DEFAULT_COMMANDS_CONFIG)

def refreshCommandsCachedConfig():
    global _commands_cached_config
    ac = config.conf.get("audiothemes", {})
    us = config.conf.get("unspoken", {})
    _commands_cached_config = {
        "audio3d": ac.get("audio3d", _DEFAULT_COMMANDS_CONFIG["audio3d"]),
        "reverb": us.get("Reverb", _DEFAULT_COMMANDS_CONFIG["reverb"]),
        "enable_ffmpeg": ac.get("enable_ffmpeg", _DEFAULT_COMMANDS_CONFIG["enable_ffmpeg"]),
        "output_mode": ac.get("output_mode", _DEFAULT_COMMANDS_CONFIG["output_mode"]),
    }

_WAVE_PLAYER_POOL_MAX = 16

_cached_output_device = None
def _get_output_device():
    global _cached_output_device
    if _cached_output_device is None:
        try:
            _cached_output_device = config.conf["speech"]["outputDevice"]
        except KeyError:
            _cached_output_device = config.conf["audio"]["outputDevice"]
    return _cached_output_device

def get_pooled_player(channels, sample_rate, ducking=False):
    # global _wave_player_pool
    key = (channels, sample_rate, ducking)
    with _wave_player_pool_lock:
        if key not in _wave_player_pool:
            od = _get_output_device()
            _wave_player_pool[key] = nvwave.WavePlayer(
                channels=channels,
                samplesPerSec=sample_rate,
                bitsPerSample=16,
                outputDevice=od,
                wantDucking=ducking,
                purpose=nvwave.AudioPurpose.SOUNDS
            )
            if len(_wave_player_pool) > _WAVE_PLAYER_POOL_MAX:
                evicted_key = next(iter(_wave_player_pool))
                evicted = _wave_player_pool.pop(evicted_key)
                try:
                    evicted.close()
                except Exception:
                    pass
        return _wave_player_pool[key]

# Cache for reverbed audio (capped at 50 entries to prevent unbounded growth)
_reverb_cache = {}
_reverb_cache_lock = threading.Lock()
_REVERB_CACHE_MAX = 50

def _apply_ducking(pcm_bytes, df):
    if df >= 1.0:
        return pcm_bytes
    try:
        from . import frenzy
        return frenzy.apply_ducking_to_pcm(pcm_bytes, df)
    except Exception as e:
        from logHandler import log
        log.debugWarning(f"_apply_ducking: frenzy fallback: {e}")
    arr = array.array('h', (int(x * df) for x in array.array('h', pcm_bytes)))
    return arr.tobytes()

def _reverb_cache_put(key, value):
    """Add to reverb cache with LRU eviction when exceeding max size."""
    with _reverb_cache_lock:
        if key in _reverb_cache:
            _reverb_cache.pop(key)
        elif len(_reverb_cache) >= _REVERB_CACHE_MAX:
            _reverb_cache.pop(next(iter(_reverb_cache)))
        _reverb_cache[key] = value

def _downmix_stereo_mono(arr):
    """Downmix a stereo int16 array to a mono float array (0.5 L + 0.5 R)."""
    n = len(arr) // 2
    return array.array('f', ((arr[i * 2] + arr[i * 2 + 1]) * (0.5 / 32767.0) for i in range(n)))

class PpSynchronousCommand(speech.commands.BaseCallbackCommand):
    def getDuration(self):
        raise NotImplementedError()
    def terminate(self):
        raise NotImplementedError()

class PpBeepCommand(PpSynchronousCommand):
    def __init__(self, hz, length, left=50, right=50):
        super().__init__()
        self.hz = hz
        self.length = length
        self.left = left
        self.right = right
        self.reverbPlayer = None

    def run(self):
        if is_sound_suppressed("earcons"):
            return
        try:
            self._runInner()
        except Exception as e:
            from logHandler import log
            log.debugWarning(f"PpBeepCommand.run() failed: {e}", exc_info=True)

    def _runInner(self):
        from NVDAHelper.localLib import generateBeep
        hz,length,left,right = self.hz, self.length, self.left, self.right

        # Apply audio ducking
        try:
            from . import frenzy
            df = frenzy.get_ducking_factor("earcons")
            if df < 1.0:
                left = int(left * df)
                right = int(right * df)
        except Exception as e:
            from logHandler import log
            log.debugWarning(f"PpBeepCommand.run(): ducking failed: {e}")

        _angle_x, _angle_y = 0, 0
        _audio3d = _commands_cached_config.get("audio3d", False)
        _handler = None
        if _audio3d:
            import globalPlugins.audiothemes as at
            _handler = getattr(at.GlobalPlugin, "_instance_handler", None)
            if _handler:
                _angle_x, _angle_y = _handler.get_earcon_angles()

        try:
            reverb_enabled = _commands_cached_config.get("reverb", False)
            if reverb_enabled:
                out_mode = _commands_cached_config.get("output_mode", "stereo")
                cache_key = ("beep", hz, length, left, right, _angle_x, _angle_y, out_mode)
                reverbed = None
                with _reverb_cache_lock:
                    if cache_key in _reverb_cache:
                        reverbed = _reverb_cache[cache_key]
                if reverbed is not None:
                    # The reverbed cache entry is already mode-specific: mono
                    # output centered the dry beep before reverb was applied.
                    rp = get_pooled_player(2, int(tones.SAMPLE_RATE), True)
                    rp.stop()
                    rp.feed(reverbed)
                    rp.idle()
                    self.reverbPlayer = rp
                    return

                bufSize=generateBeep(None,hz,length,left,right)
                buf=create_string_buffer(bufSize)
                generateBeep(buf,hz,length,left,right)

                from .unspoken.steam_audio import get_steam_audio
                steam_audio = get_steam_audio()
                if steam_audio and getattr(steam_audio, "initialized", False):
                    reverbed_generated = None
                    if _angle_x == 0 and _angle_y == 0:
                        # Centered beep: mono output mode applies only to the
                        # dry beep (L==R), reverb output must stay stereo.
                        dry_pcm = ensure_mono(buf.raw, 2, int(tones.SAMPLE_RATE))
                        reverbed_generated = steam_audio.apply_reverb(dry_pcm)
                    else:
                        arr = array.array('h')
                        arr.frombytes(buf.raw)
                        # Beeps from generateBeep are stereo
                        float_samples = _downmix_stereo_mono(arr)
                        remainder = len(float_samples) % 1024
                        if remainder != 0:
                            float_samples.extend([0.0] * (1024 - remainder))
                        processed = steam_audio.process_sound(float_samples, _angle_x, _angle_y)
                        if processed:
                            reverbed_generated = steam_audio.apply_reverb(processed)
                    if reverbed_generated:
                        _reverb_cache_put(cache_key, reverbed_generated)
                        rp = get_pooled_player(2, int(tones.SAMPLE_RATE), True)
                        rp.stop()
                        rp.feed(reverbed_generated)
                        rp.idle()
                        self.reverbPlayer = rp
                        return
        except Exception as e:
            from logHandler import log
            log.error(f"Failed to apply reverb to PpBeepCommand: {e}", exc_info=True)

        bufSize=generateBeep(None,hz,length,left,right)
        buf=create_string_buffer(bufSize)
        generateBeep(buf,hz,length,left,right)
        audio_bytes = buf.raw
        cur_channels = 2
        cur_sample_rate = int(tones.SAMPLE_RATE)

        _spatialized = False
        if _audio3d and _handler and getattr(_handler.player, "steam_audio_active", False) and (_angle_x != 0 or _angle_y != 0):
            arr = array.array('h')
            arr.frombytes(audio_bytes)
            float_samples = _downmix_stereo_mono(arr)
            remainder = len(float_samples) % 1024
            if remainder:
                float_samples.extend([0.0] * (1024 - remainder))
            processed = _handler.player.steam_audio.process_sound(float_samples, _angle_x, _angle_y)
            if processed:
                audio_bytes = processed
                _spatialized = True

        if not _spatialized:
            audio_bytes = ensure_mono(audio_bytes, cur_channels, cur_sample_rate)

        p = _get_pp_player()
        p.stop()
        p.feed(audio_bytes)
        p.idle()

    def getDuration(self):
        return self.length

    def __repr__(self):
        return "PpBeepCommand({hz}, {length}, left={left}, right={right})".format(
            hz=self.hz, length=self.length, left=self.left, right=self.right)

    def terminate(self):
        if self.reverbPlayer is not None:
            self.reverbPlayer.stop()
        else:
            _get_pp_player().stop()

class PpWaveFileCommand(PpSynchronousCommand):
    _wave_cache = {}
    _cache_lock = threading.Lock()

    def __init__(self, fileName, startAdjustment=0, endAdjustment=0, volume=100):
        self.fileName = fileName
        self.startAdjustment = startAdjustment
        self.endAdjustment = endAdjustment
        self.volume = volume
        self._loaded = False
        self.buf = None
        self.fileWavePlayer = None
        self._duration = 0
        self._channels = 1
        self._sample_rate = 44100

    def _ensureLoaded(self):
        if self._loaded:
            return
            
        with self._cache_lock:
            cache_key = (self.fileName, self.volume, self.startAdjustment, self.endAdjustment)
            if cache_key in self._wave_cache:
                cached = self._wave_cache[cache_key]
                self.buf = cached["buf"]
                self._duration = cached["duration"]
                self._channels = cached["channels"]
                self._sample_rate = cached["sample_rate"]
                
                # Re-acquire the pooled player
                self.fileWavePlayer = get_pooled_player(self._channels, self._sample_rate, False)
                
                # Move to end for LRU
                self._wave_cache[cache_key] = self._wave_cache.pop(cache_key)
                
                self._loaded = True
                return

        decoded = None
        try:
            from .unspoken import wav_decode
            decoded = wav_decode.decode_wav_to_float(self.fileName)
        except Exception as e:
            from logHandler import log
            log.debugWarning(f"PpWaveFileCommand: native WAV decode failed for {self.fileName}: {e}")

        if self.buf is None:
            ext = os.path.splitext(self.fileName)[1].lower()
            try:
                from logHandler import log
                if ext == '.mp3':
                    from .unspoken import mp3_decode
                    decoded = mp3_decode.decode_mp3_to_float(self.fileName)
                elif ext == '.ogg':
                    from .unspoken import ogg_vorbis
                    decoded = ogg_vorbis.decode_ogg_to_float(self.fileName)
                elif ext == '.flac':
                    from .unspoken import flac_decode
                    decoded = flac_decode.decode_flac_to_float(self.fileName)
            except Exception as e:
                log.error(f"PpWaveFileCommand: native decode failed for {self.fileName}: {e}")

        if self.buf is None and decoded is None:
            try:
                if not _commands_cached_config.get("enable_ffmpeg", False):
                    return
                from logHandler import log
                from .unspoken import ffmpeg_utils
                decoded = ffmpeg_utils.decode_with_ffmpeg(self.fileName)
                if decoded is None:
                    log.error(f"PpWaveFileCommand: FFmpeg decode failed for {self.fileName}")
                    return
            except Exception as e:
                log.error(f"PpWaveFileCommand: FFmpeg fallback error for {self.fileName}: {e}")
                return

        if decoded is not None:
            float_samples, sample_rate, channels = decoded
            import array as _array
            int_arr = _array.array('h', (max(-32768, min(32767, int(s * 32767))) for s in float_samples))
            if self.volume != 100:
                vol_mult = self.volume / 100.0
                int_arr = _array.array('h', (max(-32768, min(32767, int(x * vol_mult))) for x in int_arr))
            if self.startAdjustment > 0:
                pos = self.startAdjustment * sample_rate // 1000
                pos *= channels
                int_arr = int_arr[pos:]
            if self.endAdjustment > 0:
                end_pos = self.endAdjustment * sample_rate // 1000
                end_pos *= channels
                if end_pos < len(int_arr):
                    int_arr = int_arr[:-end_pos]
            self.buf = int_arr.tobytes()
            self._channels = channels
            self._sample_rate = sample_rate
            self.fileWavePlayer = get_pooled_player(
                channels=self._channels,
                sample_rate=self._sample_rate,
                ducking=False
            )
            total_samples = len(int_arr)
            total_frames = total_samples // channels
            wavMillis = int(1000 * total_frames / sample_rate)
            result = wavMillis - self.startAdjustment - self.endAdjustment
            self._duration = max(0, result)
        
        with self._cache_lock:
            if self.buf is not None:
                if len(self._wave_cache) > 50:
                    self._wave_cache.pop(next(iter(self._wave_cache)))
                self._wave_cache[cache_key] = {
                    "buf": self.buf,
                    "duration": self._duration,
                    "channels": self._channels,
                    "sample_rate": self._sample_rate
                }
                self._loaded = True

    def run(self):
        if is_sound_suppressed("earcons"):
            return
        try:
            self._ensureLoaded()
        except Exception as e:
            from logHandler import log
            log.debugWarning(f"PpWaveFileCommand.run() _ensureLoaded failed: {e}", exc_info=True)
            return
        if not self._loaded:
            return
        try:
            self._runInner()
        except Exception as e:
            from logHandler import log
            log.debugWarning(f"PpWaveFileCommand.run() failed: {e}", exc_info=True)

    def _runInner(self):
        if self.startAdjustment < 0:
            time.sleep(-self.startAdjustment / 1000.0)

        # Apply audio ducking factor
        _ducking_factor = 1.0
        try:
            from . import frenzy
            _ducking_factor = frenzy.get_ducking_factor("earcons")
        except Exception as e:
            from logHandler import log
            log.debugWarning(f"PpWaveFileCommand.run(): ducking failed: {e}")

        _angle_x, _angle_y = 0, 0
        _audio3d = _commands_cached_config.get("audio3d", False)
        _handler = None
        if _audio3d:
            import globalPlugins.audiothemes as at
            _handler = getattr(at.GlobalPlugin, "_instance_handler", None)
            if _handler:
                _angle_x, _angle_y = _handler.get_earcon_angles()

        try:
            reverb_enabled = _commands_cached_config.get("reverb", False)
            if reverb_enabled:
                out_mode = _commands_cached_config.get("output_mode", "stereo")
                cache_key = ("wave", self.fileName, self.volume, self.startAdjustment, self.endAdjustment, _angle_x, _angle_y, out_mode)
                packed = None
                with _reverb_cache_lock:
                    if cache_key in _reverb_cache:
                        packed = _reverb_cache[cache_key]
                if packed is not None:
                    # The reverbed cache entry is already mode-specific: mono
                    # output centered the dry file before reverb was applied.
                    rp = get_pooled_player(2, self._sample_rate, False)
                    rp.stop()
                    rp.feed(_apply_ducking(packed, _ducking_factor))
                    rp.idle()
                    self.fileWavePlayer = rp
                    return

                from .unspoken.steam_audio import get_steam_audio
                steam_audio = get_steam_audio()
                if steam_audio and getattr(steam_audio, "initialized", False):
                    reverbed_generated = None
                    if _angle_x == 0 and _angle_y == 0 and self._channels == 2:
                        # Centered stereo file: mono output mode applies only to the
                        # dry file (L==R), reverb output must stay stereo.
                        dry_pcm = ensure_mono(self.buf, 2, self._sample_rate)
                        reverbed_generated = steam_audio.apply_reverb(dry_pcm)
                    elif _angle_x == 0 and _angle_y == 0 and self._channels == 1:
                        # Centered mono file: upmix to stereo, then add reverb.
                        arr = array.array('h')
                        arr.frombytes(self.buf)
                        mono_dup = array.array('h', (s for s in arr for _ in range(2)))
                        reverbed_generated = steam_audio.apply_reverb(mono_dup.tobytes())
                    else:
                        # Off-center: downmix to mono, reposition, then add reverb.
                        arr = array.array('h')
                        arr.frombytes(self.buf)
                        if self._channels == 2:
                            float_samples = _downmix_stereo_mono(arr)
                        else:
                            float_samples = array.array('f', (x / 32767.0 for x in arr))
                        remainder = len(float_samples) % 1024
                        if remainder != 0:
                            float_samples.extend([0.0] * (1024 - remainder))
                        processed = steam_audio.process_sound(float_samples, _angle_x, _angle_y)
                        if processed:
                            reverbed_generated = steam_audio.apply_reverb(processed)
                    if reverbed_generated:
                        _reverb_cache_put(cache_key, reverbed_generated)
                        rp = get_pooled_player(2, self._sample_rate, False)
                        rp.stop()
                        rp.feed(_apply_ducking(reverbed_generated, _ducking_factor))
                        rp.idle()
                        self.fileWavePlayer = rp
                        return
        except Exception as e:
            from logHandler import log
            log.error(f"Failed to apply reverb to PpWaveFileCommand: {e}", exc_info=True)

        audio_bytes = self.buf
        if audio_bytes is None:
            return
        cur_channels = self._channels
        cur_sample_rate = self._sample_rate

        _spatialized = False
        if _audio3d and _handler and getattr(_handler.player, "steam_audio_active", False) and (_angle_x != 0 or _angle_y != 0):
            arr = array.array('h')
            arr.frombytes(audio_bytes)
            if cur_channels == 2:
                float_samples = _downmix_stereo_mono(arr)
            else:
                float_samples = array.array('f', (x / 32767.0 for x in arr))
            remainder = len(float_samples) % 1024
            if remainder:
                float_samples.extend([0.0] * (1024 - remainder))
            processed = _handler.player.steam_audio.process_sound(float_samples, _angle_x, _angle_y)
            if processed:
                audio_bytes = processed
                cur_channels = 2
                _spatialized = True

        if not _spatialized:
            audio_bytes = ensure_mono(audio_bytes, cur_channels, cur_sample_rate)

        fileWavePlayer = self.fileWavePlayer
        if fileWavePlayer is None:
            return
        fileWavePlayer.stop()
        try:
            fileWavePlayer.feed(_apply_ducking(audio_bytes, _ducking_factor))
        except Exception as e:
            from logHandler import log
            log.error(f"PpWaveFileCommand.run() feed ERROR: {e}", exc_info=True)
        try:
            fileWavePlayer.idle()
        except Exception as e:
            from logHandler import log
            log.error(f"PpWaveFileCommand.run() idle ERROR: {e}", exc_info=True)

    def getDuration(self):
        self._ensureLoaded()
        return self._duration

    def __repr__(self):
        return "PpWaveFileCommand(%r)" % self.fileName

    def terminate(self):
        if self.fileWavePlayer is not None:
            self.fileWavePlayer.stop()

_current_chain_lock = threading.Lock()
currentChain = None

def terminateCurrentChain():
    global currentChain
    with _current_chain_lock:
        if currentChain is not None:
            currentChain.terminate()
            currentChain = None
class PpChainCommand(PpSynchronousCommand):
    def __init__(self, subcommands):
        super().__init__()
        self.subcommands = subcommands
        self.terminated = False

    def run(self):
        global currentChain
        try:
            with _current_chain_lock:
                currentChain = self
            import threading
            t = threading.Thread(target=self.threadFunc, daemon=True)
            t.start()
        except Exception as e:
            from logHandler import log
            log.debugWarning(f"PpChainCommand.run() failed: {e}", exc_info=True)
            with _current_chain_lock:
                if currentChain is self:
                    currentChain = None

    def getDuration(self):
        return sum([subcommand.getDuration() for subcommand in self.subcommands])

    def threadFunc(self):
        global currentChain
        try:
            timestamp = time.time()
            for subcommand in self.subcommands:
                if self.terminated:
                    return
                threadPool.add_task(subcommand.run)
                timestamp += subcommand.getDuration() / 1000
                sleepTime = timestamp - time.time()
                if sleepTime > 0:
                    time.sleep(sleepTime)
        except Exception as e:
            from logHandler import log
            log.debugWarning(f"PpChainCommand.threadFunc() failed: {e}", exc_info=True)
        finally:
            with _current_chain_lock:
                if currentChain is self:
                    currentChain = None
        

    def __repr__(self):
        return f"PpChainCommand({self.subcommands})"

    def terminate(self):
        self.terminated = True
        for subcommand in self.subcommands:
            subcommand.terminate()
