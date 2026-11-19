# Measures what a resonance suppressor did to the test signal: run as
#   analyze.py dry.wav sections.json wet.wav [more wet.wav ...]
# and it prints, for each wet render, side by side.
import json, sys
import numpy as np
import soundfile as sf

def load(path, sr_expected):
    x, sr = sf.read(path, always_2d=True)
    assert sr == sr_expected, (path, sr)
    return x[:, :2] if x.shape[1] >= 2 else np.repeat(x, 2, 1)

def align(dry, wet, sr):
    # The lag that best lines the wet render up with the dry (a plugin's
    # delay, or a DAW's offset), from the first 20 s, by cross-correlation.
    n = min(len(dry), len(wet), 20 * sr)
    a = dry[:n].sum(1); b = wet[:n].sum(1)
    size = 1 << int(np.ceil(np.log2(2 * n)))
    c = np.fft.irfft(np.fft.rfft(b, size) * np.conj(np.fft.rfft(a, size)), size)
    lag = int(np.argmax(c[: sr]))   # wet is late by 0 to 1 s
    out = wet[lag:]
    if len(out) < len(dry):
        out = np.vstack([out, np.zeros((len(dry) - len(out), 2))])
    return out[: len(dry)], lag

def spectrum(x, sr, size=32768):
    # Averaged power spectrum (Hann windows, half overlap).
    size = min(size, 1 << int(np.floor(np.log2(len(x)))))
    hop = size // 2; w = np.hanning(size); acc = np.zeros(size // 2 + 1); k = 0
    for i in range(0, len(x) - size + 1, hop):
        acc += np.abs(np.fft.rfft(x[i:i + size] * w)) ** 2; k += 1
    return acc / max(k, 1), np.fft.rfftfreq(size, 1 / sr)

def band(spec, freqs, lo, hi):
    m = (freqs >= lo) & (freqs < hi)
    if not m.any():   # narrower than a bin: the nearest one
        return spec[np.argmin(np.abs(freqs - np.sqrt(lo * hi)))]
    return np.mean(spec[m])

def change_db(dry, wet, sr, f, width_oct=1 / 12):
    sd, fr = spectrum(dry, sr); sw, _ = spectrum(wet, sr)
    lo, hi = f / 2 ** (width_oct / 2), f * 2 ** (width_oct / 2)
    return 10 * np.log10(band(sw, fr, lo, hi) / band(sd, fr, lo, hi))

def cut_curve(dry, wet, sr, centre, octaves=1.5, step=1 / 24):
    # The change (dB) at frequencies round `centre`, 1/24-octave steps.
    sd, fr = spectrum(dry, sr); sw, _ = spectrum(wet, sr)
    out = []
    for k in np.arange(-octaves, octaves + 1e-9, step):
        f = centre * 2 ** k; lo, hi = f / 2 ** (step / 2), f * 2 ** (step / 2)
        out.append((f, 10 * np.log10(band(sw, fr, lo, hi) / band(sd, fr, lo, hi))))
    return out

def width_octaves(curve):
    # How wide the cut is: the span (octaves) where it's at least half its deepest.
    depths = np.array([d for _, d in curve]); deepest = depths.min()
    if deepest > -0.5:
        return 0.0
    inside = [f for f, d in curve if d <= deepest / 2]
    return np.log2(max(inside) / min(inside))

def bandpass_env(x, sr, f, q=8.0, ms=2.0):
    # The level (dB) of a narrow band over time, smoothed over `ms`.
    w = 2 * np.pi * f / sr; al = np.sin(w) / (2 * q)
    b = np.array([al, 0, -al]) / (1 + al); a = np.array([1, -2 * np.cos(w) / (1 + al), (1 - al) / (1 + al)])
    y = np.empty_like(x); z1 = z2 = 0.0
    for i, v in enumerate(x):
        o = b[0] * v + z1; z1 = b[1] * v - a[1] * o + z2; z2 = b[2] * v - a[2] * o; y[i] = o
    n = max(1, int(sr * ms / 1000)); p = np.convolve(y ** 2, np.ones(n) / n, "same")
    return 10 * np.log10(p + 1e-20)

