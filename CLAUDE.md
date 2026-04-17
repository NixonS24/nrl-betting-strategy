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
python test_read_data.py

# Run the full agent research team (end-to-end pipeline)
python -m src.agents.team

# Skip data sourcing (use existing raw data only)
python -m src.agents.team --skip-sourcing

# Fetch supplementary datasets only (no analysis)
python -m src.agents.team --source-only

# Run with a custom task
python -m src.agents.team --task "Focus only on Venue Bias for ANZ Stadium"

# Launch Jupyter for notebooks
jupyter lab
```

No build, test, or lint tooling is configured yet.

## Architecture

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
