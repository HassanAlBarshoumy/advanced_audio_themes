# audio_converter.py
"""Permanent audio conversion without external FFmpeg for the ENCODE step.

WAV output is written in pure Python (RIFF PCM 16-bit). FLAC output uses the
bundled libFLAC encoder DLL. FFmpeg.exe (when present and enabled) is only
used to DECODE source formats that have no bundled native decoder
(m4a/aac/opus/wma/mp2/ac3).

Every conversion is safe-by-default:
  1. The source is decoded first.
  2. The output is written to a temporary ".part" file next to the target.
  3. The output is decoded back and verified before anything is replaced.
  4. Only then is the target atomically installed (os.replace) and the source
     deleted.

If the target file already exists, the source is left untouched (skipped) so
an existing file that already maps to the same filename stem keeps winning.
"""

import os
import array
import struct
import ctypes
from logHandler import log

# Every audio format the addon understands. Used by the manual "Convert all
# theme sounds now" button so that ALL theme audio is rewritten to the
# selected target format (e.g. every WAV becomes FLAC when FLAC is chosen).
ALL_AUDIO_EXTS = {
	".wav", ".ogg", ".mp3", ".flac",
	".m4a", ".aac", ".opus", ".wma", ".mp2", ".ac3",
}

# Source extensions that have NO bundled native decoder. This is the default
# scope for the background auto-convert: only these FFmpeg-only files are
# rewritten, so bundled WAV stores and natively-supported formats are never
# touched without an explicit user action.
CONVERTIBLE_EXTS = {".m4a", ".aac", ".opus", ".wma", ".mp2", ".ac3"}

_flac_enc_lib = None


def _get_flac_encoder_lib():
	global _flac_enc_lib
	if _flac_enc_lib is None:
		try:
			dll_path = os.path.join(os.path.dirname(__file__), "lib", "x64", "libFLAC.dll")
			lib = ctypes.CDLL(dll_path)
			lib.FLAC__stream_encoder_new.restype = ctypes.c_void_p
			lib.FLAC__stream_encoder_new.argtypes = []
			lib.FLAC__stream_encoder_delete.restype = None
			lib.FLAC__stream_encoder_delete.argtypes = [ctypes.c_void_p]
			lib.FLAC__stream_encoder_set_channels.restype = ctypes.c_int
			lib.FLAC__stream_encoder_set_channels.argtypes = [ctypes.c_void_p, ctypes.c_uint]
			lib.FLAC__stream_encoder_set_bits_per_sample.restype = ctypes.c_int
			lib.FLAC__stream_encoder_set_bits_per_sample.argtypes = [ctypes.c_void_p, ctypes.c_uint]
			lib.FLAC__stream_encoder_set_sample_rate.restype = ctypes.c_int
			lib.FLAC__stream_encoder_set_sample_rate.argtypes = [ctypes.c_void_p, ctypes.c_uint]
			lib.FLAC__stream_encoder_set_compression_level.restype = ctypes.c_int
			lib.FLAC__stream_encoder_set_compression_level.argtypes = [ctypes.c_void_p, ctypes.c_uint]
			lib.FLAC__stream_encoder_init_file.restype = ctypes.c_int
			lib.FLAC__stream_encoder_init_file.argtypes = [
				ctypes.c_void_p, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_void_p
			]
			lib.FLAC__stream_encoder_process_interleaved.restype = ctypes.c_int
			lib.FLAC__stream_encoder_process_interleaved.argtypes = [
				ctypes.c_void_p, ctypes.POINTER(ctypes.c_int32), ctypes.c_uint
			]
			lib.FLAC__stream_encoder_finish.restype = ctypes.c_int
			lib.FLAC__stream_encoder_finish.argtypes = [ctypes.c_void_p]
			lib.FLAC__stream_encoder_get_state.restype = ctypes.c_int
			lib.FLAC__stream_encoder_get_state.argtypes = [ctypes.c_void_p]
			_flac_enc_lib = lib
		except Exception as e:
			log.error(f"Failed to load libFLAC.dll for encoding: {e}")
			_flac_enc_lib = None
	return _flac_enc_lib


