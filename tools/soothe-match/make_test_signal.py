# The soothe comparison test signal: one stereo file of sections (48 kHz,
# or the rate given as a third argument, e.g. 44100),
# each built to show one thing about how a resonance suppressor behaves.
import json, sys
import numpy as np
import soundfile as sf

SR = int(sys.argv[3]) if len(sys.argv) > 3 else 48000
rng = np.random.default_rng(20261119)

def pink(n):
    # Voss-McCartney-ish via FFT shaping: exact -3 dB/octave.
    white = rng.standard_normal(n)
    spec = np.fft.rfft(white)
    f = np.fft.rfftfreq(n, 1 / SR)
    f[0] = f[1]
    spec /= np.sqrt(f)
    x = np.fft.irfft(spec, n)
    return x / np.sqrt(np.mean(x ** 2))

def peak_coeffs(f0, gain_db, q):
    a = 10 ** (gain_db / 40); w = 2 * np.pi * f0 / SR; al = np.sin(w) / (2 * q)
    b = np.array([1 + al * a, -2 * np.cos(w), 1 - al * a]); aa = np.array([1 + al / a, -2 * np.cos(w), 1 - al / a])
    return b / aa[0], aa / aa[0]

def biquad(x, b, a, z=None):
    y = np.empty_like(x); z1, z2 = (0.0, 0.0) if z is None else z
    for i, v in enumerate(x):
        o = b[0] * v + z1; z1 = b[1] * v - a[1] * o + z2; z2 = b[2] * v - a[2] * o; y[i] = o
    return y, (z1, z2)

def peaks(x, specs):
    for f0, g, q in specs:
        b, a = peak_coeffs(f0, g, q); x, _ = biquad(x, b, a)
    return x

def rms_to(x, dbfs):
    return x * (10 ** (dbfs / 20) / np.sqrt(np.mean(x ** 2)))

def seconds(s): return int(round(s * SR))

sections, parts, t = [], [], 0.0
def add(name, left, right, note):
    global t
    sections.append({"name": name, "start": round(t, 6), "end": round(t + len(left) / SR, 6), "note": note})
    parts.append(np.stack([left, right], 1)); t += len(left) / SR
def gap(s):
    global t
    parts.append(np.zeros((seconds(s), 2))); t += s

BASE = -20.0
FIXED = [(150, 9, 8), (400, 6, 1), (1000, 12, 8), (3500, 18, 8), (8000, 9, 8)]

gap(1.0)
x = rms_to(pink(seconds(4)), BASE); add("flat_pink", x, x, "pink noise, no resonances: what it does to an even sound")
gap(0.5)
x = rms_to(peaks(pink(seconds(6)), FIXED), BASE); add("fixed_resonances", x, x, "pink with narrow peaks 150 Hz +9, 1 kHz +12, 3.5 kHz +18, 8 kHz +9 (Q 8) and a wide one 400 Hz +6 (Q 1)")
gap(0.5)
# A narrow +12 dB peak gliding 60 Hz -> 14 kHz over 12 s (coefficients updated every 32 samples).
n = seconds(12); base = pink(n); y = np.empty(n); z = (0.0, 0.0)
for i in range(0, n, 32):
    f0 = 60 * (14000 / 60) ** (i / n); b, a = peak_coeffs(f0, 12, 8)
    y[i:i + 32], z = biquad(base[i:i + 32], b, a, z)
x = rms_to(y, BASE); add("sweeping_resonance", x, x, "pink with a narrow +12 dB peak gliding 60 Hz to 14 kHz (log) over 12 s")
gap(0.5)
# A 2.5 kHz +15 dB peak switched on for 250 ms every second (1 ms fades): attack and release.
n = seconds(6); base = pink(n); b, a = peak_coeffs(2500, 15, 8); res, _ = biquad(base, b, a)
gate = np.zeros(n)
for k in range(6):
    s0 = seconds(k + 0.25); gate[s0:s0 + seconds(0.25)] = 1
