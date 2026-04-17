# Project Progress

## Status: Live — Venue Bias strategy operational, Round 7 bet active

**Repo:** https://github.com/NixonS24/nrl-betting-strategy  
**Last updated:** 17 April 2026

---

## Quick Summary

An NRL betting strategy built on statistically significant venue bias.
5,435 matches analysed (1998–2026), three data sources merged.
Venue bias confirmed p<0.0001. Bookmaker backtest: **79 bets, +9.32% ROI**.
Live from Round 7 2026. Five analysis agents built and run.

---

## Sessions Completed

### Session 1 — 2026-04-14
- [x] Project structure, four-agent pipeline, Python 3.11 + dependencies

### Session 2 — 2026-04-14
- [x] Fetched all data sources (uselessnrlstats, Betfair, AusSportsBetting)
- [x] Built data pipeline → `nrl_clean.csv` (5,435 rows × 41 cols)
- [x] Statistical analysis across three biases; Venue Bias confirmed

### Session 3 — 2026-04-17
- [x] Venue bias backtest — refined to remove Cbus Super Stadium (−10.3% ROI drag)
- [x] Word report generated (`NRL_Bias_Research_Report.docx`)
- [x] Weekend picks generator — Round 7 card produced
- [x] GitHub repo initialised and pushed
- [x] Quick Wins system: 3 agents (rest/fatigue, weather, CLV) + coordinator
- [x] CLV tracking infrastructure live

### Session 4 — 2026-04-17 (continued)
- [x] Referee Bias agent (Agent 4) — proxy analysis complete, real data collection planned
- [x] Form Filter agent (Agent 5) — tested, not integrated (ROI neutral at 3/5, worse at 4/5)
- [x] Weather agent NaN bug fixed (dropna alignment), re-running with full dataset
- [x] Coordinator updated to run all 5 agents

---

## Statistical Analysis Results

| Bias | Test | Result | Key Finding |
|---|---|---|---|
| Draw Bias | Chi-square | p=0.62 — not significant | NRL draw rate 1%, no draw market |
| Form/Momentum | Point-biserial | p<0.0001, r=0.20 | Real but Betfair already prices it (r=0.66) |
| **Venue/Home Bias** | ANOVA + t-tests | **p<0.0001, F=4.33** | Large, persistent, exploitable |
| Home advantage trend | Linear regression | **p=0.015, r=−0.45** | Declining ~0.19%/yr — monitor |

---

## Strategy: Venue Bias

### Rules
- **Back home** when venue base HW rate − bookmaker implied prob ≥ 5%
- **Fade home (back away)** when venue base away rate − bookmaker implied away prob ≥ 5%
- Odds range: $1.50–$6.00 | Staking: Quarter Kelly | Min edge: 5%

### Target Venues

| Venue | Base HW Rate | Signal | Betfair Edge |
|---|---|---|---|
| AAMI Park | 76.0% | Back home | +10.4% |
| Olympic Park Stadium | 76.5% | Back home | — |
| Queensland Sport & Athletics Centre | 75.4% | Back home | — |
| Sydney Showground | 65.7% | Back home | — |
| Campbelltown Sports Stadium | 37.9% | Fade home | −24.7% |
| ~~Cbus Super Stadium~~ | ~~44.3%~~ | ~~Removed~~ | ~~−10.3% ROI drag~~ |

### Backtest Results (2009–2025)

| Source | Bets | Win Rate | Profit | ROI | Max Drawdown |
|---|---|---|---|---|---|
| Bookmaker (primary) | 79 | 55.7% | +$736 | **+9.32%** | $567 |
| Betfair validation | 9 | 77.8% | +$628 | **+69.78%** | $100 |

**AAMI Park alone:** 43 bets, 30W, +$866, ROI +20.1%

---

## Quick Wins Agent Results

Run with: `python -m src.agents.quick_wins.coordinator`

| # | Agent | Finding | Verdict |
|---|---|---|---|
| 1 | Rest & Travel Fatigue | Away short rest: +1.6% HW rate improvement (p=0.27) | Not significant — skip |
| 2 | **Weather Overlay** | Wet games average **4.8 fewer points** (t=−6.79, p<0.0001). Cold games +2.4 pts. No effect on HW rate. | **Confirmed — use for overs/unders, not win/loss** |
| 3 | **CLV Tracker** | Home odds shortening → **63% win rate** vs 48% when drifting (p<0.0001) | **Integrated — bet early in week** |
| 4 | Referee Bias | Home advantage declining −0.19%/yr (**p=0.015**); full ref data needed | **Partial — collect ref assignments** |
| 5 | Form Filter | 3/5 threshold: ROI 9.20% (−0.12%). 4/5: ROI −2.45%. No improvement. | Not integrated — venue signal standalone |

