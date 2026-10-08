# DriverGuard - UTA-RLDD, false alarms against drowsy subjects caught

From config/thresholds.yaml; block 5 decided again from the traced inputs.

## Headline: the held-out subjects at the current thresholds

At `risk.drowsy.l1` = 40 on 24 held-out subjects (4.08 h of awake video): **0.98 false alarms per hour** (Poisson 0.27–2.51; resampled by person 0.00–3.02), and **15 / 24** drowsy (`10`) videos get a drowsiness alert, **12 / 24** reach L3. The point estimate is at or under 1.0 / h; the upper bound is not: the PRD target is not shown, only not contradicted.

## Trade-off on the dev subjects

24 dev subjects, 3.87 h of awake video. One row per `risk.drowsy.l1`, everything else as in `config/thresholds.yaml`. False alarms are drowsiness-branch alerts on `0` videos after the start-up stretch; sensitivity counts `10` videos (one per subject) with at least one drowsiness alert. Unit: subject (one `0` and one `10` video each), positive share = `10` videos among the scored `10` + `0` videos.

| l1 | False alarms | Per hour (95% CI) | Upper bound, wider of Poisson / by person | `10` with an alert | `10` at L2+ | `10` at L3 | ≤ 1.0 / h |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 30 | 7 | 1.8 (0.73–3.7) | 3.78 | 17 / 24 | 13 / 24 | 12 / 24 | no |
| 35 | 5 | 1.3 (0.42–3.0) | 3.02 | 15 / 24 | 12 / 24 | 12 / 24 | no |
| 40 (current) | 5 | 1.3 (0.42–3.0) | 3.02 | 14 / 24 | 12 / 24 | 12 / 24 | no |
| 45 | 5 | 1.3 (0.42–3.0) | 3.02 | 14 / 24 | 12 / 24 | 12 / 24 | no |
| 50 | 2 | 0.5 (0.06–1.9) | 1.87 | 12 / 24 | 12 / 24 | 12 / 24 | yes |
| 55 | 2 | 0.5 (0.06–1.9) | 1.87 | 12 / 24 | 12 / 24 | 12 / 24 | yes |
| 60 | 2 | 0.5 (0.06–1.9) | 1.87 | 12 / 24 | 12 / 24 | 12 / 24 | yes |

Among the dev rows at 1.0 / h or under (point estimate), the most `10` videos with an alert: risk.drowsy.l1=50 (12 / 24). Reading only: no threshold is changed here; if the curve suggests another `l1` that is a separate decision (M53 left 40 → 50 open).