def _decode_any(path, allow_ffmpeg=True):
	"""Decode any audio file to (float_array, sample_rate, channels) or None."""
	ext = os.path.splitext(path)[1].lower()
	try:
		if ext == ".wav":
			from . import wav_decode
			return wav_decode.decode_wav_to_float(path)
		if ext == ".ogg":
			from . import ogg_vorbis
			return ogg_vorbis.decode_ogg_to_float(path)
		if ext == ".mp3":
			from . import mp3_decode
			return mp3_decode.decode_mp3_to_float(path)
		if ext == ".flac":
			from . import flac_decode
			return flac_decode.decode_flac_to_float(path)
	except Exception as e:
		log.error(f"Native decode failed for {path}: {e}")
		return None
	if allow_ffmpeg:
		try:
			from . import ffmpeg_utils
			return ffmpeg_utils.decode_with_ffmpeg(path)
		except Exception as e:
			log.error(f"FFmpeg decode failed for {path}: {e}")
	return None


def _normalize_channels(samples, channels):
	"""Collapse multi-channel audio to mono (matches the addon's convention)."""
	if channels <= 2:
		return samples, channels
	n = len(samples) // channels
	mono = array.array('f', [0.0]) * n
	for c in range(channels):
		for i in range(n):
			mono[i] += samples[i * channels + c]
	inv = 1.0 / channels
	return array.array('f', (s * inv for s in mono)), 1


def _write_wav(path, samples, sample_rate, channels):
	"""Write float samples as a 16-bit PCM WAV file."""
	data = array.array('h', (max(-32768, min(32767, int(s * 32767.0))) for s in samples)).tobytes()
	byte_rate = sample_rate * channels * 2
	with open(path, "wb") as f:
		f.write(b"RIFF")
		f.write(struct.pack("<I", 36 + len(data)))
		f.write(b"WAVE")
		f.write(b"fmt ")
		f.write(struct.pack("<IHHIIHH", 16, 1, channels, sample_rate, byte_rate, channels * 2, 16))
		f.write(b"data")
		f.write(struct.pack("<I", len(data)))
		f.write(data)


def _encode_flac(path, samples, sample_rate, channels, compression=5):
	"""Encode float samples to a FLAC file using the bundled libFLAC encoder."""
	lib = _get_flac_encoder_lib()
	if lib is None:
		log.error("FLAC encoder unavailable: libFLAC.dll failed to load")
		return False
	enc = lib.FLAC__stream_encoder_new()
	if not enc:
		log.error("FLAC__stream_encoder_new failed")
		return False
	try:
		lib.FLAC__stream_encoder_set_channels(enc, channels)
		lib.FLAC__stream_encoder_set_bits_per_sample(enc, 16)
		lib.FLAC__stream_encoder_set_sample_rate(enc, sample_rate)
		lib.FLAC__stream_encoder_set_compression_level(enc, compression)
		ret = lib.FLAC__stream_encoder_init_file(enc, path.encode("utf-8"), None, None)
		if ret != 0:
			log.error(f"FLAC encoder init_file failed: status {ret}")
			return False
		n = len(samples) // channels
		int_arr = array.array('i', (max(-2147483648, min(2147483647, int(s * 32767.0))) for s in samples))
		buf = (ctypes.c_int32 * len(int_arr)).from_buffer(int_arr)
		ok = lib.FLAC__stream_encoder_process_interleaved(enc, buf, n)
		fin = lib.FLAC__stream_encoder_finish(enc)
		if not ok or not fin:
			log.error(
				f"FLAC encode failed: process={ok} finish={fin} "
				f"state={lib.FLAC__stream_encoder_get_state(enc)}"
			)
			return False
		return True
	except Exception as e:
		log.error(f"FLAC encode error: {e}")
		return False
	finally:
		try:
			lib.FLAC__stream_encoder_delete(enc)
		except Exception:
			pass


def _verify_file(path, fmt_ext=".wav"):
	"""Re-decode an output file natively to confirm it is valid and non-empty.

	The temp file carries a ".part" suffix (unknown extension), so the decoder
	is selected from the target format rather than the file extension.
	"""
	try:
		if fmt_ext == ".flac":
			from . import flac_decode
			decoded = flac_decode.decode_flac_to_float(path)
		else:
			from . import wav_decode
			decoded = wav_decode.decode_wav_to_float(path)
		return decoded is not None and len(decoded[0]) > 0
	except Exception:
		return False


