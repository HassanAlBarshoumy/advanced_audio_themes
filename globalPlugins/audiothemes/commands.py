# -*- coding: UTF-8 -*-
#A part of the Earcons and Speech Rules addon for NVDA
#Copyright (C) 2019-2022 Tony Malykh
#This file is covered by the GNU General Public License.
#See the file COPYING.txt for more details.

import config
from ctypes import create_string_buffer
import nvwave
import speech
import speech.commands
import threading
import time
import tones
import wave

from .utils import *

try:
    outputDevice=config.conf["speech"]["outputDevice"]
except KeyError:
    outputDevice=config.conf["audio"]["outputDevice"]
ppSynchronousPlayer = nvwave.WavePlayer(channels=2, samplesPerSec=int(tones.SAMPLE_RATE), bitsPerSample=16, outputDevice=outputDevice,wantDucking=True, purpose=nvwave.AudioPurpose.SOUNDS,)

# Global pool for WavePlayers keyed by (channels, sample_rate, ducking)
_wave_player_pool = {}
_wave_player_pool_lock = threading.Lock()

def get_pooled_player(channels, sample_rate, ducking=False):
    global _wave_player_pool
    key = (channels, sample_rate, ducking)
    with _wave_player_pool_lock:
        if key not in _wave_player_pool:
            try:
                od = config.conf["speech"]["outputDevice"]
            except KeyError:
                od = config.conf["audio"]["outputDevice"]
            _wave_player_pool[key] = nvwave.WavePlayer(
                channels=channels,
                samplesPerSec=sample_rate,
                bitsPerSample=16,
                outputDevice=od,
                wantDucking=ducking,
                purpose=nvwave.AudioPurpose.SOUNDS
            )
        return _wave_player_pool[key]

# Cache for reverbed audio (capped at 50 entries to prevent unbounded growth)
_reverb_cache = {}
_reverb_cache_lock = threading.Lock()
_REVERB_CACHE_MAX = 50

def _reverb_cache_put(key, value):
    """Add to reverb cache with LRU eviction when exceeding max size."""
    with _reverb_cache_lock:
        if key in _reverb_cache:
            _reverb_cache.pop(key)
        elif len(_reverb_cache) >= _REVERB_CACHE_MAX:
            _reverb_cache.pop(next(iter(_reverb_cache)))
        _reverb_cache[key] = value

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
        from NVDAHelper import generateBeep
        hz,length,left,right = self.hz, self.length, self.left, self.right
        
        try:
            reverb_enabled = config.conf.get("unspoken", {}).get("Reverb", False)
            if reverb_enabled:
                cache_key = ("beep", hz, length, left, right)
                reverbed = None
                with _reverb_cache_lock:
                    if cache_key in _reverb_cache:
                        reverbed = _reverb_cache[cache_key]
                if reverbed is not None:
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
                    import array
                    arr = array.array('h')
                    arr.frombytes(buf.raw)
                    # Beeps from generateBeep are stereo
                    float_samples = [(arr[i] + arr[i+1]) / (2.0 * 32767.0) for i in range(0, len(arr), 2)]
                    remainder = len(float_samples) % 1024
                    if remainder != 0:
                        float_samples.extend([0.0] * (1024 - remainder))
                    processed = steam_audio.process_sound(float_samples, 0, 0)
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
        ppSynchronousPlayer.stop()
        ppSynchronousPlayer.feed(buf.raw)
        ppSynchronousPlayer.idle()

    def getDuration(self):
        return self.length

    def __repr__(self):
        return "PpBeepCommand({hz}, {length}, left={left}, right={right})".format(
            hz=self.hz, length=self.length, left=self.left, right=self.right)

    def terminate(self):
        if self.reverbPlayer is not None:
            self.reverbPlayer.stop()
        else:
            ppSynchronousPlayer.stop()

