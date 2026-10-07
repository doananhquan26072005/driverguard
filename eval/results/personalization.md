# DriverGuard - does a per-driver baseline lower false alarms? (YawDD)

Blocks 7-12 replayed on the stored YawDD traces (`tools/trace_studies.py personal`). Driver enrollment (M9) never runs in the evaluations (the clips start at a simulated 60 km/h), so until now there was no number for it. Here its result is imitated: from the first 10 s (`eval.fake_enroll_s`) of a person's `Normal` clip, the medians of the good frames give the open-eye EAR, closed-mouth MAR and road pose, which are handed to blocks 7 and 8 the way a finished enrollment does. That clip is left out of every score below, in all three settings.

212 clips of 105 people scored (left out: 1, no Normal clip with a second of good frames). A person = gender + number + eyewear in the file name; whether the same number with and without glasses is one person was not checked.

- **Fixed common eye baseline**: the open-eye EAR stays at `eye.baseline_init` for everyone (never learnt).
- **Self-learnt**: the baseline is learnt during the clip (what every reported number used).
- **Fake-enrolled**: the person's own values from their Normal clip, as described above.

| Eyewear | Setting | Normal / talking clips | Hours | Alerts | of them drowsiness / off-road | Alerts / hour (95% CI) | False yawn events | False microsleep events | Yawning clips with a yawn event |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| all | fixed common eye baseline | 99 | 0.84 | 7 | 0 / 7 | 8.4 (3.37–17.3) | 0 | 3 | 93/113 (82.3%) |
| all | self-learnt (as evaluated so far) | 99 | 0.84 | 7 | 0 / 7 | 8.4 (3.37–17.3) | 0 | 3 | 93/113 (82.3%) |
| all | fake-enrolled from the person's Normal clip | 99 | 0.84 | 9 | 0 / 9 | 10.8 (4.93–20.5) | 1 | 3 | 97/113 (85.8%) |
| no glasses | fixed common eye baseline | 56 | 0.48 | 3 | 0 / 3 | 6.3 (1.29–18.3) | 0 | 3 | 51/64 (79.7%) |
| no glasses | self-learnt (as evaluated so far) | 56 | 0.48 | 3 | 0 / 3 | 6.3 (1.29–18.3) | 0 | 3 | 51/64 (79.7%) |
| no glasses | fake-enrolled from the person's Normal clip | 56 | 0.48 | 3 | 0 / 3 | 6.3 (1.29–18.3) | 0 | 3 | 51/64 (79.7%) |
| glasses | fixed common eye baseline | 33 | 0.28 | 3 | 0 / 3 | 10.8 (2.23–31.6) | 0 | 0 | 31/36 (86.1%) |
| glasses | self-learnt (as evaluated so far) | 33 | 0.28 | 3 | 0 / 3 | 10.8 (2.23–31.6) | 0 | 0 | 31/36 (86.1%) |
| glasses | fake-enrolled from the person's Normal clip | 33 | 0.28 | 5 | 0 / 5 | 18.0 (5.84–42.0) | 0 | 0 | 34/36 (94.4%) |
| sunglasses | fixed common eye baseline | 10 | 0.08 | 1 | 0 / 1 | 12.7 (0.32–70.6) | 0 | 0 | 11/13 (84.6%) |
| sunglasses | self-learnt (as evaluated so far) | 10 | 0.08 | 1 | 0 / 1 | 12.7 (0.32–70.6) | 0 | 0 | 11/13 (84.6%) |
| sunglasses | fake-enrolled from the person's Normal clip | 10 | 0.08 | 1 | 0 / 1 | 12.7 (0.32–70.6) | 1 | 0 | 12/13 (92.3%) |

Clips whose alerts differ between self-learnt and fake-enrolled: 8: 24-FemaleNoGlasses-Talking (1 → 1); 32-FemaleSunGlasses-Talking (1 → 1); 38-FemaleNoGlasses-Talking (1 → 1); 7-FemaleGlasses-Talking (1 → 1); 19-MaleGlassesmoustache-Talking (0 → 1); 28-MaleGlasses-Talking (1 → 1); 31-MaleGlasses-Talking (0 → 1); 33-MaleGlasses-Talking (1 → 1).

## Reading it

- YawDD is a parked car with clips of ~20 s: the false alarms here are almost all `off_road` at the start of a clip and yawn / microsleep events; PERCLOS and `drowsy_score` hardly ever get going. It can show whether the enrolled road pose and mouth baseline help; it cannot show the effect on drowsiness scoring.
- The enrolled values come from another clip of the same person, not from the start of the scored clip: between two YawDD clips the person may sit differently, which a real enrollment at the start of the same trip would not suffer from. Extra `off_road` alerts with the enrolled road pose can come from that.
- The CIs of the three settings overlap unless the counts differ a lot: with this little time a small difference is not a result.
- FL3D and SUST file names carry no person, so they cannot be used. The main number has to come from UTA-RLDD (same person awake and drowsy, 10 min each).
- Do not write "personalised" as a measured benefit in a report unless this table shows one.
