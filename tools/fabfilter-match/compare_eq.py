# Renders ECHELON at each Pro-Q 4 render's settings (the hidden "[eqfit]" test)
# and compares the two responses:
#   python3 compare_eq.py DIR [Q01 Q02 ...]
# DIR holds eq_test_44k.wav, sections_44k.json and renders/Q00.wav ...; the
# settings "as it comes" in the sheet are filled in below from the owner's notes.
import json, os, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import measure_eq as M

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(HERE, "../../build/tests/ParagonX1Tests")

# Each render: ECHELON's settings for the same band (see render-sheet-eq.md).
CASES = {
    "Q00": "",
    "Q01": "shape=bell freq=1000 gain=6 q=1", "Q02": "shape=bell freq=1000 gain=12 q=1", "Q03": "shape=bell freq=1000 gain=-12 q=1",
    "Q04": "shape=bell freq=1000 gain=6 q=0.3", "Q05": "shape=bell freq=1000 gain=6 q=4", "Q06": "shape=bell freq=1000 gain=12 q=15",
    "Q07": "shape=bell freq=10000 gain=6 q=1", "Q08": "shape=bell freq=18000 gain=6 q=1", "Q09": "shape=bell freq=40 gain=6 q=1",
    "Q10": "shape=lowshelf freq=200 gain=6 q=0.71", "Q11": "shape=lowshelf freq=200 gain=6 q=2",
    "Q12": "shape=highshelf freq=5000 gain=6 q=0.71", "Q13": "shape=highshelf freq=5000 gain=-6 q=2",
    "Q14": "shape=lowcut freq=100 slope=12 q=0.71", "Q15": "shape=lowcut freq=100 slope=24 q=0.71", "Q16": "shape=lowcut freq=100 slope=48 q=0.71",
    "Q17": "shape=lowcut freq=100 slope=96 q=0.71", "Q18": "shape=lowcut freq=100 slope=6 q=0.71", "Q19": "shape=lowcut freq=100 slope=12 q=3",
    "Q20": "shape=highcut freq=8000 slope=24 q=0.71", "Q21": "shape=notch freq=1000 q=1", "Q22": "shape=bandpass freq=1000 q=1",
    "Q23": "shape=tiltshelf freq=1000 gain=6 q=0.71", "Q24": "shape=flattilt freq=1000 gain=6",
    "Q25": "shape=bell freq=1000 gain=6 q=1 place=left", "Q26": "shape=bell freq=1000 gain=6 q=1 place=mid",
    "Q27": "shape=bell freq=1000 gain=6 q=1 place=side",
    "Q28": "shape=bell freq=1000 gain=0 q=1 dyn=-12 thresh=-30 auto=0", "Q29": "shape=bell freq=1000 gain=0 q=1 dyn=-12 auto=1",
    "Q30": "shape=bell freq=1000 gain=0 q=1 dyn=12 thresh=-30 auto=0",
}

def render_echelon(directory, names):
    out = os.path.join(directory, "echelon"); os.makedirs(out, exist_ok=True)
    jobs = os.path.join(out, "jobs.txt")
    open(jobs, "w").write("\n".join(f"{out}/{n}.wav {CASES[n]}" for n in names) + "\n")
    env = dict(os.environ, PARAGON_EQFIT_IN=os.path.join(directory, "eq_test_44k.wav"), PARAGON_EQFIT_JOBS=jobs)
    p = subprocess.run([BIN, "[eqfit]"], env=env, capture_output=True, text=True)
    if p.returncode != 0: raise RuntimeError(p.stdout[-2000:])
    return {n: os.path.join(out, f"{n}.wav") for n in names}

if __name__ == "__main__":
    directory = sys.argv[1]
    info = json.load(open(os.path.join(directory, "sections_44k.json"))); sr = info["sampleRate"]
    sec = {s["name"]: s for s in info["sections"]}
    names = sys.argv[2:] or [n for n in CASES if os.path.exists(os.path.join(directory, "renders", f"{n}.wav"))]
    dry = M.load(os.path.join(directory, "eq_test_44k.wav"), sr)
    ours = render_echelon(directory, names)
    print("%-5s %-44s %8s %8s %8s %8s   %s" % ("", "", "worst", "<5k", "phase", "delay", "Pro-Q / ECHELON at 100, 1k, 10k Hz"))
    for n in names:
        a = M.measure(dry, M.load(os.path.join(directory, "renders", f"{n}.wav"), sr), sec, sr)
        b = M.measure(dry, M.load(ours[n], sr), sec, sr)
        ca, cb = np.array(a["impulse_db"]["L"]), np.array(b["impulse_db"]["L"])
        diff = cb - ca; low = M.GRID < 5000
        pa, pb = np.array(a["impulse_phase"]), np.array(b["impulse_phase"])
        audible = (M.GRID > 50) & (M.GRID < 15000)
        phase = np.degrees(np.max(np.abs((pb - pa)[audible] - np.median((pb - pa)[audible]))))
        worst = M.GRID[np.argmax(np.abs(diff))]
        print("%-5s %-44s %+7.2f %+7.2f %7.0f° %8d   %s   (worst at %.0f Hz)" % (
            n, CASES[n][:44], diff[np.argmax(np.abs(diff))], np.max(np.abs(diff[low])), phase, a["lag_samples"] - b["lag_samples"],
            "  ".join("%+.2f/%+.2f" % (M.at(ca, f), M.at(cb, f)) for f in (100, 1000, 10000)), worst))
        if a["gated"]["held_db"] or b["gated"]["held_db"]:
            print("      dynamic: by level -40..-10 Pro-Q %s ECHELON %s; timing attack %.0f/%.0f ms release %.0f/%.0f ms" % (
                [round(a["levels"][k], 1) for k in (40, 30, 20, 10)], [round(b["levels"][k], 1) for k in (40, 30, 20, 10)],
                a["gated"]["attack_ms"], b["gated"]["attack_ms"], a["gated"]["release_ms"], b["gated"]["release_ms"]))
