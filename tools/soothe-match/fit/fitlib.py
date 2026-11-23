# Fitting DOMINION REFINED to the soothe 3 renders: render, measure, compare.
import json, os, subprocess, sys, tempfile, concurrent.futures as cf
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import measure as M

S = os.environ["SOOTHE_DIR"]   # the test file, sections_44k.json and renders/R00.wav ...
DRY = f"{S}/soothe_test_44k.wav"
BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../build/tests/ParagonX1Tests")
INFO = json.load(open(f"{S}/sections_44k.json")); SR = INFO["sampleRate"]
SEC = {s["name"]: s for s in INFO["sections"]}
DRYX = M.load(DRY, SR)

# Each soothe render, and DOMINION's settings for it (soothe's 0-10 as 0-100; depth as is).
CASES = {
 "R01": "", "R02": "lookahead=0", "R03": "depth=2.5", "R04": "depth=7.5", "R05": "depth=10",
 "R06": "detail=0", "R07": "detail=100", "R08": "attack=0", "R09": "attack=100",
 "R10": "release=0", "R11": "release=100", "R12": "mode=hard", "R13": "mode=hard depth=10",
 "R14": "stereo=ms link=0", "R15": "link=0", "R16": "depth=1", "R17": "detail=25", "R18": "detail=75",
 "R19": "attack=25", "R20": "release=60", "R21": "mode=hard depth=2.5", "R22": "mode=hard depth=7.5",
 "R23": "delta=1", "R24": "mix=50", "R25": "lookahead=0 depth=10", "R26": "lookahead=0 attack=0", "R27": "curve=flat",
}

_soothe = {}
def soothe(name):
    if name not in _soothe:
        cache = f"{S}/soothe_{name}.json"
        if os.path.exists(cache):
            _soothe[name] = json.load(open(cache))
        else:
            wet, lag = M.align(DRYX, M.load(f"{S}/renders/{name}.wav", SR), SR)
            r = M.measure(DRYX, wet, SEC, SR); r["lag_ms"] = lag / SR * 1000
            r = json.loads(json.dumps(r, default=float))
            json.dump(r, open(cache, "w")); _soothe[name] = r
    return _soothe[name]

def render(names, tuning, workdir, procs=4):
    # Renders the cases through DOMINION (in `procs` processes), returns {name: path}.
    os.makedirs(workdir, exist_ok=True)
    groups = [names[i::procs] for i in range(procs)]
    tun = ",".join(f"{k}={v:.6g}" for k, v in tuning.items())
    def run(group, i):
        if not group: return
        jobs = f"{workdir}/jobs{i}.txt"
        open(jobs, "w").write("\n".join(f"{workdir}/{n}.wav {CASES[n]}" for n in group) + "\n")
        env = dict(os.environ, PARAGON_DOMFIT_IN=DRY, PARAGON_DOMFIT_JOBS=jobs, PARAGON_DOMFIT_TUNING=tun)
        p = subprocess.run([BIN, "[domfit]"], env=env, capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(p.stdout[-3000:] + p.stderr[-2000:])
    with cf.ThreadPoolExecutor(procs) as ex:
        list(ex.map(run, groups, range(procs)))
    return {n: f"{workdir}/{n}.wav" for n in names}

def measure_file(path):
    wet, lag = M.align(DRYX, M.load(path, SR), SR)
    r = M.measure(DRYX, wet, SEC, SR); r["lag_ms"] = lag / SR * 1000
    return json.loads(json.dumps(r, default=float))

def features(r, timing=True):
    # The numbers compared (dB, or 10 x log2 of times so a factor of two is "10").
    f = {}
    f["flat_level"] = r["flat_level_db"]; f["flat_deep"] = r["flat_deepest_third_octave"][0]
    for k, v in r["fixed"].items():
        f[f"fix{k}"] = v["cut_db"]; f[f"fixw{k}"] = 3 * v["width_oct"]
    for fr, v in r["sweep_cut_db"]: f[f"sw{int(fr)}"] = v
    f["held"] = r["gated"]["held_cut_db"]
    if timing:
        ok = r["gated"]["held_cut_db"] < -0.8
        f["att"] = 10 * np.log2(max(r["gated"]["attack_ms"], 1.0)) if ok else None
        f["rel"] = 10 * np.log2(max(r["gated"]["release_ms"], 1.0)) if ok and r["gated"]["release_ms"] < 650 else None
    for lv, v in r["levels"].items(): f[f"lv{lv}"] = v["3500"] if "3500" in v else v[3500]
    f["drum_pk"] = 3 * r["drums"]["hit_peak_change_db"]; f["snare"] = r["drums"]["snare_ring_220_db"]
    for k, v in r["stereo_lr"].items(): f["lr_" + k] = v
    for k, v in r["stereo_side"].items(): f["side_" + k] = v
    return f

def compare(a, b):
    fa, fb = features(a), features(b); out = {}
    for k in fa:
        if fa[k] is None or fb.get(k) is None: continue
        out[k] = fa[k] - fb[k]
    return out

def loss(names, tuning, workdir, verbose=False):
    paths = render(names, tuning, workdir)
    with cf.ProcessPoolExecutor(4) as ex:
        results = dict(zip(names, ex.map(measure_file, [paths[n] for n in names])))
    total = 0.0; per = {}
    for n in names:
        d = compare(results[n], soothe(n))
        e = sum(v * v for v in d.values()); per[n] = (e, d); total += e
    if verbose:
        for n in names:
            e, d = per[n]; worst = sorted(d.items(), key=lambda kv: -abs(kv[1]))[:5]
            print(f"{n} {e:8.1f}  " + "  ".join(f"{k}:{v:+.1f}" for k, v in worst))
    return total, per, results

# Real material (0.25.1): a dry track and soothe's renders of it, compared by
# the long-term change in each third octave and the change moment by moment.
# REAL lists (name, dry, soothe render, DOMINION settings); the files live in SOOTHE_DIR/song/in.
REAL = [("guitars_default", "guitars_dry.wav", "guitars_soothe_default.wav", ""),
        ("guitars_depth75", "guitars_dry.wav", "guitars_soothe_depth75.wav", "depth=7.5")]
CENTRES = 25 * 2 ** (np.arange(0, 29) / 3)

def _bandpowers(x, frame=4096, hop=2048):
    w = np.hanning(frame); f = np.fft.rfftfreq(frame, 1 / SR); m = x.mean(1)
    S = np.array([np.abs(np.fft.rfft(m[i:i + frame] * w)) ** 2 for i in range(0, len(m) - frame, hop)])
    out = np.zeros((len(S), len(CENTRES)))
    for j, c in enumerate(CENTRES):
        sel = (f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6)); out[:, j] = S[:, sel].sum(1) + 1e-20
    return out