def convert_file(src_path, target_ext=".wav", delete_original=True, allow_ffmpeg=True, compression=5):
	"""Convert one audio file. Returns (ok, message)."""
	target_ext = target_ext.lower()
	if not target_ext.startswith("."):
		target_ext = "." + target_ext
	src_ext = os.path.splitext(src_path)[1].lower()
	if src_ext == target_ext:
		return (True, "skipped (already target)")
	if not os.path.isfile(src_path):
		return (False, "source not found")
	target_path = os.path.splitext(src_path)[0] + target_ext
	if os.path.exists(target_path):
		# A file with the same stem already exists in the target format. Verify
		# it is a valid, non-empty file of the target format, then remove the
		# redundant source so an explicit "convert everything" run leaves no
		# duplicate stems behind (e.g. checkbox.wav + checkbox.flac).
		try:
			if _verify_file(target_path, target_ext):
				if delete_original:
					try:
						os.remove(src_path)
					except Exception as e:
						return (True, "skipped (target exists), original delete failed: %s" % e)
				return (True, "converted (target already existed)")
		except Exception:
			pass
		return (True, "skipped (target already exists)")
	decoded = _decode_any(src_path, allow_ffmpeg=allow_ffmpeg)
	if decoded is None:
		return (False, "decode failed")
	samples, sample_rate, channels = decoded
	samples, channels = _normalize_channels(samples, channels)
	if not samples or sample_rate <= 0:
		return (False, "empty audio")
	tmp_path = target_path + ".part"
	try:
		if os.path.exists(tmp_path):
			os.remove(tmp_path)
		if target_ext == ".wav":
			_write_wav(tmp_path, samples, sample_rate, channels)
		elif target_ext == ".flac":
			if not _encode_flac(tmp_path, samples, sample_rate, channels, compression):
				return (False, "FLAC encode failed")
		else:
			return (False, "unsupported target: %s" % target_ext)
		if not _verify_file(tmp_path, target_ext):
			return (False, "output verification failed")
		os.replace(tmp_path, target_path)
	except Exception as e:
		try:
			os.remove(tmp_path)
		except Exception:
			pass
		return (False, "conversion error: %s" % e)
	if delete_original:
		try:
			os.remove(src_path)
		except Exception as e:
			return (True, "converted but original delete failed: %s" % e)
	return (True, "converted")


def convert_folder(root, target_ext=".wav", candidate_exts=None, delete_original=True, allow_ffmpeg=True, report=None):
	"""Convert all candidate files under root.

	Returns (converted, skipped, failed, errors). `report(src, ok, msg)` is
	called for every candidate when provided.
	"""
	if candidate_exts is None:
		candidate_exts = CONVERTIBLE_EXTS
	converted = 0
	skipped = 0
	failed = 0
	errors = []
	for dirpath, _dirs, files in os.walk(root):
		for name in files:
			ext = os.path.splitext(name)[1].lower()
			if ext not in candidate_exts:
				continue
			src = os.path.join(dirpath, name)
			ok, msg = convert_file(src, target_ext, delete_original, allow_ffmpeg, compression=5)
			if report is not None:
				try:
					report(src, ok, msg)
				except Exception:
					pass
			if ok:
				if msg.startswith("skipped"):
					skipped += 1
				else:
					converted += 1
			else:
				failed += 1
				errors.append((src, msg))
	return (converted, skipped, failed, errors)


def convert_all(roots, target_ext=".wav", candidate_exts=None, delete_original=True, allow_ffmpeg=True, report=None):
	"""Convert all candidate files across multiple roots."""
	converted = 0
	skipped = 0
	failed = 0
	errors = []
	for root in roots:
		if not os.path.isdir(root):
			continue
		c, s, f, e = convert_folder(root, target_ext, candidate_exts, delete_original, allow_ffmpeg, report)
		converted += c
		skipped += s
		failed += f
		errors.extend(e)
	return (converted, skipped, failed, errors)
