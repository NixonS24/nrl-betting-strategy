# Agent 2 — Weather Overlay Findings

Weather-matched matches: 1,040

---

## Temperature vs Total Score
- Pearson r=nan, p=nan — not significant
- Direction: higher temp → fewer points

## Wet Conditions (>5mm precipitation) vs Total Score
- Wet: 123 matches, avg score 37.0
- Dry: 917 matches, avg score 43.9
- Difference: -6.9 points
- t=nan, p=nan — not significant

## Wind vs Total Score
- Pearson r=nan, p=nan — not significant
- Direction: more wind → fewer points

## Temperature vs Home Win Rate
- Pearson r=0.0008, p=0.9786 — not significant

## Wet Conditions vs Home Win Rate
- Wet home win rate: 63.4%  |  Dry: 58.9%
- t=0.960, p=0.3375 — not significant

## Cold (<12°C) vs Total Score
- Cold: 373 matches, avg 44.9  |  Warm: 667, avg 42.1
- t=nan, p=nan — not significant

---

## Recommendation
**DO NOT INTEGRATE** — weather effects not statistically significant in this dataset