ramp = np.ones(seconds(0.001)) / seconds(0.001); gate = np.convolve(gate, ramp, "same")
y = base + (res - base) * gate
x = rms_to(base, BASE) / np.sqrt(np.mean(base ** 2)) * 1.0
scale = 10 ** (BASE / 20) / np.sqrt(np.mean(base ** 2)); x = y * scale
add("gated_resonance", x, x, "pink; a 2.5 kHz +15 dB peak on for 250 ms every second (from 0.25 s): how fast it grabs and lets go")
gap(0.5)
# The fixed resonances at four levels: does it depend on how loud the track is?
for level in (-40, -30, -20, -10):
    x = rms_to(peaks(pink(seconds(2)), FIXED), level)
    add(f"level_{abs(level)}", x, x, f"the fixed resonances at {level} dBFS RMS")
gap(0.5)
# A synthetic drum loop at 120 BPM (kick, snare with a 220 Hz ring, hats).
n = seconds(5); y = np.zeros(n)
for beat in range(10):
    s0 = seconds(beat * 0.5); tt = np.arange(seconds(0.4)) / SR
    if beat % 2 == 0:   # kick
        ph = 2 * np.pi * np.cumsum(45 + 75 * np.exp(-tt * 30)) / SR; seg = np.sin(ph) * np.exp(-tt * 8)
    else:               # snare: noise burst plus a ringing 220 Hz
        seg = rng.standard_normal(len(tt)) * np.exp(-tt * 18) * 0.6 + np.sin(2 * np.pi * 220 * tt) * np.exp(-tt * 6) * 0.5
    y[s0:s0 + len(seg)] += seg[: n - s0]
for h in range(20):   # hats, eighth notes
    s0 = seconds(h * 0.25); tt = np.arange(seconds(0.05)) / SR
    hat = np.diff(rng.standard_normal(len(tt) + 1)) * np.exp(-tt * 80) * 0.15; y[s0:s0 + len(hat)] += hat[: n - s0]
x = y * (10 ** (-6 / 20) / np.max(np.abs(y))); add("drum_loop", x, x, "synthetic drums at 120 BPM, peaks -6 dBFS: transients and a ringing snare")
gap(0.5)
# Stereo: a different resonance on each side, then one only in the sides (L-R).
base = pink(seconds(4))
l = rms_to(peaks(base.copy(), [(1500, 12, 8)]), BASE); r = rms_to(peaks(base.copy(), [(5000, 12, 8)]), BASE)
add("stereo_left_right", l, r, "the same noise both sides; left has a 1.5 kHz +12 peak, right a 5 kHz +12 peak")
gap(0.5)
mid = rms_to(pink(seconds(4)), BASE); b, a = peak_coeffs(3000, 24, 12); side, _ = biquad(pink(seconds(4)), b, a)
side = rms_to(side - pink(seconds(4)) * 0, BASE - 6)
add("stereo_side_only", mid + side, mid - side, "an even sound in the middle; a narrow 3 kHz resonance only in the sides (L-R)")
gap(2.0)

out = np.concatenate(parts)
# The whole file scaled together to peak at -1 dBFS (the sections keep
# their levels relative to each other); the real levels are recorded.
trim_db = -1.0 - 20 * np.log10(np.max(np.abs(out)))
out *= 10 ** (trim_db / 20)
peak = np.max(np.abs(out))
sf.write(sys.argv[1], out.astype(np.float32), SR, subtype="PCM_24")
json.dump({"sampleRate": SR, "trimDb": round(trim_db, 3), "sections": sections, "length": round(t, 6)}, open(sys.argv[2], "w"), indent=1)
print("length %.2f s, peak %.2f dBFS, trim %.2f dB" % (t, 20 * np.log10(peak), trim_db))
for s in sections: print("%6.2f - %6.2f  %s" % (s["start"], s["end"], s["name"]))
