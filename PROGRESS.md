# Project Progress

## Status: Live — BlueBet Stadium added to strategy; H_001–H_010 in pipeline (Session 7)

**Repo:** https://github.com/NixonS24/nrl-betting-strategy  
**Last updated:** 17 April 2026 (Session 5)

---

## Quick Summary

An NRL betting strategy built on statistically significant venue bias.
5,435 matches analysed (1998–2026), three data sources merged.
Venue bias confirmed p<0.0001. Bookmaker backtest: **79 bets, +9.32% ROI**.
Live from Round 7 2026. Five analysis agents built and run.

---

## Sessions Completed

### Session 7 — 2026-04-24 (Strategy update + H_010 delivered)

- [x] Reviewed all H_001–H_009 results (all run and verified by Gemini during session gap)
- [x] **Strategy update:** Added BlueBet Stadium to `BACK_HOME_VENUES` in `venue_bias.py` (H_001 confirmed, p=0.0001, 82.3% HW 2019+); AAMI Park annotated as Storm team-linked (H_004)
- [x] **H_003 referee data:** `data/raw/referee_assignments.csv` scraped (264 rows, 2024+). Existing R_003 flagged as in-sample; holdout re-run possible with new data
- [x] **H_010 queued by OpenAI:** Near-flip calibration follow-up (tighter design than rejected H_009 near-flip bucket, p=0.060). Script delivered: `research/scripts/H_010_analysis.py`
- [x] H_010 key design concern flagged: H_009 showed a direction **reversal** between training (homes over-priced in near-flip) and holdout (homes under-priced). Script explicitly tests for this structural shift
- [x] Updated `RESPONSE_FROM_CLAUDE.md` with H_003/H_004/H_009 analysis notes for Gemini and OpenAI
- [ ] H_010 pending Gemini run (`python3 research/scripts/H_010_analysis.py`)

### Session 6 — 2026-04-24 (Tri-Model Pipeline: Architect Turn)

- [x] Tri-model research pipeline formalised: OpenAI (Ideator) → Claude (Architect) → Gemini (Verifier)
- [x] Agreed to `PROPOSAL_FOR_CLAUDE.md`; `RESPONSE_FROM_CLAUDE.md` updated with feedback and schema additions (`method`, `data_window`, `backtest_type` fields)
- [x] Wrote and verified H_001, H_002, H_003, H_004, H_006, H_007, H_008, H_009
- [x] **H_001 result:** BlueBet Stadium edge CONFIRMED (p=0.0001) — promoted to BACK HOME strategy venue
- [x] **H_002 result:** Suncorp fade NOT significant (p=0.071). Marked EXPLORATORY
- [x] **H_003 result:** Referee & DOW analysis shows large effect sizes (Sunday -9%) but p > 0.05 on small n=258. Marked EXPLORATORY
- [x] **H_004 result:** AAMI Park confirmed as 100% Melbourne Storm home venue. Re-classified as team-linked venue edge
- [x] **H_006 result:** BK/BF Disagreement filter shows +28% ROI delta but n=6 in holdout. Marked EXPLORATORY
- [x] **H_007 result:** Bookmaker Line Movement rejected. ROI Delta -4.6% in holdout
- [x] **H_008 result:** Overround intensity rejected. No significant calibration difference
- [x] **H_009 result:** Asymmetric calibration rejected. No significant odds-based bias found


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

### Session 5 — 2026-04-17 (Injury Mispricing — Agent 6 complete)
- [x] Scraped SuperCoach prices 2021–2026 (548 players/year) → `sc_player_values.csv`
- [x] Discovered NRL.com match pages embed full team lists as HTML-escaped JSON
- [x] Built `_extract_teams_from_html()` parser — 100% success rate on completed matches
- [x] Scraped 64 real team list matches across 2024–2025 → `team_lists_raw.csv`
- [x] Tested lineup value delta (SC prices) as predictor: **NOT significant** (r=−0.044, p=0.73)
- [x] Key insight: market already prices lineup quality; the signal is *change* in odds
- [x] Built `score_upcoming_round()` for real-time Thursday squad scoring
- [x] Confirmed proxy signals remain best: line movement p<0.0001 (unchanged)

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
| 6 | **Injury Mispricing** | Raw lineup delta (SC prices) **not significant** (p=0.73, 64 matches) — market prices lineup quality. Line movement IS significant (p<0.0001): drift >5% → 40.3% HW; shorten >5% → 60.8% HW. Real-time lineup scorer built (NRL.com parser). | **Confirmed — use line movement as injury proxy; lineup scorer for confirmation** |

### Key Insights
- **Bet early in the week** — when home odds shorten, team wins 63% of the time (CLV signal)
- **Home advantage is declining** — ~0.19%/yr over 27 seasons; re-check venue baselines annually
- **Injury/team news is priced directionally correctly** — home odds drifting >10% → home wins only 36.3% vs 60.5% normal (p<0.0001). Market direction right but magnitude may be off
- **Calibration error at 50/50** — when Betfair prices home at 45–55%, they win 62.5% (+11.9% error). Back home teams priced as genuine coin-flips at strategy venues
- **Lineup quality (SC prices) not independently predictive** — 64 matches, r=-0.044 (p=0.73). Market already prices lineup strength. The signal is *change* in odds, not absolute lineup value
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
      coordinator.py             — runs all 6 agents, integrates signals
      rest_fatigue.py            — Agent 1: rest days & travel
      weather.py                 — Agent 2: temperature/rain/wind
      clv_tracker.py             — Agent 3: CLV infrastructure
      referee_bias.py            — Agent 4: referee assignment bias
      form_filter.py             — Agent 5: form overlay test
      injury_bias.py             — Agent 6: real NRL.com lineup scraper + SC prices