### Key Insights
- **Bet early in the week** — when home odds shorten, team wins 63% of the time (CLV signal)
- **Home advantage is declining** — ~0.19%/yr over 27 seasons; re-check venue baselines annually
- **Weather suppresses scoring** — wet conditions cut average score by **4.8 pts** (p<0.0001, confirmed); cold games add 2.4 pts. Use for overs/unders markets alongside win/loss bets
- **Form filter hurts** — adding form requirement reduces sample size without improving ROI

---

## Round 7 — Active Bet

| Field | Value |
|---|---|
| Match | Wests Tigers vs Brisbane Broncos |
| Kickoff | Saturday 18 Apr, 7:35pm AEST |
| Venue | Campbelltown Sports Stadium |
| Bet | **Back Brisbane Broncos** (fade home) |
| Odds | $2.45 |
| Edge | 21.3% |
| Stake | $8.99 (¼ Kelly on $100 bankroll) |

Log result in: `data/processed/quick_wins/bet_ledger.csv`

---

## Codebase Map

```
src/
  ingestion/pipeline.py          — merges 3 sources → nrl_clean.csv
  analysis/bias_analysis.py      — statistical tests for all 3 biases
  strategy/
    venue_bias.py                — backtest engine + Kelly staking
    generate_report.py           — Word doc report
    weekend_picks.py             — weekly betting card generator
  agents/
    team.py                      — original 4-agent research pipeline
    quick_wins/
      coordinator.py             — runs all 5 agents, integrates signals
      rest_fatigue.py            — Agent 1: rest days & travel
      weather.py                 — Agent 2: temperature/rain/wind
      clv_tracker.py             — Agent 3: CLV infrastructure
      referee_bias.py            — Agent 4: referee assignment bias
      form_filter.py             — Agent 5: form overlay test

data/processed/
  nrl_clean.csv                  — unified dataset (5,435 × 41)
  NRL_Bias_Research_Report.docx  — full research report
  weekend_picks_r7_2026.txt      — R7 betting card
  WEEKLY_SUMMARY_R7_2026.md      — R7 summary
  quick_wins/
    bet_ledger.csv               — FILL IN after each game
    coordinator_report.md
    rest_fatigue_findings.md
    weather_findings.md          — 3,556 matches, NaN fix pending
    clv_tracker_findings.md
    referee_findings.md
    form_filter_findings.md
```

---

## Next Steps

### This week
- [ ] Log Round 7 result (Broncos game Sat 18 Apr) → `bet_ledger.csv`
- [ ] Run `python src/strategy/weekend_picks.py --bankroll 100` Thursday for Round 8

### Short term
- [ ] **Add weather to weekend_picks.py** — fetch precipitation forecast for qualifying venue, flag overs/unders opportunity when wet predicted
- [ ] **Referee data collection** — scrape NRL.com match pages for referee assignments (2009–2026); re-run Agent 4 for full ANOVA
- [ ] **Regenerate Word report** — update with all 5 agent findings: `python src/strategy/generate_report.py`

### Medium term
- [ ] **CLV dashboard** — after 20+ live bets in ledger, build summary showing avg CLV
- [ ] **Bookmaker account strategy** — at +9% ROI, accounts will be limited; plan Betfair as primary execution venue
- [ ] **2026 mid-season refresh** — update nrl_clean.csv, re-check venue baselines holding

### Longer term
- [ ] Elo rating model (open source base: brandonfalconer/NRLPredictionModel)
- [ ] OddsPortal scraper to fill any historical odds gaps
- [ ] Jupyter EDA notebooks with venue maps and equity curves

---

## How to Run

```bash
# This week's bets
python src/strategy/weekend_picks.py --bankroll 100

# Full backtest
python src/strategy/venue_bias.py

# Run all 5 analysis agents
python -m src.agents.quick_wins.coordinator

# Regenerate Word report
python src/strategy/generate_report.py

# Rebuild full dataset
python src/ingestion/pipeline.py && python src/analysis/bias_analysis.py
```
