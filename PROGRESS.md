# Project Progress

## Status: Analysis complete — Venue Bias confirmed, strategy in development

---

## Completed

### Session 1 — 2026-04-14
- [x] Created project structure (`src/`, `data/raw/`, `data/processed/`, `notebooks/`)
- [x] Confirmed primary data source: `data/raw/nrl.xlsx` (AusSportsBetting — results + odds 2013–present)
- [x] Researched supplementary data sources (see findings below)
- [x] Built four-agent research pipeline (`src/agents/team.py`)
- [x] Installed Python 3.11 + all dependencies (`/opt/homebrew/bin/python3.11`)

---

## Agent Team

| Agent | Status | Purpose |
|---|---|---|
| `data-sourcer` | Complete | uselessnrlstats + Betfair CSVs fetched |
| `requirements-manager` | Skipped | Not needed — data schema known |
| `data-engineer` | Complete | `nrl_clean.csv` built (5,435 rows, 1998–2025) |
| `data-scientist` | Complete | Findings written to `data/processed/findings.md` |

> Note: `claude-agent-sdk` could not connect (CLI subprocess issue). Pipeline was run directly by Claude Code instead. Same output.

---

## Analysis Results (Session 2)

| Bias | Result | p-value | Key Finding |
|---|---|---|---|
| Draw Bias | Not significant | p=0.84 | NRL draw rate only 1% — not exploitable |
| Form/Momentum Bias | **Significant** | p<0.0001 | r=0.20, but Betfair already prices in form (r=0.66) |
| **Venue/Home Bias** | **Significant** | p<0.0001 | AAMI Park: 76% home win rate, +12.9% Betfair edge |

**Primary target: Venue Bias — specifically AAMI Park (Melbourne Storm home ground)**

Top venues by home win rate:
- AAMI Park: 76.0% (Betfair edge: +12.9%)
- Olympic Park Stadium: 76.5% (predecessor to AAMI Park)
- Campbelltown Sports Stadium: 37.9% (home UNDERPERFORMS — fade home)
- Cbus Super Stadium: 44.3% (home underperforms)

---

## Blocker — Manual Download Required

`data/raw/nrl.xlsx` is an HTML placeholder, not a real Excel file.
**Action:** Download manually from https://www.aussportsbetting.com/data/historical-odds-results/nrl-rugby-league/
and save to `data/raw/nrl.xlsx`. This gives bookmaker odds 2013–present for full edge confirmation.

---

## Next Session — Pick up here

1. **Re-run pipeline** after downloading real nrl.xlsx:
   ```bash
   /opt/homebrew/bin/python3.11 src/ingestion/pipeline.py
   /opt/homebrew/bin/python3.11 src/analysis/bias_analysis.py
   ```
2. **Review strategy backtest results** in `data/processed/strategy_results.md`

---

## Data Sources Research Summary

| Source | Coverage | Odds? | Status |
|---|---|---|---|
| `data/raw/nrl.xlsx` | 2013–present | Yes (H2H + line + totals) | In repo |
| uselessnrlstats CSVs (GitHub) | 1998–present | No | data-sourcer will fetch |
| Betfair Automation Hub CSVs | 2021–present | Yes (exchange prices) | data-sourcer will attempt fetch |
| OddsPortal (via OddsHarvester) | 2009–present | Yes (multi-bookmaker) | Future — fills 2009–2012 gap |

---

## Backlog

- [x] Fetch supplementary data sources
- [x] Build data pipeline (`src/ingestion/pipeline.py`)
- [x] Run statistical analysis (`src/analysis/bias_analysis.py`)
- [x] Identify primary bias to exploit (Venue Bias — AAMI Park)
- [ ] **Download real nrl.xlsx** from AusSportsBetting (manual browser step)
- [ ] Re-run analysis with bookmaker odds once nrl.xlsx is real
- [ ] Review strategy backtest results (`data/processed/strategy_results.md`)
- [ ] Refine strategy with Kelly Criterion / staking plan
- [ ] Consider OddsPortal scraping to fill 2009–2012 odds gap
- [ ] Create Jupyter notebooks in `notebooks/` for EDA visualisations
- [ ] Add `strategy-developer` agent to the team pipeline
