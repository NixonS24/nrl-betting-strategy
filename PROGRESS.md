# Project Progress

## Status: Live — Venue Bias strategy operational, Round 7 bet active

**Repo:** https://github.com/NixonS24/nrl-betting-strategy  
**Last updated:** 17 April 2026

---

## Summary

An NRL betting strategy built on statistically significant venue bias.  
Three data sources merged (5,435 matches, 1998–2026). Venue bias confirmed  
at p<0.0001. Bookmaker backtest: 79 bets, +9.32% ROI. Live from Round 7 2026.

---

## Sessions Completed

### Session 1 — 2026-04-14
- [x] Created project structure (`src/`, `data/raw/`, `data/processed/`, `notebooks/`)
- [x] Built four-agent research pipeline (`src/agents/team.py`)
- [x] Installed Python 3.11 + all dependencies

### Session 2 — 2026-04-14 (continued)
- [x] Fetched uselessnrlstats CSVs (1998–2025, match history)
- [x] Fetched Betfair exchange CSVs (2021–2026, exchange odds)
- [x] Integrated manually downloaded AusSportsBetting xlsx (2009–2026, bookmaker odds)
- [x] Built data pipeline → `data/processed/nrl_clean.csv` (5,435 rows × 41 cols)
- [x] Ran statistical analysis across three biases
- [x] Identified Venue Bias as primary exploitable signal

### Session 3 — 2026-04-17
- [x] Built venue bias backtest (`src/strategy/venue_bias.py`)
- [x] Refined strategy — removed Cbus Super Stadium (−10.3% ROI drag)
- [x] Generated professional Word report (`data/processed/NRL_Bias_Research_Report.docx`)
- [x] Built weekend picks generator (`src/strategy/weekend_picks.py`)
- [x] Generated Round 7 2026 betting card
- [x] Initialised GitHub repo — https://github.com/NixonS24/nrl-betting-strategy
- [x] Researched strategy extensions (referee bias, weather, CLV, ML models)
- [x] Built Quick Wins agent system (3 agents + coordinator)
- [x] Ran all quick win agents — CLV infrastructure confirmed significant

---

## Statistical Analysis Results

| Bias | Test | Result | Key Finding |
|---|---|---|---|
| Draw Bias | Chi-square | p=0.62 — not significant | NRL draw rate only 1%, no draw market on Betfair |
| Form/Momentum | Point-biserial | p<0.0001, r=0.20 | Real effect but Betfair already prices it (r=0.66) |
| **Venue/Home Bias** | ANOVA + t-tests | **p<0.0001, F=4.33** | Large, persistent, exploitable at specific venues |

---

## Strategy: Venue Bias

### Rules
- **Back home** when venue has historically elevated home win rate AND bookmaker odds imply probability < (base rate − 5%)
- **Fade home (back away)** when venue home team historically underperforms AND market overprices home
- Odds range: $1.50 – $6.00 | Staking: Quarter Kelly | Min edge: 5%

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

**By venue (bookmaker backtest):**
- AAMI Park: 43 bets, 30W, +$866, ROI **+20.1%**
- Campbelltown Sports Stadium: 34 bets, 13W, −$81, ROI −2.4%
- Olympic Park Stadium: 2 bets, 1W, −$49

---

## Quick Wins Agent Results — 2026-04-17

Run with: `python -m src.agents.quick_wins.coordinator`

| Agent | Finding | Integrated? |
|---|---|---|
| Rest & Travel Fatigue | Away short rest improves home win rate by only 1.6% (p=0.27) — not significant | No |
| Weather Overlay | Wet conditions suppress scoring by 6.9 pts (37 vs 44 avg) — partial data, p=nan | No (retry needed) |
| **CLV Tracker** | **Home odds shortening predicts 63% win rate vs 48% when drifting (p<0.0001)** | Yes — ledger live |

### CLV Key Insight
When home team odds shorten from open to close, that team wins **63%** of the time.
Placing bets **early in the week** (before market adjusts) maximises CLV.

