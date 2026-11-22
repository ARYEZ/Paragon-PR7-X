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