_real = {}
def _real_reference(dry_name, wet_name):
    key = (dry_name, wet_name)
    if key not in _real:
        dry = M.load(f"{S}/song/in/{dry_name}", SR); wet, _ = M.align(dry, M.load(f"{S}/song/in/{wet_name}", SR), SR)
        _real[key] = (_bandpowers(dry), _bandpowers(wet))
    return _real[key]

REAL_BANDS = (CENTRES >= 100) & (CENTRES <= 6500)
def real_loss(tuning, workdir):
    # Squared differences: the long-term change per third octave (100 Hz to 6.4 kHz), x3, and the moment-by-moment average difference, x3.
    os.makedirs(workdir, exist_ok=True); total = 0.0; parts = {}
    tun = ",".join(f"{k}={v:.6g}" for k, v in tuning.items())
    jobs = f"{workdir}/real_jobs.txt"
    open(jobs, "w").write("\n".join(f"{workdir}/{n}.wav {settings}" for n, _, _, settings in REAL) + "\n")
    env = dict(os.environ, PARAGON_DOMFIT_IN=f"{S}/song/in/{REAL[0][1]}", PARAGON_DOMFIT_JOBS=jobs, PARAGON_DOMFIT_TUNING=tun)
    p = subprocess.run([BIN, "[domfit]"], env=env, capture_output=True, text=True)
    if p.returncode != 0: raise RuntimeError(p.stdout[-2000:])
    for n, dry_name, wet_name, _ in REAL:
        B0, Bs = _real_reference(dry_name, wet_name)
        dry = M.load(f"{S}/song/in/{dry_name}", SR); dom, _ = M.align(dry, M.load(f"{workdir}/{n}.wav", SR), SR)
        Bd = _bandpowers(dom); loud = B0.sum(1) > np.percentile(B0.sum(1), 20)
        cs = 10 * np.log10(Bs[loud].sum(0) / B0[loud].sum(0)); cd = 10 * np.log10(Bd[loud].sum(0) / B0[loud].sum(0))
        long_term = (cd - cs)[REAL_BANDS]
        ts = 10 * np.log10(Bs / B0); td = 10 * np.log10(Bd / B0); w = B0 / B0.sum(1, keepdims=True)
        valid = loud[:, None] & (B0 > B0.max() * 1e-7) & REAL_BANDS[None, :]
        moment = np.sum(np.abs(ts - td)[valid] * w[valid]) / np.sum(w[valid])
        e = 3 * np.sum(long_term ** 2) + 3 * moment ** 2
        parts[n] = (e, dict(zip([f"{c:.0f}" for c in CENTRES[REAL_BANDS]], long_term), moment=moment)); total += e
    return total, parts