data/processed/
  nrl_clean.csv                  — unified dataset (5,435 × 41)
  NRL_Bias_Research_Report.docx  — full research report
  weekend_picks_r7_2026.txt      — R7 betting card
  weekend_picks_r8_2026.txt      — R8 no qualifying bet
  WEEKLY_SUMMARY_R7_2026.md      — R7 summary
  quick_wins/
    bet_ledger.csv               — R7 result logged (Broncos +$4.05)
    coordinator_report.md
    rest_fatigue_findings.md
    weather_findings.md          — 588 matches, wet −5.6 pts (p=0.0001)
    clv_tracker_findings.md
    referee_findings.md
    form_filter_findings.md
    injury_findings.md           — lineup delta not predictive (p=0.73, n=64)
    sc_player_values.csv         — 548 NRL players, 2026 SC prices
    team_lists_raw.csv           — 64 real match team lists (2024-2025)
```

---

## Research Pipeline (Tri-Model)

| ID | Hypothesis | Result | Status |
|---|---|---|---|
| H_001 | Updated venue baselines (2019+) | BlueBet CONFIRMED (p=0.0001); global recalibration REJECTED | Done ✓ |
| H_002 | Suncorp Stadium fade home | p=0.071, n=24 holdout | EXPLORATORY |
| H_003 | Referee/day-of-week bias | p=0.184 DoW, p=0.713 ref — in-sample only | EXPLORATORY (flag) |
| H_004 | AAMI Park venue vs Storm | 100% Storm — team-linked edge reclassified | Done ✓ |
| H_006 | BK/BF disagreement filter | +28% ROI delta, n=6 holdout | EXPLORATORY |
| H_007 | BK line movement signal | ROI delta -4.6% | REJECTED |
| H_008 | Overround/margin intensity | No calibration difference | REJECTED |
| H_009 | Full odds-curve calibration | Near-flip p=0.060 borderline | REJECTED |
| H_010 | Near-flip prospective design | Script delivered — pending Gemini run | In Progress |

## Next Steps

### This week
- [x] Log Round 7 result (Broncos won 21-20, +$4.05) → `bet_ledger.csv`
- [x] Run `python src/strategy/weekend_picks.py --bankroll 113.04` for Round 8 (no qualifying bet)
- [ ] Run `python src/strategy/weekend_picks.py --bankroll 113.04 --round 9` Thursday for Round 9

### Short term
- [x] **Weather added to weekend_picks.py** — live rain forecast now auto-fetched for all venues; wet flag triggers overs/unders note
- [x] **Real NRL team list scraper built** — NRL.com HTML parser extracts 1-17+bench from any completed match; `score_upcoming_round()` for Thursday lineup scoring
- [x] **SuperCoach player values scraped** — 548 players with 2026 SC prices as salary cap proxy
- [x] **Lineup delta tested** — NOT predictive (p=0.73, n=64 matches); confirms line movement is the right signal
- [x] **Calibration edge test** — 45–55% Betfair home bucket wins 62.5% (vs 50.5% implied). **REJECTED** (p=0.18, n=32). Signal is small-sample noise. (2026-04-24)
- [x] **H_001: Venue Baseline Recalibration** — Modern (2019+) baselines underperform all-time on 2022+ holdout (ROI delta -12%). **REJECTED Global**, but **BlueBet Stadium confirmed** as BACK HOME venue (p=0.0001). (2026-04-24)
- [x] **H_002: Suncorp Stadium Fade** — Fade home ROI +75% in holdout, but p=0.071 (one-sided). **NEEDS DATA** — keep as exploratory signal. (2026-04-24)
- [x] **H_004: AAMI Park Decomposition** — Venue is 100% Melbourne Storm home games. **RE-CLASSIFIED** as Team-Linked Venue Edge. (2026-04-24)
- [x] **H_006: BK/BF Disagreement Filter** — Markets-Agree filter shows +28% ROI delta, but n=6 in holdout. **EXPLORATORY**. (2026-04-24)
- [x] **H_007: Bookmaker Line Movement** — Rejected. ROI Delta -4.6% in holdout. No significant predictive power. (2026-04-24)
- [x] **H_008: Overround Intensity** — Rejected. No significant calibration difference between overround buckets. (2026-04-24)
- [x] **H_009: Asymmetric Calibration** — Rejected. No significant odds-based bias found across the curve. (2026-04-24)
- [ ] **Referee data collection** — scrape NRL.com match pages for referee assignments (2009–2026); re-run Agent 4 for full ANOVA
- [ ] **Regenerate Word report** — update with all 6 agent findings: `python src/strategy/generate_report.py`

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
