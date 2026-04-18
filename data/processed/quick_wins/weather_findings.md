# Agent 2 — Weather Overlay Findings

Weather-matched matches: 588

---

## Temperature vs Total Score
- Pearson r=0.0359, p=0.3854 — not significant
- Direction: higher temp → more points

## Wet Conditions (>5mm precipitation) vs Total Score
- Wet: 91 matches, avg score 38.0
- Dry: 497 matches, avg score 43.6
- Difference: -5.6 points
- t=-3.992, p=0.0001 — **SIGNIFICANT**

## Wind vs Total Score
- Pearson r=-0.0319, p=0.4398 — not significant
- Direction: more wind → fewer points

## Temperature vs Home Win Rate
- Pearson r=-0.0339, p=0.4114 — not significant

## Wet Conditions vs Home Win Rate
- Wet home win rate: 50.5%  |  Dry: 52.3%
- t=-0.309, p=0.7572 — not significant

## Cold (<12°C) vs Total Score
- Cold: 90 matches, avg 41.9  |  Warm: 498, avg 42.9
- t=-0.676, p=0.4994 — not significant

---

## Recommendation
**INTEGRATE** — weather is a significant predictor; add as confidence modifier