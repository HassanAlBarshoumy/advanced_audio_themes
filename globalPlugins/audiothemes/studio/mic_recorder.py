# coding: utf-8

import ctypes
import ctypes.wintypes
import os
import wave
import threading

WAVE_FORMAT_PCM = 1
CALLBACK_FUNCTION = 0x00030000
WIM_OPEN = 0x03BE
WIM_CLOSE = 0x03C2
WIM_DATA = 0x03C0
MMSYSERR_NOERROR = 0
WHDR_DONE = 0x00000001
MAX_ERROR_LEN = 256
BUF_DURATION = 1

class WAVEFORMATEX(ctypes.Structure):
	_fields_ = [
		("wFormatTag", ctypes.wintypes.WORD),
		("nChannels", ctypes.wintypes.WORD),
		("nSamplesPerSec", ctypes.wintypes.DWORD),
		("nAvgBytesPerSec", ctypes.wintypes.DWORD),
		("nBlockAlign", ctypes.wintypes.WORD),
		("wBitsPerSample", ctypes.wintypes.WORD),
		("cbSize", ctypes.wintypes.WORD),
	]

class WAVEHDR(ctypes.Structure):
	_fields_ = [
		("lpData", ctypes.c_char_p),
		("dwBufferLength", ctypes.wintypes.DWORD),
		("dwBytesRecorded", ctypes.wintypes.DWORD),
		("dwUser", ctypes.c_void_p),
		("dwFlags", ctypes.wintypes.DWORD),
		("dwLoops", ctypes.wintypes.DWORD),
		("lpNext", ctypes.c_void_p),
		("reserved", ctypes.c_void_p),
	]

winmm = ctypes.windll.winmm

# Set argtypes for all winmm functions used
winmm.waveInGetNumDevs.argtypes = []
winmm.waveInGetNumDevs.restype = ctypes.wintypes.UINT

winmm.waveInOpen.argtypes = [
	ctypes.POINTER(ctypes.wintypes.HANDLE),
	ctypes.wintypes.WORD,
	ctypes.POINTER(WAVEFORMATEX),
	ctypes.c_void_p,
	ctypes.c_void_p,
	ctypes.wintypes.DWORD,
]
winmm.waveInOpen.restype = ctypes.wintypes.DWORD

winmm.waveInClose.argtypes = [ctypes.wintypes.HANDLE]
winmm.waveInClose.restype = ctypes.wintypes.DWORD

winmm.waveInPrepareHeader.argtypes = [ctypes.wintypes.HANDLE, ctypes.POINTER(WAVEHDR), ctypes.wintypes.UINT]
winmm.waveInPrepareHeader.restype = ctypes.wintypes.DWORD

winmm.waveInUnprepareHeader.argtypes = [ctypes.wintypes.HANDLE, ctypes.POINTER(WAVEHDR), ctypes.wintypes.UINT]
winmm.waveInUnprepareHeader.restype = ctypes.wintypes.DWORD

winmm.waveInAddBuffer.argtypes = [ctypes.wintypes.HANDLE, ctypes.POINTER(WAVEHDR), ctypes.wintypes.UINT]
winmm.waveInAddBuffer.restype = ctypes.wintypes.DWORD

winmm.waveInStart.argtypes = [ctypes.wintypes.HANDLE]
winmm.waveInStart.restype = ctypes.wintypes.DWORD

winmm.waveInStop.argtypes = [ctypes.wintypes.HANDLE]
winmm.waveInStop.restype = ctypes.wintypes.DWORD

winmm.waveInReset.argtypes = [ctypes.wintypes.HANDLE]
winmm.waveInReset.restype = ctypes.wintypes.DWORD

winmm.waveInGetErrorTextW.argtypes = [ctypes.wintypes.DWORD, ctypes.wintypes.LPWSTR, ctypes.wintypes.UINT]
winmm.waveInGetErrorTextW.restype = ctypes.wintypes.DWORD

WAVEIN_CALLBACK = ctypes.WINFUNCTYPE(
	None,
	ctypes.wintypes.HANDLE,
	ctypes.wintypes.UINT,
	ctypes.c_void_p,
	ctypes.c_void_p,
	ctypes.c_void_p,
)


