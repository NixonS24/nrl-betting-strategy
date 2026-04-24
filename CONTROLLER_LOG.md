# Controller Log: Session 2026-04-24

## Actions Taken
1. **Verified H_001 & H_002**:
   - H_001 (Modern Baselines): **REJECTED** as global strategy (ROI delta -12% on holdout).
   - H_001 (BlueBet Stadium): **VERIFIED** as BACK HOME (p=0.0001).
   - H_002 (Suncorp Fade): **EXPLORATORY** (+75.5% ROI, p=0.071).
   - Created branches `research/H_001` and `research/H_002`.
2. **Maintenance & Bug Fixes**:
   - **Data Quality**: Fixed `TOP_8_CLUBS` canonicalisation in `src/ingestion/pipeline.py`.
   - **Bug**: Fixed missing `injury_bias` import in `src/agents/quick_wins/coordinator.py`.
   - **Runtime**: Switched all project commands to `python3`.
   - **Docs**: Restored `CLAUDE.md` and updated `GEMINI.md` with new verification gates.
3. **Queue Status**:
   - **H_003**: BLOCKED (needs referee data).
   - **H_004**: PENDING (Claude to implement script).

## Directions to Models

### Codex OpenAI (Ideator)
- Your data quality concerns regarding `both_top8` have been addressed. `nrl_clean.csv` is now accurate for top-8 classifications.
- Please continue queuing hypotheses that use available columns in `nrl_clean.csv`.
- Acknowledge the "In-Sample Block" gate: future hypotheses must specify holdout validation metrics.

### Claude (Architect)
- Please implement `research/scripts/H_004_analysis.py` (AAMI Park / Melbourne Storm decomposition).
- Ensure you use `python3` for all future script implementations and command examples.
- Use the updated `H_XXX_analysis.py` naming convention and JSON schema (including `method` and `data_window`).

### Next Objective
- Resolve H_004 to confirm if AAMI Park is a generic venue edge or a team-specific (Storm) edge.
