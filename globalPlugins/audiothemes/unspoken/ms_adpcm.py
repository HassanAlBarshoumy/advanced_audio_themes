import struct
from array import array

# MS ADPCM nibble -> delta multiplier (FFmpeg ff_adpcm_AdaptationTable)
_ADAPTATION_TABLE = (
	230, 230, 230, 230, 307, 409, 512, 614,
	768, 614, 512, 409, 307, 230, 230, 230,
)
# Predictor coefficients, quartered to match FFmpeg's int8 tables
# (equivalent to the standard table {256,512,0,192,240,460,392} / {0,-256,0,64,0,-208,-232}
#  divided by 4 with a /64 predictor instead of /256).
_COEFF1 = (64, 128, 0, 48, 60, 115, 98)
_COEFF2 = (0, -64, 0, 16, 0, -52, -58)


def _clip16(v):
	return -32768 if v < -32768 else (32767 if v > 32767 else v)


def _trunc_div_by_64(a):
	# C integer division truncates toward zero; Python // floors.
	if a >= 0:
		return a // 64
	return -((-a) // 64)


def _expand_nibble(state, nibble):
	# Mirrors FFmpeg adpcm_ms_expand_nibble exactly.
	predictor = _trunc_div_by_64(state[0] * state[2] + state[1] * state[3])
	predictor += ((nibble - 0x10) if (nibble & 0x08) else nibble) * state[4]
	sample = _clip16(predictor)
	state[1] = state[0]
	state[0] = sample
	state[4] = (state[4] * _ADAPTATION_TABLE[nibble]) >> 8
	if state[4] < 16:
		state[4] = 16
	return sample


def _decode_block(block, channels, out):
	pos = 0
	states = []
	if channels == 2:
		# Header: predictor x2, idelta x2, sample1 x2, sample2 x2
		if len(block) < 14:
			return False
		for _ in range(2):
			predictor = block[pos]
			pos += 1
			if predictor > 6:
				return False
			states.append([0, 0, _COEFF1[predictor], _COEFF2[predictor], 0])
		for s in states:
			s[4] = struct.unpack_from("<h", block, pos)[0]
			pos += 2
		for s in states:
			s[0] = struct.unpack_from("<h", block, pos)[0]
			pos += 2
		for s in states:
			s[1] = struct.unpack_from("<h", block, pos)[0]
			pos += 2
		# Emit sample2 first, then sample1
		out.append(states[0][1] / 32768.0)
		out.append(states[1][1] / 32768.0)
		out.append(states[0][0] / 32768.0)
		out.append(states[1][0] / 32768.0)
		# Nibbles: byte >> 4 for ch0, byte & 0x0F for ch1
		for byte in block[pos:]:
			out.append(_expand_nibble(states[0], byte >> 4) / 32768.0)
			out.append(_expand_nibble(states[1], byte & 0x0F) / 32768.0)
		return True
	# Mono (and fallback for other channel counts: sequential per-channel header)
	if len(block) < 8 * channels:
		return False
	for _ in range(channels):
		predictor = block[pos]
		pos += 1
		if predictor > 6:
			return False
		s = [0, 0, _COEFF1[predictor], _COEFF2[predictor], 0]
		s[4] = struct.unpack_from("<h", block, pos)[0]
		pos += 2
		s[0] = struct.unpack_from("<h", block, pos)[0]
		pos += 2
		s[1] = struct.unpack_from("<h", block, pos)[0]
		pos += 2
		states.append(s)
	for s in states:
		out.append(s[1] / 32768.0)
		out.append(s[0] / 32768.0)
	for byte in block[pos:]:
		out.append(_expand_nibble(states[0], byte >> 4) / 32768.0)
		if channels == 1:
			out.append(_expand_nibble(states[0], byte & 0x0F) / 32768.0)
	return True


def decode_ms_adpcm_to_float(path):
	"""Decode a WAV file with MS ADPCM compression (format tag 2) to float32 PCM.

	Returns (float_array, sample_rate, channels) or None on failure.
	"""
	with open(path, "rb") as f:
		raw = f.read()
	if len(raw) < 44:
		return None

	# Parse chunks
	pos = 12
	fmt_data = None
	data_chunk = None
	while pos + 8 <= len(raw):
		cid = raw[pos:pos + 4]
		csize = struct.unpack_from("<I", raw, pos + 4)[0]
		body_start = pos + 8
		body = raw[body_start:body_start + csize]
		if cid == b"fmt " and len(body) >= 16:
			fmt_data = body
		elif cid == b"data":
			data_chunk = body
			break
		pos = body_start + csize + (csize & 1)

	if fmt_data is None or data_chunk is None:
		return None

	fmt_tag, channels, sample_rate, byte_rate, block_align, bits = struct.unpack_from("<HHIIHH", fmt_data, 0)
	if fmt_tag != 2:
		return None
	extra = fmt_data[16:]
	if len(extra) < 2:
		return None
	samples_per_block = struct.unpack_from("<H", extra, 0)[0]

	if samples_per_block < 2 or block_align < 8 * channels:
		return None

	output = array("f")
	remaining = len(data_chunk)
	off = 0
	while remaining > 0:
		block = data_chunk[off:off + block_align]
		min_header = 14 if channels == 2 else 8 * channels
		if len(block) < min_header:
			break
		if not _decode_block(block, channels, output):
			return None
		off += block_align
		remaining -= block_align

	return (output, sample_rate, channels)
