# Measures what an EQ did to the test signal (make_eq_signal.py):
#   python3 measure_eq.py dry.wav sections.json wet.wav [more.wav ...]
# prints, for each render: its delay, the response (dB) at chosen frequencies
# from the click and from the sweep, which sides it works on, and for dynamic
# bands the change at 1 kHz by level and its timing. Writes each render's
# response curve (1/48 octave, 20 Hz to 20 kHz) to curves.json.
import json, sys
import numpy as np
import soundfile as sf

def load(path, sr):
    x, rate = sf.read(path, always_2d=True)
    assert rate == sr, (path, rate)
    return x[:, :2] if x.shape[1] >= 2 else np.repeat(x, 2, 1)

def lag_of(dry, wet, sr, sec):
    # The delay that best lines up the sweep (0 to 1 s), by cross-correlation.
    a = dry[int(sec["start"] * sr):int(sec["end"] * sr)].sum(1); b = wet[int(sec["start"] * sr):int(sec["end"] * sr) + sr].sum(1)
    size = 1 << int(np.ceil(np.log2(len(a) + len(b))))
    c = np.fft.irfft(np.fft.rfft(b, size) * np.conj(np.fft.rfft(a, size)), size)
    return int(np.argmax(np.abs(c[:sr])))

GRID = 20 * 2 ** (np.arange(0, 10 * 48 + 1) / 48)   # 20 Hz to 20.5 kHz, 1/48 octave
GRID = GRID[GRID <= 20000]

def response_from(dry_seg, wet_seg, sr, smooth_oct=0.0):
    # Complex response on GRID (wet over dry), optionally smoothed in power over smooth_oct.
    n = 1 << int(np.ceil(np.log2(max(len(dry_seg), 1 << 16))))
    D = np.fft.rfft(dry_seg, n); W = np.fft.rfft(wet_seg, n); f = np.fft.rfftfreq(n, 1 / sr)
    if smooth_oct <= 0:
        H = W / np.where(np.abs(D) < 1e-12, 1e-12, D)
        return np.interp(GRID, f, H.real) + 1j * np.interp(GRID, f, H.imag)
    out = []
    for g in GRID:
        m = (f >= g * 2 ** (-smooth_oct / 2)) & (f <= g * 2 ** (smooth_oct / 2))
        out.append(np.sqrt(np.sum(np.abs(W[m]) ** 2) / max(np.sum(np.abs(D[m]) ** 2), 1e-30)))
    return np.array(out, dtype=complex)

def db(h): return 20 * np.log10(np.maximum(np.abs(h), 1e-12))

def band_level(x, sr, f, q=8.0, ms=2.0):
    w = 2 * np.pi * f / sr; al = np.sin(w) / (2 * q)
    from scipy.signal import lfilter
    y = lfilter([al / (1 + al), 0, -al / (1 + al)], [1, -2 * np.cos(w) / (1 + al), (1 - al) / (1 + al)], x)
    k = max(1, int(sr * ms / 1000)); return 10 * np.log10(np.convolve(y ** 2, np.ones(k) / k, "same") + 1e-20)

