import ctypes
import os
import array
from logHandler import log

_X64_DIR = os.path.join(os.path.dirname(__file__), "lib", "x64")

_mpg123 = ctypes.CDLL(os.path.join(_X64_DIR, "libmpg123-0.dll"))

MPG123_OK = 0
MPG123_DONE = -11
MPG123_NEW_FORMAT = -12

_mpg123.mpg123_new.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_int)]
_mpg123.mpg123_new.restype = ctypes.c_void_p

_mpg123.mpg123_delete.argtypes = [ctypes.c_void_p]
_mpg123.mpg123_delete.restype = None

_mpg123.mpg123_open.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
_mpg123.mpg123_open.restype = ctypes.c_int

_mpg123.mpg123_close.argtypes = [ctypes.c_void_p]
_mpg123.mpg123_close.restype = ctypes.c_int

_mpg123.mpg123_read.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
_mpg123.mpg123_read.restype = ctypes.c_int

_mpg123.mpg123_getformat.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_long),
    ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_int),
]
_mpg123.mpg123_getformat.restype = ctypes.c_int


def decode_mp3_to_float(path):
    mh = _mpg123.mpg123_new(None, None)
    if not mh:
        log.error("mpg123_new failed")
        return None

    try:
        ret = _mpg123.mpg123_open(mh, path.encode('utf-8'))
        if ret != MPG123_OK:
            log.error(f"mpg123_open failed for {path}: {ret}")
            return None

        rate = ctypes.c_long(0)
        channels = ctypes.c_int(0)
        encoding = ctypes.c_int(0)
        ret = _mpg123.mpg123_getformat(mh, ctypes.byref(rate), ctypes.byref(channels), ctypes.byref(encoding))
        if ret != MPG123_OK:
            log.error(f"mpg123_getformat failed: {ret}")
            return None

        buf_size = 8192
        buf = ctypes.create_string_buffer(buf_size)
        done = ctypes.c_size_t(0)
        all_pcm = bytearray()
        new_fmt_idle = 0

        while True:
            ret = _mpg123.mpg123_read(mh, buf, buf_size, ctypes.byref(done))
            if done.value > 0:
                all_pcm.extend(buf.raw[:done.value])
            if ret == MPG123_DONE:
                if done.value > 0:
                    continue
                if all_pcm:
                    break
                continue
            if ret == MPG123_NEW_FORMAT:
                new_fmt_idle += 1
                if new_fmt_idle > 10:
                    break
                continue
            if ret != MPG123_OK:
                if all_pcm:
                    break
                log.error(f"mpg123_read failed: {ret}")
                return None

        if not all_pcm:
            log.error(f"No PCM data decoded from {path}")
            return None

        arr = array.array('h')
        arr.frombytes(bytes(all_pcm))

        if channels.value == 2:
            n = len(arr) // 2
            float_samples = array.array('f', [0.0]) * n
            for i in range(n):
                float_samples[i] = (arr[i * 2] + arr[i * 2 + 1]) / 65536.0
            return (float_samples, rate.value, 1)
        else:
            float_samples = array.array('f', [s / 32768.0 for s in arr])
            return (float_samples, rate.value, channels.value)

    except Exception as e:
        log.error(f"Failed to decode MP3 {path}: {e}")
        return None
    finally:
        try:
            _mpg123.mpg123_close(mh)
        except Exception:
            pass
        try:
            _mpg123.mpg123_delete(mh)
        except Exception:
            pass
