import ctypes
import os
import array
from logHandler import log

_X64_DIR = os.path.join(os.path.dirname(__file__), "lib", "x64")

_flac = ctypes.CDLL(os.path.join(_X64_DIR, "libFLAC.dll"))

FLAC__STREAM_DECODER_WRITE_CONTINUE = 0
FLAC__STREAM_DECODER_END_OF_STREAM = 4
FLAC__STREAM_DECODER_UNINITIALIZED = 9

_flac.FLAC__stream_decoder_new.restype = ctypes.c_void_p
_flac.FLAC__stream_decoder_new.argtypes = []

_flac.FLAC__stream_decoder_delete.restype = None
_flac.FLAC__stream_decoder_delete.argtypes = [ctypes.c_void_p]

_flac.FLAC__stream_decoder_finish.restype = ctypes.c_int
_flac.FLAC__stream_decoder_finish.argtypes = [ctypes.c_void_p]

_flac.FLAC__stream_decoder_init_file.restype = ctypes.c_int
_flac.FLAC__stream_decoder_init_file.argtypes = [
    ctypes.c_void_p,
    ctypes.c_char_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
]

_flac.FLAC__stream_decoder_process_single.restype = ctypes.c_int
_flac.FLAC__stream_decoder_process_single.argtypes = [ctypes.c_void_p]

_flac.FLAC__stream_decoder_get_state.restype = ctypes.c_int
_flac.FLAC__stream_decoder_get_state.argtypes = [ctypes.c_void_p]

_flac.FLAC__stream_decoder_get_blocksize.restype = ctypes.c_uint
_flac.FLAC__stream_decoder_get_blocksize.argtypes = [ctypes.c_void_p]

_flac.FLAC__stream_decoder_get_channels.restype = ctypes.c_uint
_flac.FLAC__stream_decoder_get_channels.argtypes = [ctypes.c_void_p]

_flac.FLAC__stream_decoder_get_sample_rate.restype = ctypes.c_uint
_flac.FLAC__stream_decoder_get_sample_rate.argtypes = [ctypes.c_void_p]

_flac.FLAC__stream_decoder_get_bits_per_sample.restype = ctypes.c_uint
_flac.FLAC__stream_decoder_get_bits_per_sample.argtypes = [ctypes.c_void_p]


class _WriteContext:
    def __init__(self):
        self.all_pcm = []
        self.channels = 0
        self.bits_per_sample = 0
        self.sample_rate = 0


WRITE_CALLBACK = ctypes.CFUNCTYPE(
    ctypes.c_int,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
)

METADATA_CALLBACK = ctypes.CFUNCTYPE(
    None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p
)

ERROR_CALLBACK = ctypes.CFUNCTYPE(
    None, ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p
)


def _make_write_callback(ctx):
    @WRITE_CALLBACK
    def _write_cb(decoder, frame, buffer, client_data):
        blocksize = _flac.FLAC__stream_decoder_get_blocksize(decoder)
        channels = _flac.FLAC__stream_decoder_get_channels(decoder)
        if not ctx.channels:
            ctx.channels = channels
            ctx.bits_per_sample = _flac.FLAC__stream_decoder_get_bits_per_sample(decoder)
            ctx.sample_rate = _flac.FLAC__stream_decoder_get_sample_rate(decoder)
        buf_array = ctypes.cast(buffer, ctypes.POINTER(ctypes.POINTER(ctypes.c_int32)))
        for sample_idx in range(blocksize):
            for ch in range(channels):
                ctx.all_pcm.append(buf_array[ch][sample_idx])
        return FLAC__STREAM_DECODER_WRITE_CONTINUE
    return _write_cb


def _make_metadata_callback(ctx):
    @METADATA_CALLBACK
    def _metadata_cb(decoder, metadata, client_data):
        pass
    return _metadata_cb


def _make_error_callback(ctx):
    @ERROR_CALLBACK
    def _error_cb(decoder, status, client_data):
        pass
    return _error_cb


def decode_flac_to_float(path):
    dec = _flac.FLAC__stream_decoder_new()
    if not dec:
        log.error("FLAC__stream_decoder_new failed")
        return None

    try:
        ctx = _WriteContext()
        write_cb = _make_write_callback(ctx)
        metadata_cb = _make_metadata_callback(ctx)
        error_cb = _make_error_callback(ctx)

        ret = _flac.FLAC__stream_decoder_init_file(
            dec, path.encode('utf-8'),
            write_cb, metadata_cb, error_cb, None
        )
        if ret != 0:
            log.error(f"FLAC init_file failed for {path}: error {ret}")
            return None

        while True:
            state = _flac.FLAC__stream_decoder_get_state(dec)
            if state >= FLAC__STREAM_DECODER_END_OF_STREAM:
                break
            ret = _flac.FLAC__stream_decoder_process_single(dec)
            if not ret:
                break

        _flac.FLAC__stream_decoder_finish(dec)

        if not ctx.all_pcm:
            log.error(f"No PCM data decoded from FLAC: {path}")
            return None

        rate = ctx.sample_rate
        channels = ctx.channels

        scale = 1.0 / (1 << (ctx.bits_per_sample - 1))
        float_samples = array.array('f', [s * scale for s in ctx.all_pcm])
        if channels == 2:
            n = len(float_samples) // 2
            mono = array.array('f', [0.0]) * n
            for i in range(n):
                mono[i] = (float_samples[i * 2] + float_samples[i * 2 + 1]) * 0.5
            return (mono, rate, 1)
        else:
            return (float_samples, rate, channels)

    except Exception as e:
        log.error(f"Failed to decode FLAC {path}: {e}")
        return None
    finally:
        _flac.FLAC__stream_decoder_delete(dec)