---

## Round 7 — Active Bet (2026-04-17)

| Field | Value |
|---|---|
| Match | Wests Tigers vs Brisbane Broncos |
| Kickoff | Saturday 18 Apr, 7:35pm AEST |
| Venue | Campbelltown Sports Stadium |
| Bet | **Back Brisbane Broncos** (fade home) |
| Odds | $2.45 |
| Edge | 21.3% (venue base away rate 62.1% vs market-implied 40.8%) |
| Stake | $8.99 (¼ Kelly on $100 bankroll) |
| Expected profit | +$4.69 |

Log result in: `data/processed/quick_wins/bet_ledger.csv`

---

## Codebase

```
src/
  ingestion/
    pipeline.py              — merges all 3 data sources → nrl_clean.csv
  analysis/
    bias_analysis.py         — statistical tests for all 3 biases
  strategy/
    venue_bias.py            — backtest engine + Kelly staking
    generate_report.py       — Word doc report generator
    weekend_picks.py         — weekly betting card (run each round)
  agents/
    team.py                  — original 4-agent research pipeline
    quick_wins/
      coordinator.py         — runs all 3 quick win agents
      rest_fatigue.py        — Agent 1: rest days & travel
      weather.py             — Agent 2: temperature/rain/wind
      clv_tracker.py         — Agent 3: CLV infrastructure

data/
  raw/
    nrlmanualdownlaod.xlsx   — AusSportsBetting bookmaker odds (2009–2026)
    uselessnrlstats/         — Match history CSVs (1998–2025)
    betfair/                 — Exchange odds CSVs (2021–2026)
  processed/
    nrl_clean.csv            — Unified dataset (5,435 rows × 41 cols)
    NRL_Bias_Research_Report.docx
    weekend_picks_r7_2026.txt
    quick_wins/
      bet_ledger.csv         — Live bet tracking (fill each week)
      coordinator_report.md
      rest_fatigue_findings.md
      weather_findings.md
      clv_tracker_findings.md
```

---

## Next Steps

### Immediate (this week)
- [ ] Log Round 7 result into `bet_ledger.csv` after Saturday's game
- [ ] Run `weekend_picks.py --bankroll 100` each Thursday for Round 8

### Short term (next 2–3 sessions)
- [ ] **Fix weather agent** — add rate limiting (sleep between API calls) and retry → re-run with full dataset to confirm/deny the 6.9 pt suppression effect
- [ ] **Referee bias agent** — strongest unimplemented signal (peer-reviewed evidence); scrape NRL referee assignments, correlate with home penalty rates and outcomes
- [ ] **Form filter overlay** — only back home at AAMI Park when Melbourne Storm also have ≥3 wins in last 5 (add confidence layer, test if improves ROI)

### Medium term
- [ ] **CLV dashboard** — after 20+ live bets in ledger, build CLV summary report showing if strategy is capturing genuine value
- [ ] **OddsPortal scraper** — fills 2009–2012 bookmaker odds gap (currently using 2009 from ASB manual download only)
- [ ] **Jupyter EDA notebooks** — visual exploration of venue maps, seasonal trends, equity curves

### Longer term
- [ ] **Elo rating model** — combine with venue bias as composite signal; test if consensus between Elo + venue picks improves win rate
- [ ] **Bookmaker account management** — if ROI holds at +9%+, accounts will be limited; plan for Betfair exchange as primary execution venue
- [ ] **2026 season monitoring** — refresh nrl_clean.csv mid-season, re-run baselines to check venue rates holding

---

## Running the Project

```bash
# Generate this week's bets
python src/strategy/weekend_picks.py --bankroll 100

# Re-run full backtest
python src/strategy/venue_bias.py

# Run quick wins agents
python -m src.agents.quick_wins.coordinator

# Regenerate Word report
python src/strategy/generate_report.py

# Rebuild full dataset (after updating raw data)
python src/ingestion/pipeline.py
python src/analysis/bias_analysis.py
```
