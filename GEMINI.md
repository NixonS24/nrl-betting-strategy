# Gemini Verification Protocol

You are the **Verifier** and **Workflow Manager**. Your goal is to ensure only high-quality, non-hallucinated findings reach the master branch.

## Priority Order (Mandatory)
The research pipeline runs on two parallel tracks. **Track 1 always takes priority.**

### Track 1: User Scripts (HIGHEST PRIORITY)
- The project owner may write, request, or modify scripts directly (e.g., `src/strategy/`, `src/agents/quick_wins/`).
- **Your Role:** Verify these immediately using the standard checklist.
- **Commit Logic:** Commit directly to `main` unless the user specifies a branch. Do NOT block user-requested work behind the H_XXX branching workflow.

### Track 2: Codex OpenAI Hypothesis Queue (BACKGROUND)
- Codex OpenAI generates hypotheses → Claude implements → Gemini verifies.
- **Workflow:** Create `research/valid-H_XXX` branch, update `findings.md`, and propose a PR summary.

## Verification Checklist (The "Red Team")
1. **Sample Size:** Is `sample_size` sufficient for the test? (Minimum n=50 for basic edges, n=100+ preferred).
2. **P-Value Audit:** Check if the p-value is robust or a result of over-filtering (p-hacking).
3. **Temporal Leakage:** Ensure `H_XXX_analysis.py` doesn't use data from the "future" relative to the match being predicted.
4. **In-Sample Block:** Strictly enforce out-of-sample (holdout) validation. If a result is in-sample only, mark it as **EXPLORATORY**. Check `backtest_type` in JSON.
5. **Data Quality Gate:** For hypotheses using `both_top8` or team-specific columns, verify team canonicalisation hasn't drifted.
6. **Logic Check:** Does the finding contradict established baseline trends (e.g., `findings.md`)?
7. **Chart Audit:** Verify the chart in `research/visuals/` confirms the trend/distribution claimed in the JSON.

## Output Schema (Parsed by Gemini)
Claude scripts save to `research/results/R_XXX.json`:
```json
{
  "hypothesis_id": "H_XXX",
  "p_value": float,
  "sample_size": int,
  "roi_impact": float,
  "is_significant": boolean,
  "method": string,
  "data_window": string,
  "summary": string
}
```

## Operation
- **Runtime:** This environment requires **`python3`**. Update all command examples accordingly.
- **Trigger:** Manual invocation (e.g., "Analyse the results of H_001").
- **Run Analysis:** `python3 research/scripts/H_XXX_analysis.py`
- **Check Progress:** `cat PROGRESS.md`

## Current Queue (updated 2026-04-24, session 7)

### Scripts awaiting Gemini verification

| Script | Status | Notes |
|---|---|---|
| `H_010_analysis.py` | **Pending run** | `python3 research/scripts/H_010_analysis.py` — near-flip prospective design |

### Pending Gemini actions
1. Run `H_010_analysis.py` — check `direction_reversal_detected` field in R_010.json. If true, mark REJECTED (noise). If false and p<0.05, consider exploratory strategy branch.
2. Flag R_003.json as `[IN-SAMPLE, NOT VALIDATED]` in `data/processed/findings.md` — the result used in-sample data only.
3. Verify `src/strategy/venue_bias.py` BlueBet Stadium addition (committed by Claude this session) — run backtest to confirm no regressions.
4. Consider H_003 holdout re-run: `data/raw/referee_assignments.csv` (264 rows, 2024+) is now available. A proper holdout test is possible if the referee data can be joined to `nrl_clean.csv` via match_id or date/team matching.

## Confirmed Results (all H_001–H_009 verified)

| Hypothesis | Verdict | p-value | Action |
|---|---|---|---|
| H_001 (venue recalibration) | REJECTED global / CONFIRMED BlueBet | p=0.0001 | ✓ BlueBet added to strategy |
| H_002 (Suncorp fade) | EXPLORATORY | p=0.071 | No strategy branch |
| H_003 (referee/DoW) | EXPLORATORY — in-sample only | p=0.184 DoW | Flag in findings.md |
| H_004 (AAMI Park decomp) | CONFIRMED team-linked | Storm 100% | ✓ Annotated in strategy |
| H_006 (BK/BF disagreement) | EXPLORATORY | n=6 holdout | No strategy branch |
| H_007 (BK line movement) | REJECTED | ROI -4.6% | Done |
| H_008 (overround intensity) | REJECTED | — | Done |
| H_009 (odds-curve calibration) | REJECTED | p=0.076 | Done — near-flip → H_010 |
| H_010 (near-flip prospective) | **Pending** | — | Run script |
