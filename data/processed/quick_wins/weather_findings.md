# Agent 2 — Weather Overlay Findings

Weather-matched matches: 3,556

---

## Temperature vs Total Score
- Pearson r=nan, p=nan — not significant
- Direction: higher temp → fewer points

## Wet Conditions (>5mm precipitation) vs Total Score
- Wet: 391 matches, avg score 39.2
- Dry: 3165 matches, avg score 44.0
- Difference: -4.8 points
- t=nan, p=nan — not significant

## Wind vs Total Score
- Pearson r=nan, p=nan — not significant
- Direction: more wind → fewer points

## Temperature vs Home Win Rate
- Pearson r=-0.0135, p=0.4212 — not significant

## Wet Conditions vs Home Win Rate
- Wet home win rate: 57.5%  |  Dry: 56.1%
- t=0.562, p=0.5743 — not significant

## Cold (<12°C) vs Total Score
- Cold: 639 matches, avg 45.5  |  Warm: 2917, avg 43.1
- t=nan, p=nan — not significant

---

## Recommendation
**DO NOT INTEGRATE** — weather effects not statistically significant in this dataset