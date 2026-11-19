# Rendering the soothe test file: step by step

Thank you for doing this! It takes about 15 minutes. You'll export the same
test file 16 times through soothe 3, each time with **one** setting changed.

## Setting up (once)

1. In your DAW, make a new project at **48 kHz**.
2. Put `soothe_test_48k.wav` on a stereo audio track, starting at the very
   beginning (bar 1, time 0).
3. Put **soothe 3** on that track, the only plugin on it. Nothing on the
   master bus either (no limiter, no EQ).
4. Leave soothe's quality or latency setting as it comes, and write down what
   it says.

## Exporting (each render)

- Export the whole file from the start to the end (about 56 seconds): the
  tail at the end matters.
- Format: **WAV, 48 kHz, 24-bit or 32-bit float, stereo**.
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

## Sending them back

There are 16 files of about 16 MB each.

- **Easiest:** put them in a zip, along with your notes, and attach it here.
- **If the zip is too big to attach,** convert to **FLAC** (lossless, about
  half the size) and attach that.
- **Or:** connect the folder on your computer to this session, and I'll read
  the files directly. I can set that up when you're ready.
