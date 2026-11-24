# The EQ comparison test signal (ECHELON against FabFilter Pro-Q 4): one stereo
# file of sections, each built to measure one thing.
#   python3 make_eq_signal.py out.wav sections.json [rate]     (44100 by default)
# Deterministic: it always rebuilds bit-identically.
import json, sys
import numpy as np
import soundfile as sf

SR = int(sys.argv[3]) if len(sys.argv) > 3 else 44100
rng = np.random.default_rng(20261124)

def seconds(s): return int(round(s * SR))

def pink(n):
    spec = np.fft.rfft(rng.standard_normal(n)); f = np.fft.rfftfreq(n, 1 / SR); f[0] = f[1]
    x = np.fft.irfft(spec / np.sqrt(f), n); return x / np.sqrt(np.mean(x ** 2))

def db(v): return 10 ** (v / 20)

sections, parts, t = [], [], 0.0
def add(name, left, right, note):
    global t
    sections.append({"name": name, "start": round(t, 6), "end": round(t + len(left) / SR, 6), "note": note})
    parts.append(np.stack([left, right], 1)); t += len(left) / SR
def gap(s):
    global t
    parts.append(np.zeros((seconds(s), 2))); t += s

# 1. A click on both sides: an EQ's whole response (level and phase) in one go.
gap(1.0)
click = np.zeros(seconds(1.5)); click[0] = 0.5
add("impulse", click, click, "one sample at -6 dBFS on both sides, then 1.5 s for the tail")
# 2. A click on the left alone, then on the right alone: which side a band works on (left / right / mid / side).
add("impulse_left", click, np.zeros_like(click), "a click on the left only")
add("impulse_right", np.zeros_like(click), click, "a click on the right only")
gap(0.5)
# 3. A slow sine sweep, 20 Hz to 20 kHz: the response again, measured another way (and any distortion).
n = seconds(8.0); tt = np.arange(n) / SR; f1, f2 = 20.0, 20000.0; k = np.log(f2 / f1)
sweep = db(-12) * np.sin(2 * np.pi * f1 * 8.0 / k * (np.exp(tt / 8.0 * k) - 1))
fade = seconds(0.01); sweep[:fade] *= np.linspace(0, 1, fade); sweep[-fade:] *= np.linspace(1, 0, fade)
add("sweep", sweep, sweep, "sine sweep 20 Hz to 20 kHz over 8 s at -12 dBFS")
gap(1.0)
# 4. Pink noise: the response on a steady, music-like sound.
x = pink(seconds(4)) * db(-20); add("pink", x, x, "pink noise at -20 dBFS RMS")
gap(0.5)
# 5. For dynamic bands: pink noise with a 1 kHz tone at four levels (where it starts working).
for level in (-40, -30, -20, -10):
    n = seconds(2.0); tt = np.arange(n) / SR
    x = pink(n) * db(level - 12) + db(level) * np.sqrt(2) * np.sin(2 * np.pi * 1000 * tt)
    add(f"level_{abs(level)}", x, x, f"a 1 kHz tone at {level} dBFS RMS over pink noise 12 dB lower")
gap(0.5)
# 6. For dynamic bands: the 1 kHz tone switched on for 250 ms every second (how fast it grabs and lets go).
n = seconds(6.0); tt = np.arange(n) / SR; gate = np.zeros(n)
for i in range(6):
    s0 = seconds(i + 0.25); gate[s0:s0 + seconds(0.25)] = 1
ramp = np.ones(seconds(0.001)) / seconds(0.001); gate = np.convolve(gate, ramp, "same")
x = pink(n) * db(-32) + gate * db(-12) * np.sqrt(2) * np.sin(2 * np.pi * 1000 * tt)
add("gated", x, x, "pink at -32 dBFS; a 1 kHz tone at -12 dBFS on for 250 ms every second")
gap(2.0)

out = np.concatenate(parts).astype(np.float32)
assert np.max(np.abs(out)) < 0.9
sf.write(sys.argv[1], out, SR, subtype="FLOAT")
json.dump({"sampleRate": SR, "sections": sections, "length": round(t, 6)}, open(sys.argv[2], "w"), indent=1)
print(f"length {t:.2f} s, peak {20 * np.log10(np.max(np.abs(out))):.2f} dBFS")
for s in sections: print(f"  {s['start']:6.2f} - {s['end']:6.2f}  {s['name']}")
