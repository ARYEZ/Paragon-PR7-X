# Matching ECHELON to FabFilter Pro-Q 4

Like `tools/soothe-match` for DOMINION: a black-box comparison of outputs,
never anyone's code. The owner renders our test signal through Pro-Q 4
(trial) at set band settings; we render ECHELON at the same settings and
measure both.

- `make_eq_signal.py out.wav sections.json [rate]`: the 36 s test file
  (44.1 kHz by default, 32-bit float, seeded so it rebuilds identically).
  A click on both sides (the whole response in one go), a click on each side
  alone (which side a band works on), a 20 Hz to 20 kHz sine sweep (the
  response again, and any distortion), pink noise, a 1 kHz tone over noise
  at four levels and switched on and off (for dynamic bands).
- `render-sheet-eq.md`: the owner's 31 renders (Q00 to Q30), for PR7-S.
- `measure_eq.py dry.wav sections.json wet.wav [...]`: each render's delay,
  response (from the click; the sweep as a check), sides, and dynamic
  behaviour. Checked against a textbook bell: exact to 0.01 dB.
- `compare_eq.py DIR [Q01 ...]`: renders ECHELON at each render's settings
  through the hidden test `"[eqfit]"` (tests/EqTests.cpp) and prints the
  differences (worst anywhere, worst under 5 kHz, phase, delay). The
  settings "as it comes" in the sheet are filled in from the owner's notes.

The renders stay out of the repository (they're Pro-Q's output).
