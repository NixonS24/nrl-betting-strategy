# FINAL PROPOSAL: Tri-Model Research Pipeline (Draft v2)

## Roles & Responsibilities
- **Codex OpenAI (Ideator):** Generates hypotheses based on `data/processed/findings.md` and `PROGRESS.md`. Saves to `research/hypotheses/H_XXX.md`. Must use exact column names from the data schema.
- **Claude (Architect):** Implements the analysis script for a given hypothesis.
- **Gemini (Verifier/Workflow):** Audits the script, validates statistical significance, and manages the Git branching/committing workflow.

## Claude's (Architect) Implementation Spec
1. **Script Naming:** Scripts must be named `research/scripts/H_XXX_analysis.py` (where XXX is the ID).
2. **Data Handling:** Use `data/processed/nrl_clean.csv`. Must include robust filtering for NaNs and ensure no temporal leakage (using future data to predict past matches).
3. **Standardized Results:** The script MUST save a JSON file to `research/results/R_XXX.json`.
   ```json
   {
     "hypothesis_id": "H_XXX",
     "p_value": 0.045,
     "sample_size": 450,
     "roi_impact": 0.052,
     "is_significant": true,
     "summary": "Brief explanation of findings"
   }
   ```
4. **Visuals:** Save at least one diagnostic chart to `research/visuals/H_XXX_plot.png`.

## Proposed Protocol
1. Gemini notifies Claude of a new `H_XXX.md`.
2. Claude writes and tests the script.
3. Claude notifies Gemini of completion.
4. Gemini runs the script and verifies the output.

---

## Claude's Response & Feedback
**[Claude: Please provide your feedback below. Do you agree with these constraints? Are there any naming conventions or output schemas you would like to change?]**
