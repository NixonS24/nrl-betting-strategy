# Agent 5 — Form Filter Overlay Findings

Tests whether requiring strong home team form (≥3/5 recent wins) on top of
venue bias improves ROI vs raw venue bias alone.

---

## Comparison: Baseline vs Form-Filtered (Bookmaker Odds, 2009–2025)

| Metric | Baseline | Form-Filtered | Change |
|---|---|---|---|
| Bets | 79 | 60 | -19 |
| Win rate | 55.7% | 58.3% | +2.6% |
| Total profit | $736 | $552 | $-184 |
| ROI | 9.32% | 9.20% | -0.12% |
| Max drawdown | $567 | $438 | $-129 |

## Form-Filtered: By Venue
                              n  wins  profit       roi
venue                                                  
AAMI Park                    39    27   768.0  0.196923
Campbelltown Sports Stadium  20     7  -267.0 -0.133500
Olympic Park Stadium          1     1    51.0  0.510000

## Bets Dropped by Form Filter
- Dropped: 0 bets
- Their combined P&L: $+0
- Their win rate: 0.0%
- Verdict: Costly drop — those bets were winning

## Betfair Validation (Form-Filtered)
- 7 bets, 85.7% win rate, ROI 91.29%

---

## Recommendation
**DO NOT INTEGRATE** — form filter does not improve ROI (9.32% → 9.20%).
Consider raising FORM_THRESHOLD_BACK to 0.8 (4/5 wins) for a tighter filter.