def measure(dry, wet, sec, sr):
    r = {}
    get = lambda name, ch=None: (lambda s: (dry[int(s["start"] * sr):int(s["end"] * sr)], wet[int(s["start"] * sr):int(s["end"] * sr)]))(sec[name])
    mono = lambda x: x.mean(1)

    d, w = get("flat_pink")
    r["flat_level_db"] = 10 * np.log10(np.mean(w ** 2) / np.mean(d ** 2))
    sd, fr = spectrum(mono(d), sr); sw, _ = spectrum(mono(w), sr)
    worst = min((10 * np.log10(band(sw, fr, f / 2 ** (1 / 6), f * 2 ** (1 / 6)) / band(sd, fr, f / 2 ** (1 / 6), f * 2 ** (1 / 6))), f) for f in 25 * 2 ** (np.arange(0, 9.5, 1 / 3)))
    r["flat_deepest_third_octave"] = worst

    d, w = get("fixed_resonances")
    r["fixed"] = {}
    for f in (150, 400, 1000, 3500, 8000):
        curve = cut_curve(mono(d), mono(w), sr, f, octaves=1.0)
        r["fixed"][f] = {"cut_db": min(dd for _, dd in curve), "width_oct": width_octaves(curve),
                         "between_db": change_db(mono(d), mono(w), sr, f * 2 ** 0.5, 1 / 6)}

    d, w = get("sweeping_resonance")
    n = len(d); track = []
    for f in (100, 250, 500, 1000, 2000, 4000, 8000, 12000):
        t = np.log(f / 60) / np.log(14000 / 60) * n
        i0 = int(max(0, t - 0.15 * sr)); i1 = int(min(n, t + 0.15 * sr))
        track.append((f, change_db(mono(d)[i0:i1], mono(w)[i0:i1], sr, f, 1 / 6)))
    r["sweep_cut_db"] = track

    d, w = get("gated_resonance")
    ed = bandpass_env(mono(d), sr, 2500); ew = bandpass_env(mono(w), sr, 2500)
    # The cut over time, smoothed over 5 ms (both bands ring a little, and
    # the dry falls a moment before the wet when the resonance stops).
    n5 = int(0.005 * sr); gr = np.convolve(ew - ed, np.ones(n5) / n5, "same")
    def first_held (seg, ok):
        # The first moment `ok` holds for the next 5 ms.
        good = ok(seg)
        for i in range(len(seg) - n5):
            if good[i] and good[i:i + n5].all():
                return i
        return len(seg)
    attack, release, held = [], [], []
    for k in range(1, 6):   # skip the first burst (start-up)
        on = int((k + 0.25) * sr); off = on + int(0.25 * sr)
        steady = np.median(gr[off - int(0.05 * sr):off])
        held.append(steady)
        seg = gr[on:off]
        idx = first_held (seg, lambda v: v <= 0.63 * steady) if steady < -0.5 else 0
        attack.append(idx / sr * 1000)
        # Release: from the moment the resonance stops, until the cut has let go to 37%.
        after = gr[off + n5:off + int(0.7 * sr)]
        idx = first_held (after, lambda v: v >= 0.37 * steady) if steady < -0.5 else 0
        release.append((idx + n5) / sr * 1000 if steady < -0.5 else 0.0)
    r["gated"] = {"held_cut_db": float(np.median(held)), "attack_ms": float(np.median(attack)), "release_ms": float(np.median(release))}

    r["levels"] = {}
    for lv in (40, 30, 20, 10):
        d, w = get(f"level_{lv}")
        r["levels"][lv] = {f: change_db(mono(d), mono(w), sr, f) for f in (1000, 3500)}

    d, w = get("drum_loop")
    peaks_d = [np.max(np.abs(mono(d)[int(b * 0.5 * sr):int(b * 0.5 * sr) + int(0.02 * sr)])) for b in range(10)]
    peaks_w = [np.max(np.abs(mono(w)[int(b * 0.5 * sr):int(b * 0.5 * sr) + int(0.02 * sr)])) for b in range(10)]
    r["drums"] = {"hit_peak_change_db": float(np.median(20 * np.log10(np.array(peaks_w) / np.array(peaks_d)))),
                  "level_db": 10 * np.log10(np.mean(w ** 2) / np.mean(d ** 2)),
                  "snare_ring_220_db": change_db(mono(d), mono(w), sr, 220)}

    d, w = get("stereo_left_right")
    r["stereo_lr"] = {"left_1k5_db": change_db(d[:, 0], w[:, 0], sr, 1500), "left_5k_db": change_db(d[:, 0], w[:, 0], sr, 5000),
                      "right_5k_db": change_db(d[:, 1], w[:, 1], sr, 5000), "right_1k5_db": change_db(d[:, 1], w[:, 1], sr, 1500)}
    d, w = get("stereo_side_only")
    sd = (d[:, 0] - d[:, 1]) / 2; sw = (w[:, 0] - w[:, 1]) / 2; md = (d[:, 0] + d[:, 1]) / 2; mw = (w[:, 0] + w[:, 1]) / 2
    r["stereo_side"] = {"side_3k_db": change_db(sd, sw, sr, 3000), "mid_3k_db": change_db(md, mw, sr, 3000),
                        "mid_level_db": 10 * np.log10(np.mean(mw ** 2) / np.mean(md ** 2))}
    return r

