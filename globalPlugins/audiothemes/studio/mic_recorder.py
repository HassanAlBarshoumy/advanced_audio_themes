# coding: utf-8

import ctypes
import os

class MicRecorder:
    def __init__(self):
        self.is_recording = False

    def start_recording(self):
        if self.is_recording:
            return False
        # Open a new waveaudio instance
        ctypes.windll.winmm.mciSendStringW("open new type waveaudio alias recsound", None, 0, None)
        # Set parameters (PCM, 44100Hz, 16-bit, stereo)
        ctypes.windll.winmm.mciSendStringW("set recsound bitspersample 16", None, 0, None)
        ctypes.windll.winmm.mciSendStringW("set recsound samplespersec 44100", None, 0, None)
        ctypes.windll.winmm.mciSendStringW("set recsound channels 2", None, 0, None)
        # Start recording
        ctypes.windll.winmm.mciSendStringW("record recsound", None, 0, None)
        self.is_recording = True
        return True

    def stop_and_save(self, filename):
        if not self.is_recording:
            return False
        # Make sure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        # Stop and save
        ctypes.windll.winmm.mciSendStringW("stop recsound", None, 0, None)
        cmd = f'save recsound "{filename}"'
        ctypes.windll.winmm.mciSendStringW(cmd, None, 0, None)
        ctypes.windll.winmm.mciSendStringW("close recsound", None, 0, None)
        self.is_recording = False
        return True
