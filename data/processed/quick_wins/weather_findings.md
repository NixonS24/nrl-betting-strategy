# Agent 2 — Weather Overlay Findings

Dataset: 3,550 weather-matched matches (after NaN alignment fix)

---

## Temperature vs Total Score
- Pearson r=−0.0998, p<0.0001 — **SIGNIFICANT**
- Direction: higher temperature → fewer points (cold games score more — teams run harder, fewer stoppages)

## Wet Conditions (>5mm precipitation) vs Total Score
- Wet: 391 matches, avg score **39.2**
- Dry: 3,159 matches, avg score **44.0**
- Difference: **−4.8 points** in wet conditions
- t=−6.786, p<0.0001 — **SIGNIFICANT**

## Wind vs Total Score
- Pearson r=−0.0071, p=0.6721 — not significant

## Cold (<12°C) vs Total Score
- Cold: 639 matches, avg score **45.5**
- Warm: 2,911 matches, avg score **43.1**
- Difference: +2.4 points in cold conditions
- t=4.092, p<0.0001 — **SIGNIFICANT**

## Temperature vs Home Win Rate
- Pearson r=−0.0113, p=0.5022 — not significant
- Weather does not affect *who* wins, only *how much* is scored

## Wet Conditions vs Home Win Rate
- Wet home win rate: 58.3%  |  Dry: 56.1%
- p=0.4062 — not significant

---

## Summary

Weather significantly affects total scoring but NOT the winner.
Useful as an **overs/unders overlay**, not a win/loss predictor.

| Condition | Avg Total Score | vs Baseline | Significance |
|---|---|---|---|
| Wet (>5mm rain) | 39.2 | −4.8 pts | p<0.0001 |
| Cold (<12°C) | 45.5 | +2.4 pts | p<0.0001 |
| High temp | lower | r=−0.10 | p<0.0001 |
| Wind | no effect | — | p=0.67 |

---

## Recommendation
**INTEGRATE for overs/unders markets** — wet conditions reliably suppress scoring
by ~5 points. When a qualifying venue game is played in rain, consider backing
*unders* on the total points line as a complementary bet to the win/loss pick.

Do NOT use weather to adjust win/loss predictions — no significant effect on HW rate.
