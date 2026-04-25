# NRL Gambling Bias Research

## Objective

Identify and exploit statistically significant pricing inefficiencies in Australian NRL gambling markets. Live strategy operational from Round 7 2026.

## Status

**Live** — Venue Bias strategy running. Bookmaker backtest: 79 bets, +9.32% ROI. R7 result: Broncos +$4.05. Tri-model research pipeline active.

## Confirmed Edges

| Signal | Venue / Condition | Base Rate | ROI (backtest) | Status |
|---|---|---|---|---|
| Back home | AAMI Park (Melbourne Storm) | 78.9% HW | +20.1% | Live |
| Back home | BlueBet Stadium (Panthers) | 82.3% HW | Confirmed | **Live (added R9 2026)** |
| Back home | Olympic Park, QSAC, Sydney Showground | ~75% HW | Live | Live |
| Fade home | Campbelltown Sports Stadium | 30.8% HW | Live | Live |
| Weather overlay | Wet conditions | −4.8 pts/game | p<0.0001 | Use for overs/unders |
| Line movement | Home odds shorten >5% | 60.8% HW | p<0.0001 | Bet early in week |

## Setup

```bash
pip install -r requirements.txt
```

## How to Run

```bash
# This week's bets
python3 src/strategy/weekend_picks.py --bankroll 113.04

# Full backtest
python3 src/strategy/venue_bias.py

# Run all analysis agents
python3 -m src.agents.quick_wins.coordinator

# Research hypothesis scripts
python3 research/scripts/H_XXX_analysis.py

# Rebuild full dataset
python3 src/ingestion/pipeline.py && python3 src/analysis/bias_analysis.py
```

## Project Structure

```
src/
  ingestion/pipeline.py          — merges 3 sources → nrl_clean.csv
  analysis/bias_analysis.py      — statistical tests for all 3 biases
  strategy/
    venue_bias.py                — backtest engine + Kelly staking
    weekend_picks.py             — weekly betting card generator
    generate_report.py           — Word doc report
  agents/
    team.py                      — original 4-agent research pipeline
    quick_wins/
      coordinator.py             — runs all 6 quick-wins agents
      rest_fatigue.py / weather.py / clv_tracker.py
      referee_bias.py / form_filter.py / injury_bias.py

research/
  hypotheses/H_XXX.md            — written by OpenAI Ideator
  scripts/H_XXX_analysis.py      — written by Claude Architect
  results/R_XXX.json             — output from analysis scripts
  visuals/H_XXX_plot.png         — diagnostic charts

data/
  raw/nrl.xlsx                   — AusSportsBetting odds 2013–present
  processed/nrl_clean.csv        — unified dataset (5,435 × 41 cols)
```

## Multi-Model Research Pipeline

Three models collaborate on hypothesis generation and validation:

- **OpenAI/Codex (Ideator):** Writes `research/hypotheses/H_XXX.md`
- **Claude (Architect):** Implements `research/scripts/H_XXX_analysis.py`
- **Gemini (Verifier):** Runs scripts, red-teams results, manages git workflow

See `CLAUDE.md`, `GEMINI.md`, and `WORKFLOW_UPDATE.md` for protocol details.

## Key Statistical Findings

| Bias | Test | Result |
|---|---|---|
| Draw Bias | Chi-square | p=0.62 — not significant |
| Form/Momentum | Point-biserial | p<0.0001, r=0.20 — real but already priced |
| **Venue/Home Bias** | ANOVA + t-tests | **p<0.0001** — large and exploitable |
| Home advantage trend | Linear regression | p=0.015, declining ~0.19%/yr |