def report(results):
    names = list(results)
    col = lambda v: "%9.1f" % v
    head = "%-34s" % "" + "".join("%12s" % n[:12] for n in names)
    print(head)
    def row(label, fn):
        print("%-34s" % label + "".join("%12s" % col(fn(results[n])) for n in names))
    row("delay (ms)", lambda r: r["lag_ms"])
    row("flat pink: level (dB)", lambda r: r["flat_level_db"])
    row("flat pink: deepest 1/3 oct (dB)", lambda r: r["flat_deepest_third_octave"][0])
    for f in (150, 400, 1000, 3500, 8000):
        row(f"fixed {f} Hz: cut (dB)", lambda r, f=f: r["fixed"][f]["cut_db"])
        row(f"fixed {f} Hz: width (oct)", lambda r, f=f: r["fixed"][f]["width_oct"])
    for i, f in enumerate((100, 250, 500, 1000, 2000, 4000, 8000, 12000)):
        row(f"sweep at {f} Hz: cut (dB)", lambda r, i=i: r["sweep_cut_db"][i][1])
    row("gated 2.5k: held cut (dB)", lambda r: r["gated"]["held_cut_db"])
    row("gated 2.5k: attack to 63% (ms)", lambda r: r["gated"]["attack_ms"])
    row("gated 2.5k: release to 37% (ms)", lambda r: r["gated"]["release_ms"])
    for lv in (40, 30, 20, 10):
        row(f"level -{lv}: cut at 3.5k (dB)", lambda r, lv=lv: r["levels"][lv][3500])
    row("drums: hit peaks (dB)", lambda r: r["drums"]["hit_peak_change_db"])
    row("drums: snare ring 220 Hz (dB)", lambda r: r["drums"]["snare_ring_220_db"])
    row("L/R: left 1.5k cut (dB)", lambda r: r["stereo_lr"]["left_1k5_db"])
    row("L/R: right 1.5k (dB)", lambda r: r["stereo_lr"]["right_1k5_db"])
    row("L/R: right 5k cut (dB)", lambda r: r["stereo_lr"]["right_5k_db"])
    row("side-only: side 3k cut (dB)", lambda r: r["stereo_side"]["side_3k_db"])
    row("side-only: mid 3k (dB)", lambda r: r["stereo_side"]["mid_3k_db"])

if __name__ == "__main__":
    dry_path, sections_path, wets = sys.argv[1], sys.argv[2], sys.argv[3:]
    info = json.load(open(sections_path)); sr = info["sampleRate"]; sec = {s["name"]: s for s in info["sections"]}
    dry = load(dry_path, sr); results = {}
    for path in wets:
        wet, lag = align(dry, load(path, sr), sr)
        r = measure(dry, wet, sec, sr); r["lag_ms"] = lag / sr * 1000
        results[path.split("/")[-1].rsplit(".", 1)[0]] = r
    report(results)
    json.dump(results, open("results.json", "w"), indent=1, default=float)