class PpWaveFileCommand(PpSynchronousCommand):
    _wave_cache = {}
    _cache_lock = threading.Lock()

    def __init__(self, fileName, startAdjustment=0, endAdjustment=0, volume=100):
        self.fileName = fileName
        self.startAdjustment = startAdjustment
        self.endAdjustment = endAdjustment
        self.volume = volume
        self._loaded = False
        self.f = None
        self.buf = None
        self.fileWavePlayer = None
        self._duration = 0

    def _ensureLoaded(self):
        if self._loaded:
            return
            
        with self._cache_lock:
            cache_key = (self.fileName, self.volume)
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

        self.f = wave.open(self.fileName, "r")
        f = self.f
        if self.f is None:
            raise RuntimeError("can not open file %s" % self.fileName)
        if f.getsampwidth() != 2:
            bits = f.getsampwidth() * 8
            raise RuntimeError(f"We only support 16-bit encoded wav files. '{self.fileName}' is encoded with {bits} bits per sample.")
        buf = f.readframes(f.getnframes())
        import array
        arr = array.array('h')
        arr.frombytes(buf)
        n = len(arr)
        
        # Apply volume
        if self.volume != 100:
            vol_mult = self.volume / 100.0
            for i in range(n):
                arr[i] = int(arr[i] * vol_mult)
        
        if self.startAdjustment > 0:
            pos = self.startAdjustment * f.getframerate() // 1000
            pos *= f.getnchannels()
            arr = arr[pos:]
            n = len(arr)
            
        self.buf = arr.tobytes()
        self._channels = f.getnchannels()
        self._sample_rate = f.getframerate()
        self.fileWavePlayer = get_pooled_player(
            channels=self._channels,
            sample_rate=self._sample_rate,
            ducking=False
        )
        frames = self.f.getnframes()
        rate = self.f.getframerate()
        wavMillis = int(1000 * frames / rate)
        result = wavMillis - self.startAdjustment - self.endAdjustment
        self._duration = max(0, result)
        
        # Close the file handle — we've read all data into self.buf
        try:
            self.f.close()
        except Exception as e:
            try:
                from logHandler import log
                log.debug(f"AudioThemes Swallowed Exception: {e}", exc_info=True)
            except:
                pass
        self.f = None
        
        with self._cache_lock:
            if len(self._wave_cache) > 100:
                self._wave_cache.pop(next(iter(self._wave_cache)))
            self._wave_cache[cache_key] = {
                "buf": self.buf, 
                "duration": self._duration,
                "channels": self._channels,
                "sample_rate": self._sample_rate
            }
            
        self._loaded = True

    def run(self):
        self._ensureLoaded()
        if self.startAdjustment < 0:
            time.sleep(-self.startAdjustment / 1000.0)

        try:
            reverb_enabled = config.conf.get("unspoken", {}).get("Reverb", False)
            if reverb_enabled:
                cache_key = ("wave", self.fileName, self.volume, self.startAdjustment)
                packed = None
                with _reverb_cache_lock:
                    if cache_key in _reverb_cache:
                        packed = _reverb_cache[cache_key]
                if packed is not None:
                    rp = get_pooled_player(2, self._sample_rate, False)
                    rp.stop()
                    rp.feed(packed)
                    rp.idle()
                    self.fileWavePlayer = rp
                    return

                from .unspoken.steam_audio import get_steam_audio
                steam_audio = get_steam_audio()
                if steam_audio and getattr(steam_audio, "initialized", False):
                    import array
                    arr = array.array('h')
                    arr.frombytes(self.buf)
                    if self._channels == 2:
                        float_samples = [(arr[i] + arr[i+1]) / (2.0 * 32767.0) for i in range(0, len(arr), 2)]
                    else:
                        float_samples = [x / 32767.0 for x in arr]
                    remainder = len(float_samples) % 1024
                    if remainder != 0:
                        float_samples.extend([0.0] * (1024 - remainder))
                    processed = steam_audio.process_sound(float_samples, 0, 0)
                    if processed:
                        reverbed_generated = steam_audio.apply_reverb(processed)
                        if reverbed_generated:
                            _reverb_cache_put(cache_key, reverbed_generated)
                            rp = get_pooled_player(2, self._sample_rate, False)
                            rp.stop()
                            rp.feed(reverbed_generated)
                            rp.idle()
                            self.fileWavePlayer = rp
                            return
        except Exception as e:
            from logHandler import log
            log.error(f"Failed to apply reverb to PpWaveFileCommand: {e}", exc_info=True)

        fileWavePlayer = self.fileWavePlayer
        fileWavePlayer.stop()
        fileWavePlayer.feed(self.buf)
        fileWavePlayer.idle()

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
        with _current_chain_lock:
            currentChain = self
        threadPool.add_task(self.threadFunc)

    def getDuration(self):
        return sum([subcommand.getDuration() for subcommand in self.subcommands])

    def threadFunc(self):
        global currentChain
        timestamp = time.time()
        for subcommand in self.subcommands:
            if self.terminated:
                return
            threadPool.add_task(subcommand.run)
            timestamp += subcommand.getDuration() / 1000
            sleepTime = timestamp - time.time()
            if sleepTime > 0:
                time.sleep(sleepTime)
        with _current_chain_lock:
            if currentChain is self:
                currentChain = None
        

    def __repr__(self):
        return f"PpChainCommand({self.subcommands})"

    def terminate(self):
        self.terminated = True
        for subcommand in self.subcommands:
            subcommand.terminate()
