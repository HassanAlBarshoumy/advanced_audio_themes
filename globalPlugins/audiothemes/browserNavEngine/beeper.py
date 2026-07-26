#A part of the BrowserNav addon for NVDA
#Copyright (C) 2017-2021 Tony Malykh
#This file is covered by the GNU General Public License.
#See the file LICENSE  for more details.

import api
import config
import ctypes
import functools
import math
import NVDAHelper
import nvwave
import operator
import os
import queue
import re
import speech
import struct
import threading
import tones
import ui
import wave

from . addonConfig import *
from ..utils import ensure_mono, is_sound_suppressed

_beeper_output_device = None

def _get_beeper_output_device():
    global _beeper_output_device
    if _beeper_output_device is None:
        try:
            _beeper_output_device = config.conf["speech"]["outputDevice"]
        except KeyError:
            _beeper_output_device = config.conf["audio"]["outputDevice"]
    return _beeper_output_device

class Beeper:
    BASE_FREQ = speech.IDT_BASE_FREQUENCY
    def getPitch(self, indent):
        return self.BASE_FREQ*2**(indent/24.0) #24 quarter tones per octave.

    BEEP_LEN = 10 # millis
    PAUSE_LEN = 5 # millis
    MAX_CRACKLE_LEN = 400 # millis
    #MAX_BEEP_COUNT = MAX_CRACKLE_LEN // (BEEP_LEN + PAUSE_LEN)
    MAX_BEEP_COUNT = 40 # Corresponds to about 500 paragraphs with the log formula

    def __init__(self):
        outputDevice = _get_beeper_output_device()
        self.player = nvwave.WavePlayer(
            channels=2,
            samplesPerSec=int(tones.SAMPLE_RATE),
            bitsPerSample=16,
            outputDevice=outputDevice,
            wantDucking=False,
            purpose=nvwave.AudioPurpose.SOUNDS,
        )
        self._beep_queue = queue.Queue(maxsize=8)
        self._beep_worker = threading.Thread(target=self._beep_worker_loop, daemon=True)
        self._beep_worker.start()

    def _beep_worker_loop(self):
        while True:
            item = self._beep_queue.get()
            if item is None:
                self._beep_queue.task_done()
                break
            player, data = item
            try:
                player.feed(data)
            except Exception:
                pass
            self._beep_queue.task_done()

    def _feed_player(self, player, data):
        try:
            self._beep_queue.put_nowait((player, data))
        except queue.Full:
            pass



    def fancyCrackle(self, levels, volume, initialDelay=0, category="browsernav"):
        if is_sound_suppressed(category):
            return
        # Apply audio ducking
        try:
            from .. import frenzy
            df = frenzy.get_ducking_factor(category)
            if df < 1.0:
                volume = int(volume * df)
        except Exception:
            pass
        l = len(levels)
        coef = 10
        l = coef * math.log(
            1 + l/coef
        )
        l = int(round(l))
        levels = self.uniformSample(levels, min(l, self.MAX_BEEP_COUNT ))
        beepLen = self.BEEP_LEN
        pauseLen = self.PAUSE_LEN
        initialDelaySize = 0 if initialDelay == 0 else NVDAHelper.localLib.generateBeep(None,self.BASE_FREQ,initialDelay,0, 0)
        pauseBufSize = NVDAHelper.localLib.generateBeep(None,self.BASE_FREQ,pauseLen,0, 0)
        beepBufSizes = [NVDAHelper.localLib.generateBeep(None,self.getPitch(l), beepLen, volume, volume) for l in levels]
        bufSize = initialDelaySize + sum(beepBufSizes) + len(levels) * pauseBufSize
        buf = ctypes.create_string_buffer(bufSize)
        bufPtr = 0
        bufPtr += initialDelaySize
        for l in levels:
            bufPtr += NVDAHelper.localLib.generateBeep(
                ctypes.cast(ctypes.byref(buf, bufPtr), ctypes.POINTER(ctypes.c_char)),
                self.getPitch(l), beepLen, volume, volume)
            bufPtr += pauseBufSize # add a short pause
        self.player.stop()
        self._feed_player(self.player, buf.raw)

    def simpleCrackle(self, n, volume, initialDelay=0, category="browsernav"):
        return self.fancyCrackle([0] * n, volume, initialDelay=initialDelay, category=category)


    NOTES = "A,B,H,C,C#,D,D#,E,F,F#,G,G#".split(",")
    NOTE_RE = re.compile("[A-H][#]?")
    BASE_FREQ = 220
    def getChordFrequencies(self, chord):
        prev = -1
        result = []
        for m in self.NOTE_RE.finditer(chord):
            s = m.group()
            try:
                i =self.NOTES.index(s)
            except ValueError:
                continue
            while i < prev:
                i += 12
            result.append(int(self.BASE_FREQ * (2 ** (i / 12.0))))
            prev = i
        return result

    def fancyBeep(self, chord, length, left=10, right=10):
        if is_sound_suppressed("browsernav"):
            return
        # Apply audio ducking
        try:
            from .. import frenzy
            df = frenzy.get_ducking_factor("browsernav")
            if df < 1.0:
                left = int(left * df)
                right = int(right * df)
        except Exception:
            pass
        beepLen = length
        freqs = self.getChordFrequencies(chord)
        intSize = 8 # bytes
        bufSize = max([NVDAHelper.localLib.generateBeep(None,freq, beepLen, right, left) for freq in freqs])
        if bufSize % intSize != 0:
            bufSize += intSize
            bufSize -= (bufSize % intSize)
        self.player.stop()
        bbs = []
        result = [0] * (bufSize//intSize)
        for freq in freqs:
            buf = ctypes.create_string_buffer(bufSize)
            NVDAHelper.localLib.generateBeep(buf, freq, beepLen, right, left)
            bytes = bytearray(buf)
            unpacked = struct.unpack("<%dQ" % (bufSize // intSize), bytes)
            result = map(operator.add, result, unpacked)
        maxInt = 1 << (8 * intSize)
        result = map(lambda x : x %maxInt, result)
        packed = struct.pack("<%dQ" % (bufSize // intSize), *result)
        self._feed_player(self.player, packed)

    def uniformSample(self, a, m):
        n = len(a)
        if n <= m:
            return a
        # Here assume n > m
        result = []
        for i in range(0, m*n, n):
            result.append(a[i  // m])
        return result
    def stop(self):
        self.player.stop()


beeper = Beeper()

def endOfDocument(message):
    import globalPlugins.audiothemes as at
    handler = getattr(at.GlobalPlugin, "_instance_handler", None)
    if handler and handler.play_theme_sound("end_of_document"):
        pass # Played via theme
    else:
        volume = getConfig("noNextTextChimeVolume")
        beeper.fancyBeep("HF", 100, volume, volume)
        
    if getConfig("noNextTextMessage"):
        ui.message(message)
def getSoundsPath():
    # Navigate from browserNavEngine/ up to the addon root (audio_themes_NG/)
    # __file__ = .../audio_themes_NG/globalPlugins/audiothemes/browserNavEngine/beeper.py
    thisDir = os.path.abspath(os.path.dirname(__file__))  # browserNavEngine/
    audiothemesDir = os.path.dirname(thisDir)               # audiothemes/
    globalPluginsDir = os.path.dirname(audiothemesDir)      # globalPlugins/
    addonDir = os.path.dirname(globalPluginsDir)            # audio_themes_NG/
    soundsPath = os.path.join(addonDir, "sounds", "browsernav")
    return soundsPath

@functools.lru_cache(maxsize=64)
def adjustVolume(bb, volume):
    # Assuming bb is encoded 116 bits per value!
    n = len(bb) // 2
    format = f"<{n}h"
    unpacked = struct.unpack(format, bb)
    unpacked = [int(x * volume / 100) for x in unpacked]
    result=  struct.pack(format, *unpacked)
    return result

spcFile=None
spcPlayer=None
spcBuf = None
spcChannels = 2
_spc_lock = threading.Lock()
_spc_play_lock = threading.Lock()
def skippedParagraphChime():
    import globalPlugins.audiothemes as at
    handler = getattr(at.GlobalPlugin, "_instance_handler", None)
    if handler and handler.play_theme_sound("skip_paragraph"):
        return
        
    global spcFile, spcPlayer, spcBuf, spcChannels
    with _spc_lock:
        if spcPlayer is not None:
            pass
        else:
            try:
                spcFile = wave.open(getSoundsPath() + "\\classic\\on.wav","r")
            except Exception:
                return
            spcChannels = spcFile.getnchannels()
            outputDevice=_get_beeper_output_device()
            spcPlayer = nvwave.WavePlayer(
                channels=spcChannels,
                samplesPerSec=spcFile.getframerate(),
                bitsPerSample=spcFile.getsampwidth()*8,
                outputDevice=outputDevice,
                wantDucking=False,
                purpose=nvwave.AudioPurpose.SOUNDS,
            )
            spcFile.rewind()
            spcFile.setpos(100 *         spcFile.getframerate() // 1000)
            spcBuf = spcFile.readframes(spcFile.getnframes())
            spcFile.close()
    def playSkipParagraphChime():
        with _spc_play_lock:
          try:
            spcPlayer.stop()
            # Apply audio ducking
            buf = spcBuf
            try:
                from .. import frenzy
                df = frenzy.get_ducking_factor("browsernav")
                if df < 1.0:
                    buf = frenzy.apply_ducking_to_pcm(buf, df)
            except Exception:
                pass
            spcPlayer.feed(
                ensure_mono(
                    adjustVolume(
                        buf,
                        getConfig("skipChimeVolume")
                    ),
                    spcChannels,
                    0
                )
            )
            spcPlayer.idle()
          except Exception:
            pass
    threading.Thread(target=playSkipParagraphChime, daemon=True).start()

