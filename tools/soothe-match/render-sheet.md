# Rendering the soothe test file: step by step

Thank you for doing this! It takes about 20 minutes. You'll export the same
test file through soothe 3 many times, each time with **one** thing changed
from soothe's defaults. The controls named here are soothe 3's own (as on
its screen: soft / hard, depth, detail, attack, release, mix, quality,
low latency).

## Setting up (once)

1. Make a new project at the rate you work at, and use the test file made
   at that rate (`soothe_test_44k.wav` for 44.1 kHz, `soothe_test_48k.wav`
   for 48 kHz), so nothing is resampled.
2. Put the test file on a **stereo** audio track, starting at the very
   beginning (time 0). Fader at 0 dB, pan centred.
3. Put **soothe 3** on that track, the only plugin on it. Nothing on the
   master either (no limiter, no EQ), master fader at 0 dB.
4. In soothe's **cogwheel (settings) menu**, make sure **"Always render on
   ultra" is OFF**. If it's on, every export quietly uses a different
   quality from the one on the screen, and the renders won't match what you
   hear while it plays.

## Exporting (each render)

- Export the whole file from the start to the end (about 56 seconds): the
  tail at the end matters.
- Format: **WAV, the project's rate, 32-bit float (or 24-bit), stereo**.
- **No normalising, no dither, not mono,** nothing on the master.
- Name each file as below (`R01.wav` and so on).

Before each render, **reset soothe to its defaults**: the "Factory default"
preset (soft, depth 5.0, detail 5.0, attack 5.0, release 3.0, mix 100 %,
out 0.0 dB, quality normal, low latency off). Then change only what's
listed. Where a number is given, set it as close as you can and **write
down the exact number soothe shows**.

## The renders

| File | Change from the defaults | Write down |
|---|---|---|
| R00 | soothe **bypassed** (soothe's own bypass button) | — |
| R01 | nothing: **the defaults** | — |
| R02 | **low latency** on | — |
| R03 | depth **2.5** | depth |
| R04 | depth **7.5** | depth |
| R05 | depth **all the way up** | depth |
| R06 | detail **all the way down** | detail |
| R07 | detail **all the way up** | detail |
| R08 | attack **all the way down** (fastest) | attack |
| R09 | attack **all the way up** (slowest) | attack |
| R10 | release **all the way down** (fastest) | release |
| R11 | release **all the way up** (slowest) | release |
| R12 | **hard** (instead of soft) | — |
| R13 | **hard**, depth **all the way up** | depth |
| R14 | side panel, stereo: mode **left/right** (instead of mid/side) | the link % |
| R15 | side panel, stereo: link **0 %** (mode left as it is) | the mode |

R02 is the most important one after R01. DOMINION has no look-ahead (it
reacts with zero delay, like soothe's low latency mode), so R02 is the
nearest like-for-like comparison, and R01 against R02 shows what soothe's
look-ahead adds.

## Extra renders, if you have time (well worth it during the trial)

The more points we measure, the closer the match, and the trial won't last
forever. Same steps: reset to the defaults, then change only what's listed.

| File | Change from the defaults | Write down |
|---|---|---|
| R16 | depth **1.0** | depth |
| R17 | detail **2.5** | detail |
| R18 | detail **7.5** | detail |
| R19 | attack **2.5** | attack |
| R20 | release **6.0** | release |
| R21 | **hard**, depth **2.5** | depth |
| R22 | **hard**, depth **7.5** | depth |
| R23 | **delta** on (you hear only what soothe removes) | — |
| R24 | mix **50 %** | — |
| R25 | **low latency** on, depth **all the way up** | depth |
| R26 | **low latency** on, attack **all the way down** | attack |
| R27 | the depth curve made flat: **bypass all three of its bands** (double-click each node: the red one, the blue one at 4k, the green one, so each shows hollow) | — |

R27 tells me what the default curve's three bands do, so DOMINION's
default curve can match it.

**Also helpful:**

- **Screenshots** of soothe's side panel opened (the stereo, tilt and scale
  sections, at their defaults), and with each of the three default bands
  clicked so its band controls show (shape, frequency, gain or depth, Q).
  That gives me the default curve's exact numbers.
- **Your own music:** one vocal and one full mix you know well, exported twice
  each, once dry and once through soothe at its defaults (e.g. `vocal_dry`,
  `vocal_soothe`, `mix_dry`, `mix_soothe`). These are for listening and
  measuring on real material, not only test tones.

One check: if the trial ever puts silence or noise into its output (some
trials do), tell me which renders it happened in.

## Sending them back

Each file is about 10 to 20 MB.

- **Easiest:** put them in a zip, along with your notes, and attach it here.
- **If the zip is too big to attach,** convert to **FLAC** (lossless, about
  half the size) and attach that.
- **Or:** connect the folder on your computer to this session, and I'll read
  the files directly. I can set that up when you're ready.
