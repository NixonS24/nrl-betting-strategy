# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Research project investigating statistically significant biases in Australian NRL (National Rugby League) gambling markets. Three target biases:
- **Draw Bias:** Market underrepresents draw probability between high-profile/top-tier clubs
- **Form/Momentum Bias:** Market over/underreacts to recent team performance
- **Venue/Home Bias:** Market miscalculates home advantage at specific venues

Goal: Develop a profitable strategy exploiting these inefficiencies.

## Setup

```bash
pip install -r requirements.txt
```

## Running Code

```bash
# Verify data loads correctly
python3 test_read_data.py

# Run the full agent research team (end-to-end pipeline)
python3 -m src.agents.team

# Skip data sourcing (use existing raw data only)
python3 -m src.agents.team --skip-sourcing

# Fetch supplementary datasets only (no analysis)
python3 -m src.agents.team --source-only

# Run with a custom task
python3 -m src.agents.team --task "Focus only on Venue Bias for ANZ Stadium"

# Launch Jupyter for notebooks
jupyter lab
```

No build, test, or lint tooling is configured yet.

## Architecture

### Research Architect Role (Multi-Model Pipeline)

When a hypothesis file appears in `research/hypotheses/H_XXX.md`, your role is to:
1. **Write the Analysis Script:** Create `research/scripts/H_XXX_analysis.py`. Use `python3` for execution.
2. **Data Source:** Use `data/processed/nrl_clean.csv`. Strictly filter for valid rows (handle NaNs and date-aware splits).
3. **Standardized Output:** The script MUST save a JSON file to `research/results/R_XXX.json` with this structure:
   ```json
   {
     "hypothesis_id": "H_XXX",
     "p_value": 0.045,
     "sample_size": 450,
     "roi_impact": 0.052,
     "is_significant": true,
     "method": "e.g. T-test, ANOVA",
     "data_window": "e.g. 2019-2026",
     "summary": "Brief explanation"
   }
   ```
4. **Visuals:** Save a diagnostic chart to `research/visuals/H_XXX_plot.png` (required only for trends/distributions).

### Agent Team (`src/agents/team.py`)

The primary way to run research is via a four-agent pipeline orchestrated by Claude:

| Agent | Role | Writes |
|---|---|---|
| `data-sourcer` | Fetches uselessnrlstats CSVs + Betfair exchange CSVs into `data/raw/` | `data/raw/uselessnrlstats/`, `data/raw/betfair/`, `data/raw/sourcing_report.md` |
| `requirements-manager` | Reads raw data schema, defines analysis spec | `data/processed/requirements_spec.md` |
| `data-engineer` | Merges all raw sources, cleans and derives features | `data/processed/nrl_clean.csv`, `src/ingestion/pipeline.py` |
| `data-scientist` | Runs statistical tests for all three biases | `data/processed/findings.md`, `src/analysis/bias_analysis.py` |

The orchestrator coordinates them in sequence. Each agent writes files so subsequent agents can pick up where the last left off.

**Data sources:**
- `data/raw/nrl.xlsx` — AusSportsBetting: results + odds 2013–present (primary)
- `data/raw/uselessnrlstats/` — match history 1998–present, no odds (fetched by data-sourcer)
- `data/raw/betfair/` — Betfair exchange odds 2021–present (fetched by data-sourcer)

### Data Pipeline (manual stages)

1. **Ingestion** (`src/ingestion/`) — load and clean `data/raw/nrl.xlsx`
2. **Analysis** (`src/analysis/`) — statistical analysis of the three biases
3. **Strategy** (`src/strategy/`) — develop and backtest betting strategies
4. **Exploration** (`notebooks/`) — Jupyter notebooks for EDA

**Primary data source:** `data/raw/nrl.xlsx` (historical NRL match data). All processing outputs go to `data/processed/`.

## Multi-Model Research Pipeline (Tri-Model)

This project runs a three-model collaborative research loop:

| Role | Model | Responsibility |
|---|---|---|
| **Ideator** | OpenAI/Codex | Writes `research/hypotheses/H_XXX.md` based on `PROGRESS.md` and `findings.md` |
| **Architect** | Claude (you) | Writes `research/scripts/H_XXX_analysis.py` for each hypothesis file that appears |
| **Verifier** | Gemini | Runs scripts, red-teams results, manages git branching |

### Architect Rules (Claude's role)
- **Track 1 always first:** User scripts in `src/strategy/` and `src/agents/quick_wins/` take priority over the hypothesis queue.
- **After user work:** Check `research/hypotheses/` for unprocessed H_XXX files (lowest number first, skip if matching R_XXX.json exists).
- **All scripts must:**
  - Use `data/processed/nrl_clean.csv` with NaN filtering
  - Use a **holdout design** (train pre-2022, test 2022+; or pre-2023/test 2023+ for Betfair-era hypotheses)
  - Save JSON to `research/results/R_XXX.json` including `method`, `data_window`, `backtest_type` fields
  - Include `"backtest_type": "holdout"` or `"in_sample"` so Gemini can enforce the in-sample gate
  - Save chart to `research/visuals/H_XXX_plot.png` for trend/distribution hypotheses
- **After delivering scripts:** Update `RESPONSE_FROM_CLAUDE.md` with design decisions and anything Gemini should verify.
- **Do not run scripts yourself** — Gemini runs and verifies them.

### Known Data Constraints
- Betfair odds (`bf_*`) only available 2021+; dual-odds analyses have limited training windows
- `both_top8` column has team-name canonicalisation drift — avoid until Gemini confirms fix
- `coordinator.py` references `injury_bias` without importing it — known bug, do not rely on coordinator
- `venue_bias.py` computes baselines on full data (in-sample) — research scripts use holdout instead

### New data available (as of 2026-04-24)
- `data/raw/referee_assignments.csv` — 264 rows, 2024+ seasons, columns: season, round, match_slug, home_nickname, away_nickname, match_id, referee. Can be used for a proper holdout re-run of H_003.

### Confirmed Findings (as of 2026-04-24)

| Finding | Status | Notes |
|---|---|---|
| Venue bias at AAMI Park | CONFIRMED | ~78.9% HW (2019+); reclassify as Melbourne Storm team-linked edge pending H_004 |
| BlueBet Stadium BACK HOME | CONFIRMED | p=0.0001, +27pp shift post-2019; add to strategy |
| Campbelltown Sports Stadium FADE | CONFIRMED | ~30.8% HW (2019+) |
| Suncorp Stadium FADE | EXPLORATORY | p=0.071, n=24 holdout — do not trade yet |
| Blanket baseline recalibration (H_001) | REJECTED | Modern baselines underperform all-time on holdout |
| 45–55% Betfair calibration edge | REJECTED | p=0.18, n=32 — small-sample noise |
| BK line movement (H_007) | REJECTED | ROI delta -4.6% on holdout |
| Overround intensity (H_008) | REJECTED | No calibration difference across margin buckets |
| Full odds-curve calibration (H_009) | REJECTED | Near-flip bucket p=0.060 — borderline, direction reversal in H_010 |
| Referee/DoW bias (H_003) | EXPLORATORY (in-sample) | p=0.184 DoW, p=0.713 ref. Referee data now available for holdout re-run |
