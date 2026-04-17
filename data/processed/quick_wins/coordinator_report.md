# Quick Wins Coordinator Report

Generated: 17 April 2026, 06:09 PM

---

## Agent Results

| Agent | Significant? | Integrated? | Findings |
|---|---|---|---|
| Rest & Travel Fatigue | No | No | `rest_fatigue_findings.md` |
| Weather Overlay | No | No | `weather_findings.md` |
| CLV Tracker | Yes | Always | `clv_tracker_findings.md` |

---

## What to do next

1. **Re-run the backtest** to see if integrated signals improve ROI:
   ```bash
   python src/strategy/venue_bias.py
   ```
2. **Start logging live bets** in `data/processed/quick_wins/bet_ledger.csv`
   to accumulate real CLV data over the coming weeks.
3. **Check weather before each weekend** using `weekend_picks.py`
   and manually note precipitation/wind for the qualifying match.
4. **Phase 2** (when 50+ live bets logged): referee assignment analysis.