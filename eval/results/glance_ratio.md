# DriverGuard - off_road_ratio on drivers who are not distracted

Blocks 7-12 replayed on the stored traces (`tools/trace_studies.py glance`). `off_road_ratio` (M38) is the share of the last 30 s spent looking off the road, once 10 s of driving are in the window. It is only measured. None of these datasets labels distraction, so every clip counts as "not distracted": the table says how many clips a rule "ratio ≥ threshold" would have alerted on, i.e. its false-alarm side. Its detection side needs labelled glances (own recordings, DMD).

| Dataset | Clips with a filled window | Hours | Highest ratio: median / p90 / max | Clips ≥ 0.2 | Clips ≥ 0.3 | Clips ≥ 0.4 | Clips ≥ 0.5 | Clips ≥ 0.6 | Clips ≥ 0.7 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fl3d | 44 | 0.79 | 0.08 / 0.44 / 0.56 | 13 (30%) | 10 (23%) | 6 (14%) | 4 (9%) | 0 (0%) | 0 (0%) |
| yawdd | 315 | 2.06 | 0.00 / 0.21 / 0.89 | 34 (11%) | 18 (6%) | 10 (3%) | 6 (2%) | 4 (1%) | 4 (1%) |
| sust | 2074 | 5.76 | 0.00 / 0.00 / 0.00 | 0 (0%) | 0 (0%) | 0 (0%) | 0 (0%) | 0 (0%) | 0 (0%) |

SUST clips are 10 s, the minimum coverage: the window hardly ever fills there. FL3D drivers act drowsy: a dropped head is off the road too, so its ratios are not glances. YawDD is a parked car filmed from the mirror (people look around). None of them is normal driving with mirror checks, lane changes and junctions, which is where a glance rule would raise false alarms.
