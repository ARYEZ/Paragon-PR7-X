# Matching DOMINION to soothe 3 by measurement

DOMINION is our own design (soothe's workings aren't published). To bring it
closer, we measure what soothe 3 does to a test signal and fit DOMINION to
match: a black-box comparison of outputs, never anyone's code.

- `make_test_signal.py out.wav sections.json [rate]`: builds the 55.5 s test
  (48 kHz, or another rate such as `44100`) and its section map. It's seeded,
  so it always rebuilds bit-identically (at 48 kHz, sha256 starts
  `18814e77eef8c4c4`). Use the file at the rate the DAW runs at, so
  nothing is resampled. The sections are: flat pink noise; fixed
  resonances (narrow at 150 Hz, 1 kHz, 3.5 kHz and 8 kHz, wide at 400 Hz); a
  resonance gliding 60 Hz to 14 kHz; a switched 2.5 kHz resonance (attack and
  release); the fixed resonances at four levels; a drum loop; and stereo
  (a different resonance each side, then one in the sides only).
- `render-sheet.md`: what the owner renders through soothe 3 (R00 to R27, using
  soothe 3's own controls, one change from its defaults at a time).
- `measure.py dry.wav sections.json wet.wav [...]`: lines each render up with
  the dry file (cross-correlation; reports the delay), then measures each
  section and prints the renders side by side:
  - the cut at each resonance, and its width
  - the cut along the glide
  - attack and release (to 63% and 37%)
  - whether the cut depends on level
  - drum hits and the snare's ring
  - linking between left and right, and mid and side

  A render with nothing on reads 0.0 everywhere.

soothe's renders aren't kept in the repository (they're its output, and
large).

## Fitting DOMINION's REFINED engine (0.25.0)

`fit/` holds the scripts that fitted REFINED to the owner's 28 renders
(R00 to R27, soothe 3 1.0.6 at 44.1 kHz). They need the renders, which
stay out of the repository (they're soothe's output): set `SOOTHE_DIR` to
a folder with `soothe_test_44k.wav`, `sections_44k.json` and
`renders/R00.wav` ... `R27.wav`, and build the tests first.

- `fitlib.py`: each render's DOMINION settings (`CASES`: soothe's 0 to 10
  as 0 to 100 %, DEPTH as is), rendering through the hidden test
  `"[domfit]"` (in `tests/DominionTests.cpp`, any `dominion::Tuning` number
  by name), and the score: the measured numbers' differences, squared
  (dB, and times as 10 x log2).
- `fit.py STAGE [tries]`: Powell's method over one stage's numbers
  (`static`: depth, detail, widths, where it works; `timing`; `hard`),
  keeping the best in `fit/tuning.json`.
- `diag.py` and `sdiag.py`: side-by-side readings (timing, and cuts) for
  chosen renders.

The fitted numbers are the defaults in `dominion::Tuning` (Dominion.h).
R23 (DELTA) is checked on its own: soothe's delta is exactly input minus
output, as DOMINION's is.

## The fine-detail experiment (after 0.25.0, not released)

The owner's guitar track (dry, soothe at default and depth 7.5) showed
REFINED following soothe's timing (correlation 0.92) but cutting 2-5 kHz a
third to a half as much, and soothe's cut rippling with single harmonics
(0.47 dB of fine ripple against DOMINION's 0.06), so soothe analyses much
finer than 1/6-octave filters. `fine-detail-experiment.patch` (apply on
0.25.0) gives REFINED with LOOK-AHEAD an FFT listener inside its 2304-sample
delay (2048 points, a hop of 256, sqrt-Hann, per-bin prominence against a
neighbourhood, a cut spread across frequency and smoothed in time, its own
`fineTuning()`, a harmonic test). Fitted on the test renders and the
guitars together, it did not beat 0.25.0: test cuts 0.6-1.4 dB RMS against
0.2-1.1, guitars 215 against 191, and at low DETAIL it never fully let go
(single FFT bins of noise read as resonances). Tried on top: averaging
each bin with its neighbours (helps release), a 1024-point frame (no
gain), easing off where the spectrum is quiet (fixes guitars at 5-6 kHz,
hurts the test sections). Left out of the plugin; REFINED stays as 0.25.0.
A closer match on dense material would need more real material from the
owner (several sources, deterministic exports) to find what soothe does.
