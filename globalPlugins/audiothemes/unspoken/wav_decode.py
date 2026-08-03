# Robust native WAV decoder.
# Supports: PCM 8/16/24/32-bit, IEEE float 32/64-bit, WAVE_FORMAT_EXTENSIBLE,
# MS ADPCM (via ms_adpcm), A-law, and mu-law. Channel counts are normalized to
# mono (1) or stereo (2). Unsupported formats return None so FFmpeg can try.

import struct
from array import array
from logHandler import log


def _normalize_channels(float_samples, channels):
    """Return (samples, channels) with channels normalized to 1 or 2."""
    if channels <= 1:
        return float_samples, 1
    if channels == 2:
        return float_samples, 2
    n = len(float_samples) // channels
    mono = array('f', [0.0]) * n
    for c in range(channels):
        for i in range(n):
            mono[i] += float_samples[i * channels + c]
    inv = 1.0 / channels
    return array('f', (s * inv for s in mono)), 1


def _decode_pcm_8(frames):
    return array('f', ((s - 128) / 128.0 for s in frames))


def _decode_pcm_16(frames):
    frames = frames[:len(frames) & ~1]
    arr = array('h')
    arr.frombytes(frames)
    return array('f', (s / 32768.0 for s in arr))


def _decode_pcm_24(frames):
    count = len(frames) // 3
    out = array('f', [0.0]) * count
    for i in range(count):
        off = i * 3
        three_bytes = frames[off:off + 3]
        if three_bytes[2] < 128:
            padded = three_bytes + b'\x00'
        else:
            padded = three_bytes + b'\xff'
        s = struct.unpack('<i', padded)[0]
        out[i] = s / 8388608.0
    return out


def _decode_pcm_32(frames):
    frames = frames[:len(frames) & ~3]
    arr = array('i')
    arr.frombytes(frames)
    return array('f', (s / 2147483648.0 for s in arr))


def _decode_float32(frames):
    frames = frames[:len(frames) & ~3]
    arr = array('f')
    arr.frombytes(frames)
    return arr


def _decode_float64(frames):
    frames = frames[:len(frames) & ~7]
    arr = array('d')
    arr.frombytes(frames)
    return arr


def _decode_alaw(frames):
    out = array('f', [0.0]) * len(frames)
    for i, b in enumerate(frames):
        a = b ^ 0x55
        val = (a & 0x0F) << 4
        seg = (a & 0x70) >> 4
        if seg == 0:
            val += 8
        else:
            val = (val + 0x108) << (seg - 1)
        if a & 0x80:
            val = -val
        out[i] = val / 32768.0
    return out


def _decode_ulaw(frames):
    out = array('f', [0.0]) * len(frames)
    for i, b in enumerate(frames):
        c = (~b) & 0xFF
        val = ((c & 0x0F) << 3) + 0x84
        val <<= (c & 0x70) >> 4
        val -= 0x84
        if not (c & 0x80):
            val = -val
        out[i] = val / 32768.0
    return out


def decode_wav_to_float(path):
    """Decode a WAV file to float32 PCM.

    Returns (float_array, sample_rate, channels) or None on failure.
    """
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except Exception as e:
        log.error(f"Failed to read {path}: {e}")
        return None
    if len(raw) < 44 or raw[:4] != b'RIFF' or raw[8:12] != b'WAVE':
        return None

    fmt_tag = None
    channels = 1
    sample_rate = 44100
    bits = 16
    frames = b''
    pos = 12
    total = len(raw)
    while pos + 8 <= total:
        cid = raw[pos:pos + 4]
        csize = struct.unpack_from('<I', raw, pos + 4)[0]
        body = raw[pos + 8:pos + 8 + csize]
        if cid == b'fmt ':
            if len(body) >= 16:
                fmt_tag, channels, sample_rate, _byte_rate, _block_align, bits = struct.unpack_from('<HHIIHH', body, 0)
                if fmt_tag == 0xFFFE and len(body) >= 40:
                    # WAVE_FORMAT_EXTENSIBLE: the first 4 bytes of the subformat
                    # GUID hold the real format tag.
                    sub = struct.unpack_from('<I', body, 24)[0]
                    fmt_tag = sub & 0xFFFF
        elif cid == b'data':
            frames = body
            break
        pos += 8 + csize + (csize & 1)
        if csize > total:
            break

    if fmt_tag is None:
        return None

    if fmt_tag == 1:  # PCM
        if bits == 8:
            samples = _decode_pcm_8(frames)
        elif bits == 16:
            samples = _decode_pcm_16(frames)
        elif bits == 24:
            samples = _decode_pcm_24(frames)
        elif bits == 32:
            samples = _decode_pcm_32(frames)
        else:
            return None
    elif fmt_tag == 3:  # IEEE float
        if bits == 32:
            samples = _decode_float32(frames)
        elif bits == 64:
            samples = _decode_float64(frames)
        else:
            return None
    elif fmt_tag == 2:  # MS ADPCM
        try:
            from . import ms_adpcm
            return ms_adpcm.decode_ms_adpcm_to_float(path)
        except Exception as e:
            log.debugWarning(f"MS ADPCM decode failed for {path}: {e}")
            return None
    elif fmt_tag == 6:  # A-law
        samples = _decode_alaw(frames)
    elif fmt_tag == 7:  # mu-law
        samples = _decode_ulaw(frames)
    else:
        return None

    samples, channels = _normalize_channels(samples, channels)
    return (samples, sample_rate, channels)
