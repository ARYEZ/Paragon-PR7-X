# Rendering the EQ test file through Pro-Q 4: step by step

Thank you! About 30 short exports of one 36-second file. Each render is
**one band** in Pro-Q 4 with exact settings, so I can measure its shape
precisely and line ECHELON's knobs up with Pro-Q's.

**Don't start the trial until you're ready to do the whole sheet** (it
takes about 30 to 45 minutes).

## Setting up (once), in PR7-S

1. Interface at **44.1 kHz**. New, empty project; nothing on the master,
   master fader at 0 dB.
2. Press **Home**, then **File > Import Audio Files (a Track Each)...** and
   pick `eq_test_44k.wav` (it lands at the project start). Track fader at
   0 dB, pan centred.
3. Put **Pro-Q 4** in that track's first insert slot. Nothing else on it.
4. In Pro-Q 4, check once and leave alone:
   - output gain **0 dB**, **Auto Gain off**, gain scale **100%**;
   - the processing mode at its default (**Zero Latency**);
   - anything else (character, quality, analyzer) as it comes.
   **Take a screenshot** of the whole window at this point.

## Each render

1. Start from **no bands** (delete the previous band: select it and press
   Delete, or right-click it > Delete).
2. Make the band listed: double-click the display to add a band, choose
   its **shape** (and **slope** where listed) in the band's panel, then set
   **FREQ, GAIN and Q** to the numbers given. You can usually click a value
   in the band panel and type it. If you can't, get as close as you can
   and **write down what Pro-Q shows**.
3. **File > Export Audio Mixdown...**: WHAT "The whole song, to the end of
   its last part"; CHANNELS "The main mix"; SAMPLE RATE 44.1 kHz; BITS
   **32-bit float**; click OFF; **mono OFF**.
4. Name the file after its number: `Q00.wav`, `Q01.wav` ...

If Pro-Q 4 doesn't offer a setting listed, skip that render and tell me.

## The renders

| File | Band | Shape | Freq | Gain | Q / slope |
|---|---|---|---|---|---|
| Q00 | **no band at all** | | | | |
| Q01 | Bell | Bell | 1000 Hz | +6 dB | Q 1 |
| Q02 | Bell | Bell | 1000 Hz | +12 dB | Q 1 |
| Q03 | Bell | Bell | 1000 Hz | -12 dB | Q 1 |
| Q04 | Bell, wide | Bell | 1000 Hz | +6 dB | Q 0.3 |
| Q05 | Bell, narrow | Bell | 1000 Hz | +6 dB | Q 4 |
| Q06 | Bell, very narrow | Bell | 1000 Hz | +12 dB | Q 15 |
| Q07 | Bell, high | Bell | 10000 Hz | +6 dB | Q 1 |
| Q08 | Bell, very high | Bell | 18000 Hz | +6 dB | Q 1 |
| Q09 | Bell, low | Bell | 40 Hz | +6 dB | Q 1 |
| Q10 | Low shelf | Low Shelf | 200 Hz | +6 dB | Q as it comes (write it down) |
| Q11 | Low shelf, resonant | Low Shelf | 200 Hz | +6 dB | Q 2 |
| Q12 | High shelf | High Shelf | 5000 Hz | +6 dB | Q as it comes |
| Q13 | High shelf cut, resonant | High Shelf | 5000 Hz | -6 dB | Q 2 |
| Q14 | Low cut 12 | Low Cut | 100 Hz | | slope 12 dB/oct, Q as it comes |
| Q15 | Low cut 24 | Low Cut | 100 Hz | | slope 24 dB/oct |
| Q16 | Low cut 48 | Low Cut | 100 Hz | | slope 48 dB/oct |
| Q17 | Low cut 96 | Low Cut | 100 Hz | | slope 96 dB/oct |
| Q18 | Low cut 6 | Low Cut | 100 Hz | | slope 6 dB/oct |
| Q19 | Low cut, resonant | Low Cut | 100 Hz | | slope 12 dB/oct, Q 3 |
| Q20 | High cut 24 | High Cut | 8000 Hz | | slope 24 dB/oct |
| Q21 | Notch | Notch | 1000 Hz | | Q as it comes |
| Q22 | Band pass | Band Pass | 1000 Hz | | Q as it comes |
| Q23 | Tilt shelf | Tilt Shelf | 1000 Hz | +6 dB | as it comes |
| Q24 | Flat tilt | Flat Tilt | (as it comes) | +6 dB | as it comes |
| Q25 | Bell on the **left** only | Bell | 1000 Hz | +6 dB | Q 1, stereo placement **Left** |
| Q26 | Bell on the **mid** only | Bell | 1000 Hz | +6 dB | Q 1, stereo placement **Mid** |
| Q27 | Bell on the **side** only | Bell | 1000 Hz | +6 dB | Q 1, stereo placement **Side** |

**Dynamic bands** (turn the band dynamic and set its range: in Pro-Q you
drag the ring around the GAIN knob, or set the dynamic range in the band
panel; leave attack and release as they come and write them down):

| File | Band | Freq | Gain | Q | Dynamic range | Threshold |
|---|---|---|---|---|---|---|
| Q28 | dynamic cut | 1000 Hz | 0 dB | Q 1 | **-12 dB** | **-30 dB** |
| Q29 | dynamic cut, auto threshold | 1000 Hz | 0 dB | Q 1 | **-12 dB** | **Auto** (if Pro-Q 4 has it) |
| Q30 | dynamic boost | 1000 Hz | 0 dB | Q 1 | **+12 dB** | **-30 dB** |

**Screenshots, please:** the window at setup (step 4), one band panel each
for Q10, Q14 and Q28 (to see the default Q, slope and dynamic settings),
and the processing-mode menu opened.

## Sending them back

Upload them here, five at a time as before (about 12 MB each).
