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

## Current Queue (as of 2026-04-24)

### Scripts awaiting Gemini verification

| Script | Status | Notes |
|---|---|---|
| `H_001_analysis.py` | R_001.json exists | Reviewed by Claude — see RESPONSE_FROM_CLAUDE.md. Split finding: BlueBet CONFIRMED, blanket recalibration REJECTED |
| `H_002_analysis.py` | R_002.json exists | Reviewed by Claude — p=0.071, n=24 holdout bets. Mark EXPLORATORY, do not trade |
| `H_004_analysis.py` | **Pending run** | `python3 research/scripts/H_004_analysis.py` — checks if AAMI Park is Storm-only |
| `H_006_analysis.py` | **Pending run** | `python3 research/scripts/H_006_analysis.py` — BK/BF disagreement filter |

### Pending Gemini actions
1. Run `H_004_analysis.py` → verify `composition.storm_pct` and `classification` field in R_004.json
2. Run `H_006_analysis.py` → verify `is_exploratory` flags; enforce n≥30 gate
3. Update `PROGRESS.md` with H_004 and H_006 outcomes after verification
4. If H_004 confirms Storm-only: update `data/processed/findings.md` to reclassify AAMI Park edge as team-linked
5. BlueBet Stadium: once H_001 split decision is accepted, add to production strategy in `src/strategy/venue_bias.py`

## Confirmed Results (Claude's analysis)

| Hypothesis | Verdict | p-value | Action |
|---|---|---|---|
| H_001 (venue recalibration) | REJECTED (global) / CONFIRMED (BlueBet) | p=0.0001 (BlueBet) | Promote BlueBet only |
| H_002 (Suncorp fade) | EXPLORATORY | p=0.071 | No strategy branch |
| H_004 (AAMI Park decomp) | Pending | — | Expected: team-linked classification |
| H_006 (disagreement filter) | Pending | — | Expected: exploratory (thin Betfair window) |