def measure(dry, wet, sec, sr):
    r = {}
    lag = lag_of(dry, wet, sr, sec["sweep"]); r["lag_samples"] = lag
    w = np.vstack([wet[lag:], np.zeros((lag, 2))])[: len(dry)]
    cut = lambda x, name: x[int(sec[name]["start"] * sr):int(sec[name]["end"] * sr)]
    # The click: left and right channels.
    imp = {c: response_from(cut(dry, "impulse")[:, c], cut(w, "impulse")[:, c], sr) for c in (0, 1)}
    r["impulse_db"] = {"L": db(imp[0]).tolist(), "R": db(imp[1]).tolist()}
    r["impulse_phase"] = np.unwrap(np.angle(imp[0])).tolist()
    # Which sides: the left click's output on each side, the right click's likewise.
    L = cut(dry, "impulse_left")[:, 0]
    r["sides"] = {"LL": db(response_from(L, cut(w, "impulse_left")[:, 0], sr)).tolist(),
                  "LR": db(response_from(L, cut(w, "impulse_left")[:, 1], sr)).tolist(),
                  "RR": db(response_from(cut(dry, "impulse_right")[:, 1], cut(w, "impulse_right")[:, 1], sr)).tolist()}
    # The sweep (1/24 octave smoothing).
    r["sweep_db"] = db(response_from(cut(dry, "sweep").mean(1), cut(w, "sweep").mean(1), sr, 1 / 24)).tolist()
    # Dynamic: the change at 1 kHz at each level, and its timing on the gated tone.
    r["levels"] = {}
    for lv in (40, 30, 20, 10):
        d = cut(dry, f"level_{lv}").mean(1); x = cut(w, f"level_{lv}").mean(1); h = len(d) // 2
        r["levels"][lv] = float(np.mean(band_level(x[h:], sr, 1000)) - np.mean(band_level(d[h:], sr, 1000)))
    d = cut(dry, "gated").mean(1); x = cut(w, "gated").mean(1)
    gr = band_level(x, sr, 1000) - band_level(d, sr, 1000); n5 = int(0.005 * sr); gr = np.convolve(gr, np.ones(n5) / n5, "same")
    att, rel, held = [], [], []
    for k in range(1, 6):
        on = int((k + 0.25) * sr); off = on + int(0.25 * sr)
        # How the change at 1 kHz moves when the tone comes and goes (a static band doesn't move it).
        base = np.median(gr[off + int(0.45 * sr):off + int(0.7 * sr)]); steady = np.median(gr[off - int(0.05 * sr):off]) - base
        held.append(steady)
        if abs(steady) < 1.5:   # under 1.5 dB: the narrow 1 kHz filter hears tone and noise a little differently, not movement
            att.append(0.0); rel.append(0.0); continue
        seg = gr[on:off] - base; good = np.abs(seg) >= 0.63 * abs(steady)
        att.append(next((i for i in range(len(seg) - n5) if good[i:i + n5].all()), len(seg)) / sr * 1000)
        after = gr[off + n5:off + int(0.7 * sr)] - base; back = np.abs(after) <= 0.37 * abs(steady)
        rel.append((next((i for i in range(len(after) - n5) if back[i:i + n5].all()), len(after)) + n5) / sr * 1000)
    r["gated"] = {"held_db": float(np.median(held)), "attack_ms": float(np.median(att)), "release_ms": float(np.median(rel))}
    return r

SHOW = [30, 50, 100, 200, 500, 700, 1000, 1400, 2000, 5000, 8000, 10000, 15000, 18000, 20000]
def at(curve, f): return float(np.interp(np.log(f), np.log(GRID), curve))

if __name__ == "__main__":
    dry_path, sec_path, wets = sys.argv[1], sys.argv[2], sys.argv[3:]
    info = json.load(open(sec_path)); sr = info["sampleRate"]; sec = {s["name"]: s for s in info["sections"]}
    dry = load(dry_path, sr); results = {}
    for p in wets:
        results[p.split("/")[-1].rsplit(".", 1)[0]] = measure(dry, load(p, sr), sec, sr)
    names = list(results); col = lambda v: "%9.2f" % v
    print("%-26s" % "" + "".join("%12s" % n[:12] for n in names))
    row = lambda label, fn: print("%-26s" % label + "".join("%12s" % col(fn(results[n])) for n in names))
    row("delay (samples)", lambda r: r["lag_samples"])
    for f in SHOW: row(f"click {f} Hz (dB)", lambda r, f=f: at(r["impulse_db"]["L"], f))
    for f in (100, 1000, 10000): row(f"sweep {f} Hz (dB)", lambda r, f=f: at(r["sweep_db"], f))
    row("right side at 1 kHz (dB)", lambda r: at(r["impulse_db"]["R"], 1000))
    row("left click on right (dB)", lambda r: at(r["sides"]["LR"], 1000))
    for lv in (40, 30, 20, 10): row(f"1 kHz at -{lv} dBFS (dB)", lambda r, lv=lv: r["levels"][lv])
    row("gated: moves by (dB)", lambda r: r["gated"]["held_db"])
    row("gated: attack (ms)", lambda r: r["gated"]["attack_ms"])
    row("gated: release (ms)", lambda r: r["gated"]["release_ms"])
    json.dump({"grid": GRID.tolist(), "renders": {n: {"L": r["impulse_db"]["L"], "phase": r["impulse_phase"]} for n, r in results.items()}},
              open("curves.json", "w"))
