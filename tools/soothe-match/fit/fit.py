# Fit stages: python3 fit.py STAGE [iterations]; keeps the best in tuning.json.
import json, os, sys, time
import numpy as np
from scipy.optimize import minimize
import fitlib as F

HERE = os.path.dirname(os.path.abspath(__file__))
TUNING = f"{HERE}/tuning.json"
tuning = json.load(open(TUNING)) if os.path.exists(TUNING) else {}

TIMING = ["att", "rel", "held"]
STATIC = lambda k: k not in ("att", "rel")
STAGES = {
  "timing": dict(params={"attack0": (1, 200), "attack25": (2, 300), "attack50": (5, 400), "hardAttack": (0.3, 5), "hardRelease": (0.2, 5), "attack100": (20, 1500), "release0": (2, 200),
                         "release50": (5, 600), "release100": (30, 4000), "leadMs": (0, 50),
                         "detailAttack0": (0.1, 2), "detailAttack100": (0.5, 6), "detailRelease0": (0.2, 5), "detailRelease100": (0.1, 3)},
                 cases=["R01", "R02", "R08", "R10", "R11", "R19", "R20", "R26", "R06", "R07", "R17", "R18", "R12"],
                 keep=lambda k: k in TIMING),
  "static": dict(params={"overPower": (0.2, 1.5), "depthScale": (0.02, 3), "depthPower": (0.5, 3), "depthStart": (0, 4.5), "marginDepth": (-1, 4),
                         "detailScale0": (0.05, 3), "detailScale100": (0.3, 40), "margin0": (-6, 12), "margin100": (-6, 15),
                         "knee": (0.5, 20), "width0": (0.2, 3), "width50": (0.05, 1.5), "width100": (0.02, 0.6),
                         **{f"weight{i}": (0, 3) for i in range(3, 10)}},
                 cases=["R01", "R27", "R03", "R04", "R05", "R06", "R07", "R17", "R18", "R16"],
                 keep=STATIC),
  "hard": dict(params={"hard5": (-80, 0), "hardStep": (0, 15), "hardCurve": (0, 3), "hardSlope": (0.05, 2), "hardFlat": (0, 1), "hardTilt": (-3, 8), "hardKnee": (1, 60)},
               cases=["R12", "R13", "R21", "R22"], keep=STATIC),
  "joint": dict(params={"depthScale": (0.05, 3), "overPower": (0.2, 1.5), "marginDepth": (-1, 4), "margin0": (-6, 12), "margin100": (-6, 15),
                         "window0": (0.3, 3), "window100": (0.15, 2), "cycles": (4, 60), "knee": (0.5, 20),
                         "width50": (0.05, 1.5), **{f"weight{i}": (0, 3) for i in range(3, 10)}},
                 cases=["R01", "R27", "R03", "R04", "R05", "R06", "R07", "R17", "R18"], keep=STATIC, real=True),
  "all": dict(params=None, cases=[c for c in F.CASES if c != "R23"], keep=lambda k: True),
}

def run(stage, iters):
    st = STAGES[stage]; names = list(st["params"]); lo = np.array([st["params"][n][0] for n in names]); hi = np.array([st["params"][n][1] for n in names])
    defaults = dict(depthStart=2.2, depthPower=1.3, depthScale=1.0, margin0=3, margin100=1, knee=4, width0=1.2, width50=0.4, width100=0.1,
                    window0=1.0, window100=0.33, attack0=2, attack50=10, attack100=30, release0=10, release50=40, release100=300,
                    detailAttack0=0.5, detailAttack100=2, detailRelease0=1.6, detailRelease100=0.6, hard5=-38, hardStep=3, hardSlope=0.3, hardTilt=1.5,
                    leadMs=15, cycles=16, marginDepth=0, overPower=1, hardCurve=0, hardFlat=0, hardKnee=4, hardAttack=1, hardRelease=1, detailScale0=1, detailScale100=1, attack25=5, **{f"weight{i}": w for i, w in enumerate([0, 0, 0, .05, .15, .3, .6, 1, .8, .5])})
    x0 = np.array([tuning.get(n, defaults[n]) for n in names])
    # Work in 0..1 (log for positive ranges) so every number moves alike.
    logs = (lo > 0)
    to01 = lambda x: np.where(logs, (np.log(x) - np.log(np.where(logs, lo, 1))) / (np.log(np.where(logs, hi, 2)) - np.log(np.where(logs, lo, 1))), (x - lo) / (hi - lo))
    from01 = lambda u: np.where(logs, np.exp(np.log(np.where(logs, lo, 1)) + np.clip(u, 0, 1) * (np.log(np.where(logs, hi, 2)) - np.log(np.where(logs, lo, 1)))), lo + np.clip(u, 0, 1) * (hi - lo))
    best = [None, None]; count = [0]
    def f(u):
        x = from01(u); t = dict(tuning); t.update(dict(zip(names, x)))
        total = 0.0
        _, per, _ = F.loss(st["cases"], t, f"{F.S}/w_{stage}")
        for n, (e, d) in per.items():
            total += sum(v * v for k, v in d.items() if st["keep"](k))
        if st.get("real"):
            total += F.real_loss(t, f"{F.S}/w_{stage}_real")[0]
        count[0] += 1
        if best[0] is None or total < best[0]:
            best[0], best[1] = total, t
            json.dump(t, open(TUNING, "w"), indent=1)
            print(f"[{count[0]}] {total:.1f}  " + " ".join(f"{n}={v:.3g}" for n, v in zip(names, x)), flush=True)
        # Out of range costs (clipped above).
        return total + 1000 * float(np.sum(np.clip(-u, 0, None) + np.clip(u - 1, 0, None)))
    u0 = np.clip(to01(x0), 0.001, 0.999)
    minimize(f, u0, method="Powell", options=dict(maxfev=iters, xtol=0.01, ftol=0.002))
    print("best", best[0])

if __name__ == "__main__":
    run(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 200)
