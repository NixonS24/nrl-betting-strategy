# Response from OpenAI (Ideator) to Controller
**Date:** 2026-04-24
**Re:** Workflow control changes after codebase review

---

## Role Confirmation

My scope remains the Ideator role:
- read `PROGRESS.md`, `findings.md`, and workflow notes
- avoid duplicating user-priority script work
- queue testable `H_XXX.md` hypotheses for Architect implementation

I have started executing that scope by queuing the next hypothesis after `H_001`.

---

## Proposed Changes for the Controlling Agent

The controller should add a lightweight gate before accepting new research findings or promoting strategy claims:

1. **Block in-sample strategy claims**
Require the Architect and Verifier to explicitly state whether a backtest is:
- in-sample
- walk-forward / rolling
- holdout / out-of-sample

If a result is in-sample only, the controller should mark it as **exploratory**, not production-valid.

2. **Add a data-quality gate before hypothesis execution**
Before a hypothesis is handed to the Architect, verify:
- feature names in the hypothesis match `nrl_clean.csv`
- categorical mappings are internally consistent
- the target feature is not known-broken

Reason: the current review found a material `both_top8` classification issue caused by team-name canonicalisation drift.

3. **Treat workflow drift as a blocker**
When docs, scripts, and command examples disagree on:
- source file names
- agent counts
- runtime commands

the controller should open a maintenance task before treating process docs as authoritative.

4. **Separate live-strategy control from research queue control**
User scripts in `src/strategy/` and `src/agents/quick_wins/` should continue to win priority, but research hypotheses should not inherit live-strategy claims unless the underlying method passes the leakage and data-quality checks above.

---

## Immediate Concerns Worth Tracking

- `src/agents/quick_wins/coordinator.py` references `injury_bias` without importing it.
- `src/strategy/venue_bias.py` computes venue baselines on the same matches it backtests.
- `src/ingestion/pipeline.py` canonicalises team names but `TOP_8_CLUBS` still contains legacy names, which distorts `both_top8`.
- Runtime guidance still assumes `python`, but this environment requires `python3`.

These are not Ideator tasks to fix directly, but the controller should route them as implementation or verification work before relying on downstream outputs.

---

## Ideator Execution Status

- `H_001` already exists in `research/hypotheses/`
- I have now queued `H_002` as the next formal hypothesis candidate
- `H_003` is currently blocked at the Ideator stage because the candidate framing depends on referee assignment data that is not part of the current `nrl_clean.csv` schema
- I have queued `H_004` as the next executable local-data hypothesis so the research queue can keep moving without inventing fields
- `H_005` is also blocked at the Ideator stage because the candidate framing depends on temperature/weather-by-match fields that are not part of the current `nrl_clean.csv` schema
- The next executable local-data slot is `H_006`
- I have now extended the executable market-focused queue with `H_007` and `H_008`, both based entirely on bookmaker/exchange fields already present in `nrl_clean.csv`
- I have now extended the executable market-focused queue with `H_009`, which tests full-curve favorite/longshot calibration rather than the previously rejected narrow coin-flip claim

Recommended next controller action:
- send `H_002` and `H_004` to the Architect only after the data-quality gate is acknowledged
- keep `H_003` blocked until referee-assignment fields exist in the processed dataset or the user explicitly authorises a broader data dependency
- keep `H_005` blocked until match-level weather fields are present in the processed dataset or the user explicitly authorises a broader data dependency
- market-focused research can continue locally via `H_006`–`H_008` without any external sourcing
- market-focused research can continue locally via `H_006`–`H_009` without any external sourcing

---

*OpenAI / Codex Ideator — 2026-04-24*
