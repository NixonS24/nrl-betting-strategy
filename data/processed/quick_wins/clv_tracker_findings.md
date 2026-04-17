# Agent 3 — Closing Line Value (CLV) Tracker Findings

## What is CLV?
CLV = closing odds − odds obtained when bet was placed.
Consistently positive CLV means you're finding value before the market corrects.
A bettor with +CLV is profitable long-term regardless of short-term win/loss swings.

---

## Retrospective Analysis (Opening vs Closing Odds, 2009–2026)
- Matches with both open & close odds: 2,428
- Avg home line movement (close/open): 1.0261
  (< 1.0 = home shortened / market more confident in home win)
- % of matches where home odds shortened: 53.7%
- % of matches where home odds drifted:   44.5%

### Win Rate: Home Odds Shortened vs Drifted
- Home win rate when odds shortened: **63.0%**
- Home win rate when odds drifted:   47.8%
- t=7.544, p=0.0000 — **SIGNIFICANT**
- Interpretation: Shortened odds correctly signal home win probability — betting opening has CLV

### Strategy Venue CLV Proxy
- Bets at back-home venues (open odds): 134
- Avg CLV proxy (close − open):  -0.0071
- % with positive CLV proxy:     34.3%
- CLV proxy = closing odds minus opening odds for back-home strategy bets

---

## Live Bet Ledger
Template created at: data/processed/quick_wins/bet_ledger.csv

**How to use:**
1. When `weekend_picks.py` generates a bet, add a row to bet_ledger.csv
2. Fill `odds_obtained` at time of bet placement
3. After the game, fill `closing_odds`, `result`, `won`, `profit`
4. Run `clv_tracker.py` to compute CLV and track long-run edge

**Columns:**
  - `bet_id`
  - `bet_date`
  - `match_date`
  - `round`
  - `home_team`
  - `away_team`
  - `venue`
  - `bet_type`
  - `team_backed`
  - `odds_obtained`
  - `closing_odds`
  - `bf_closing_odds`
  - `result`
  - `won`
  - `stake`
  - `profit`
  - `clv`
  - `clv_pct`
  - `strategy`
  - `notes`

---

## Recommendation
**INTEGRATE** — set up CLV tracking for all live bets going forward.
Target: avg CLV > +0.02 (2 cents per dollar) over 50+ bets confirms genuine edge.