class MicRecorder:
	def __init__(self):
		self.is_recording = False
		self._samples = []
		self._lock = threading.Lock()
		self._wave_in = None
		self._header_a = None
		self._header_b = None
		self._buf_a = None
		self._buf_b = None
		self._callback_obj = None

	def _get_error_text(self, mmr):
		buf = ctypes.create_unicode_buffer(MAX_ERROR_LEN)
		winmm.waveInGetErrorTextW(mmr, buf, MAX_ERROR_LEN)
		return buf.value or f"Error {mmr}"

	def _callback(self, hwi, uMsg, dwInstance, dwParam1, dwParam2):
		if uMsg == WIM_DATA:
			hdr_ptr = ctypes.cast(dwParam1, ctypes.POINTER(WAVEHDR))
			hdr = hdr_ptr.contents
			if hdr.dwBytesRecorded > 0:
				data = ctypes.string_at(hdr.lpData, hdr.dwBytesRecorded)
				with self._lock:
					self._samples.append(data)
			if self.is_recording:
				winmm.waveInAddBuffer(ctypes.c_void_p(hwi), hdr_ptr, ctypes.sizeof(WAVEHDR))

	def start_recording(self, sample_rate=44100, channels=2):
		if self.is_recording:
			return False

		num_devs = winmm.waveInGetNumDevs()
		if num_devs == 0:
			raise RuntimeError("No audio input devices found on this system")

		self._samples = []

		fmt = WAVEFORMATEX()
		fmt.wFormatTag = WAVE_FORMAT_PCM
		fmt.nChannels = channels
		fmt.nSamplesPerSec = sample_rate
		fmt.wBitsPerSample = 16
		fmt.nBlockAlign = channels * 2
		fmt.nAvgBytesPerSec = sample_rate * fmt.nBlockAlign
		fmt.cbSize = 0

		buf_size = sample_rate * fmt.nBlockAlign * BUF_DURATION

		self._callback_obj = WAVEIN_CALLBACK(self._callback)

		hwi = ctypes.wintypes.HANDLE()
		ret = winmm.waveInOpen(
			ctypes.byref(hwi),
			-1,
			ctypes.byref(fmt),
			self._callback_obj,
			0,
			CALLBACK_FUNCTION,
		)
		if ret != MMSYSERR_NOERROR:
			raise RuntimeError(f"Cannot open recording device: {self._get_error_text(ret)}")

		self._wave_in = hwi

		self._buf_a = ctypes.create_string_buffer(buf_size)
		self._buf_b = ctypes.create_string_buffer(buf_size)

		self._header_a = WAVEHDR()
		self._header_a.lpData = ctypes.cast(self._buf_a, ctypes.c_char_p)
		self._header_a.dwBufferLength = buf_size

		self._header_b = WAVEHDR()
		self._header_b.lpData = ctypes.cast(self._buf_b, ctypes.c_char_p)
		self._header_b.dwBufferLength = buf_size

		for hdr in (self._header_a, self._header_b):
			ret = winmm.waveInPrepareHeader(hwi, ctypes.byref(hdr), ctypes.sizeof(WAVEHDR))
			if ret != MMSYSERR_NOERROR:
				winmm.waveInClose(hwi)
				raise RuntimeError(f"Cannot prepare buffer: {self._get_error_text(ret)}")
			ret = winmm.waveInAddBuffer(hwi, ctypes.byref(hdr), ctypes.sizeof(WAVEHDR))
			if ret != MMSYSERR_NOERROR:
				winmm.waveInClose(hwi)
				raise RuntimeError(f"Cannot queue buffer: {self._get_error_text(ret)}")

		ret = winmm.waveInStart(hwi)
		if ret != MMSYSERR_NOERROR:
			winmm.waveInClose(hwi)
			raise RuntimeError(f"Cannot start recording: {self._get_error_text(ret)}")

		self.is_recording = True
		return True

	def stop_and_save(self, filename):
		if not self.is_recording:
			raise RuntimeError("Not recording")

		self.is_recording = False

		hwi = self._wave_in
		winmm.waveInStop(hwi)
		winmm.waveInReset(hwi)

		all_data = bytearray()
		with self._lock:
			for chunk in self._samples:
				all_data.extend(chunk)
		self._samples = []

		os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)

		if len(all_data) == 0:
			for hdr in (self._header_a, self._header_b):
				if hdr:
					winmm.waveInUnprepareHeader(hwi, ctypes.byref(hdr), ctypes.sizeof(WAVEHDR))
			winmm.waveInClose(hwi)
			self._wave_in = None
			self._header_a = self._header_b = None
			self._buf_a = self._buf_b = None
			self._callback_obj = None
			raise RuntimeError("No audio data recorded — no samples captured from microphone")

		with wave.open(filename, "wb") as wf:
			wf.setnchannels(2)
			wf.setsampwidth(2)
			wf.setframerate(44100)
			wf.writeframes(bytes(all_data))

		for hdr in (self._header_a, self._header_b):
			if hdr:
				winmm.waveInUnprepareHeader(hwi, ctypes.byref(hdr), ctypes.sizeof(WAVEHDR))

		winmm.waveInClose(hwi)

		self._wave_in = None
		self._header_a = self._header_b = None
		self._buf_a = self._buf_b = None
		self._callback_obj = None

		if not os.path.isfile(filename) or os.path.getsize(filename) <= 44:
			raise RuntimeError(f"Recording saved but file is invalid: {filename}")

		return True
