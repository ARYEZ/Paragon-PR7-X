# Rendering the soothe test file: step by step

Thank you for doing this! It takes about 15 minutes. You'll export the same
test file 16 times through soothe 3, each time with **one** setting changed.

## Setting up (once)

1. In your DAW, make a new project at the rate you work at, and use the test file
   made at that rate (`soothe_test_44k.wav` for 44.1 kHz, `soothe_test_48k.wav` for 48 kHz),
   so nothing is resampled.
2. Put the test file on a stereo audio track, starting at the very
   beginning (bar 1, time 0).
3. Put **soothe 3** on that track, the only plugin on it. Nothing on the
   master bus either (no limiter, no EQ).
4. Leave soothe's quality or latency setting as it comes, and write down what
   it says.

## Exporting (each render)

- Export the whole file from the start to the end (about 56 seconds): the
  tail at the end matters.
- Format: **WAV, the project's rate, 24-bit or 32-bit float, stereo**.
- **No normalising, no dither,** nothing on the master.
- An offline or faster-than-real-time bounce is fine.
- Name each file as below (`R01.wav` and so on).

Before each render, **reset soothe to its defaults** (a fresh instance, or its
default preset), then change only the setting listed. For each one, write down
the number soothe shows for that control. The exact values matter as much as
the files.

## The renders

| File | soothe 3 settings | Write down |
|---|---|---|
| R00 | soothe **bypassed** (or off) | — |
| R01 | **defaults**, nothing changed | every control's value |
| R02 | DEPTH about **a quarter** of the way up | DEPTH value |
| R03 | DEPTH about **three quarters** of the way up | DEPTH value |
| R04 | DEPTH at **maximum** | DEPTH value |
| R05 | SHARPNESS at **minimum** | value |
| R06 | SHARPNESS at **maximum** | value |
| R07 | SELECTIVITY at **minimum** | value |
| R08 | SELECTIVITY at **maximum** | value |
| R09 | ATTACK at its **fastest** | value |
| R10 | ATTACK at its **slowest** | value |
| R11 | RELEASE at its **fastest** | value |
| R12 | RELEASE at its **slowest** | value |
| R13 | mode switched to **HARD** (soft is usually the default) | — |
| R14 | **HARD** and DEPTH at **maximum** | DEPTH value |
| R15 | soothe's **stereo setting** changed to its other choice (for example mid/side to left/right, or link off) | what you chose |

If soothe 3 has no control by one of these names, or calls it something else,
skip that render (or use the closest one) and tell me which.

## Extra renders, if you have time (well worth it during the trial)

The more points we measure, the closer the match, and the trial won't last
forever. Same steps: reset to defaults, then change only what's listed.

| File | soothe 3 settings | Write down |
|---|---|---|
| R16 | DEPTH about **10%** of the way up | value |
| R17 | DEPTH **halfway** | value |
| R18 | SHARPNESS about **a quarter** of the way up | value |
| R19 | SHARPNESS about **three quarters** of the way up | value |
| R20 | SELECTIVITY about **a quarter** of the way up | value |
| R21 | SELECTIVITY about **three quarters** of the way up | value |
| R22 | ATTACK about **halfway** between its default and fastest | value |
| R23 | RELEASE about **halfway** between its default and slowest | value |
| R24 | **HARD**, DEPTH about **a quarter** of the way up | value |
| R25 | **HARD**, DEPTH about **three quarters** of the way up | value |
| R26 | **DELTA** on (you hear only what soothe removes) | — |
| R27 | defaults, **MIX at 50%** | — |

**Two more things that help a lot:**

- **Screenshots** of soothe 3 at its defaults, showing every control, page and
  menu (including the quality or latency setting). They tell me the controls'
  names and ranges, so DOMINION's knobs can line up with soothe's.
- **Your own music:** one vocal and one full mix you know well, exported twice
  each, once dry and once through soothe at its defaults (e.g. `vocal_dry`,
  `vocal_soothe`, `mix_dry`, `mix_soothe`). These are for listening and
  measuring on real material, not only test tones.

One check: if the trial ever puts silence or noise into its output (some
trials do), tell me which renders it happened in.

## Sending them back

There are 16 files of about 16 MB each.

- **Easiest:** put them in a zip, along with your notes, and attach it here.
- **If the zip is too big to attach,** convert to **FLAC** (lossless, about
  half the size) and attach that.
- **Or:** connect the folder on your computer to this session, and I'll read
  the files directly. I can set that up when you're ready.
