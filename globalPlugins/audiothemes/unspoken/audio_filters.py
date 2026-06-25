# Audio filters for sound processing

import math

def apply_noise_gate(samples, threshold=0.02, attack_ms=5, release_ms=50, sample_rate=44100):
    attack_samples = max(1, int(attack_ms * sample_rate / 1000))
    release_samples = max(1, int(release_ms * sample_rate / 1000))
    decay = math.exp(-1.0 / (sample_rate * 0.01))
    result = list(samples)
    envelope = 0.0
    gate_open = False
    release_pos = -1
    attack_pos = -1
    for i in range(len(result)):
        raw = abs(samples[i])
        envelope = max(raw, envelope * decay)
        if envelope < threshold:
            if gate_open:
                gate_open = False
                release_pos = 0
            if release_pos >= 0:
                frac = 1.0 - release_pos / release_samples
                result[i] *= max(0.0, frac)
                release_pos += 1
            else:
                result[i] = 0.0
            attack_pos = -1
        else:
            if not gate_open:
                gate_open = True
                attack_pos = 0
            if attack_pos >= 0:
                frac = attack_pos / attack_samples
                result[i] *= min(1.0, frac)
                attack_pos += 1
            release_pos = -1
    return result

def apply_bass_boost(samples, gain_db=3.0, cutoff_hz=200, sample_rate=44100):
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * cutoff_hz / sample_rate
    if w0 >= math.pi:
        return list(samples)
    cos_w0 = math.cos(w0)
    sin_w0 = math.sin(w0)
    alpha = sin_w0 * math.sqrt(2.0) / 2.0
    sqrt_A = math.sqrt(A)
    b0 = A * ((A + 1.0) - (A - 1.0) * cos_w0 + 2.0 * sqrt_A * alpha)
    b1 = 2.0 * A * ((A - 1.0) - (A + 1.0) * cos_w0)
    b2 = A * ((A + 1.0) - (A - 1.0) * cos_w0 - 2.0 * sqrt_A * alpha)
    a0 = (A + 1.0) + (A - 1.0) * cos_w0 + 2.0 * sqrt_A * alpha
    a1 = -2.0 * ((A - 1.0) + (A + 1.0) * cos_w0)
    a2 = (A + 1.0) + (A - 1.0) * cos_w0 - 2.0 * sqrt_A * alpha
    b0 /= a0
    b1 /= a0
    b2 /= a0
    a1 /= a0
    a2 /= a0
    x1 = x2 = y1 = y2 = 0.0
    result = [0.0] * len(samples)
    for i, x in enumerate(samples):
        y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        result[i] = y
        x2, x1 = x1, x
        y2, y1 = y1, y
    return result
