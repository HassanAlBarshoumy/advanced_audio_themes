import ctypes
import ctypes.util
import os
import array
from logHandler import log

_X64_DIR = os.path.join(os.path.dirname(__file__), "lib", "x64")

# Load DLLs with full path to resolve dependencies
_ogg_lib = ctypes.CDLL(os.path.join(_X64_DIR, "libogg-0.dll"))
_vorbis_lib = ctypes.CDLL(os.path.join(_X64_DIR, "libvorbis-0.dll"))
_vorbisfile_lib = ctypes.CDLL(os.path.join(_X64_DIR, "libvorbisfile-3.dll"))

# --- vorbis_info struct ---
class VorbisInfo(ctypes.Structure):
    _fields_ = [
        ("version", ctypes.c_long),
        ("channels", ctypes.c_long),
        ("rate", ctypes.c_long),
        ("bitrate_upper", ctypes.c_long),
        ("bitrate_nominal", ctypes.c_long),
        ("bitrate_lower", ctypes.c_long),
        ("bitrate_window", ctypes.c_long),
    ]

# OggVorbis_File is large; allocate a buffer of sufficient size
OGG_VORBIS_FILE_SIZE = 1024

# --- ov_fopen ---
_vorbisfile_lib.ov_fopen.argtypes = [ctypes.c_char_p, ctypes.c_void_p]
_vorbisfile_lib.ov_fopen.restype = ctypes.c_int

def ov_fopen(path, vf_buffer):
    return _vorbisfile_lib.ov_fopen(path.encode("utf-8"), vf_buffer)

# --- ov_info ---
_vorbisfile_lib.ov_info.argtypes = [ctypes.c_void_p, ctypes.c_int]
_vorbisfile_lib.ov_info.restype = ctypes.POINTER(VorbisInfo)

def ov_info(vf_buffer):
    ptr = _vorbisfile_lib.ov_info(vf_buffer, 0)
    if ptr:
        return ptr.contents
    return None

# --- ov_read ---
_vorbisfile_lib.ov_read.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.POINTER(ctypes.c_int),
]
_vorbisfile_lib.ov_read.restype = ctypes.c_long

def ov_read(vf_buffer):
    buf_size = 4096
    buf = ctypes.create_string_buffer(buf_size)
    bitstream = ctypes.c_int(0)
	total_data = bytearray()
	while True:
		ret = _vorbisfile_lib.ov_read(vf_buffer, buf, buf_size, 0, 2, 1, ctypes.byref(bitstream))
		if ret == 0:
			break
		if ret < 0:
			log.debugWarning(f"ov_read error: {ret} (OV_HOLE=OV_ENOTVORBIS?) — continuing with partial data")
			break
		total_data.extend(buf.raw[:ret])
    return bytes(total_data)

# --- ov_clear ---
_vorbisfile_lib.ov_clear.argtypes = [ctypes.c_void_p]
_vorbisfile_lib.ov_clear.restype = ctypes.c_int

def ov_clear(vf_buffer):
    return _vorbisfile_lib.ov_clear(vf_buffer)

# --- Public API ---

def decode_ogg_to_float(path):
    """Decode an OGG file to float32 PCM samples.
    Returns (float_array, sample_rate, channels) or None on failure.
    """
    vf = ctypes.create_string_buffer(OGG_VORBIS_FILE_SIZE)
    try:
        ret = ov_fopen(path, vf)
        if ret != 0:
            log.error(f"ov_fopen failed for {path}: error {ret}")
            return None
        info = ov_info(vf)
        if not info:
            log.error(f"ov_info returned NULL for {path}")
            ov_clear(vf)
            return None
        sample_rate = info.rate
        channels = info.channels
        raw_pcm = ov_read(vf)
        ov_clear(vf)
        if not raw_pcm:
            return None
        arr = array.array('h')
        arr.frombytes(raw_pcm)
        float_samples = array.array('f', [s / 32768.0 for s in arr])
        return (float_samples, sample_rate, channels)
    except Exception as e:
        try:
            ov_clear(vf)
        except Exception:
            pass
        log.error(f"Failed to decode OGG {path}: {e}")
        return None
