# Audio filters for sound processing

import math

def apply_noise_gate(samples, threshold=0.02, attack_ms=5, release_ms=50, sample_rate=44100):
    gate_open = True
    attack_samples = int(attack_ms * sample_rate / 1000)
    release_samples = int(release_ms * sample_rate / 1000)
    result = list(samples)
    envelope = 0.0
    for i in range(len(result)):
        envelope = max(abs(result[i]), envelope * 0.999)
        if envelope < threshold:
            if gate_open:
                gate_open = False
                release_start = max(0, i - release_samples)
                for j in range(release_start, i):
                    frac = (j - release_start) / release_samples
                    result[j] *= frac
            result[i] = 0.0
        else:
            if not gate_open:
                gate_open = True
                attack_end = min(len(result), i + attack_samples)
                for j in range(i, attack_end):
                    frac = 1.0 - (j - i) / attack_samples
                    result[j] *= frac
    return result

def apply_bass_boost(samples, gain_db=3.0, cutoff_hz=200, sample_rate=44100):
    gain = 10.0 ** (gain_db / 20.0)
    w0 = 2.0 * math.pi * cutoff_hz / sample_rate
    alpha = math.sin(w0) * math.sqrt(2.0) / 2.0
    cos_w0 = math.cos(w0)
    b0 = 1.0 + alpha * gain
    b1 = -2.0 * cos_w0
    b2 = 1.0 - alpha * gain
    a0 = 1.0 + alpha / gain
    a1 = -2.0 * cos_w0
    a2 = 1.0 - alpha / gain
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
