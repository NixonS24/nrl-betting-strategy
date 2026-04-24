# Workflow Update — Priority Rules
**From:** User (project owner) via Claude Code  
**Date:** 2026-04-24  
**Applies to:** All three models (OpenAI/Ideator, Claude/Architect, Gemini/Verifier)

---

## Priority Order — READ THIS FIRST

The research pipeline runs on two parallel tracks. **Track 1 always takes priority.**

### Track 1: User Scripts (HIGHEST PRIORITY)
The project owner may write, request, or modify scripts directly at any time.
These are located in:
- `src/strategy/` — live strategy and betting card scripts
- `src/agents/quick_wins/` — the six analysis agents
- Any script explicitly requested by the user in conversation

**When a user script exists or is requested:**
- **Claude:** Implement or modify it immediately, before processing any queued hypotheses.
- **Gemini:** Verify it using the standard checklist, but do not block it behind the H_XXX branching workflow — commit directly to `main` unless the user says otherwise.
- **Codex OpenAI:** Do not generate hypotheses that duplicate or conflict with work the user has explicitly commissioned. Check `PROGRESS.md` and `RESPONSE_FROM_CLAUDE.md` for what is already in progress.

### Track 2: Codex OpenAI Hypothesis Queue (BACKGROUND)
Codex OpenAI generates hypotheses → Claude implements → Gemini verifies.
This runs when no user-priority work is pending. Hypotheses queue in
`research/hypotheses/` and are processed in order (lowest H_XXX number first).

---

## Combined Workflow Diagram

```
User request?
    YES → Claude implements immediately
          Gemini verifies + commits to main
    NO  → OpenAI writes H_XXX.md
          Claude writes S_XXX.py + R_XXX.json
          Gemini red-teams + creates research/valid-H_XXX branch
          Gemini proposes PR to user
```

---

## What Each Model Should Do Right Now

### OpenAI
- Read `PROGRESS.md` and `data/processed/findings.md`
- Do NOT generate a hypothesis for the 45–55% calibration edge — Claude has confirmed it is p=0.18, NOT significant (see `RESPONSE_FROM_CLAUDE.md`)
- The next unqueued hypothesis opportunity is: **H_001** — Updated venue baselines
  (Claude has done the analysis; OpenAI should formally write the hypothesis file
  so Gemini can verify and merge it properly)
- After H_001: candidate hypotheses for H_002+ are listed at the bottom of this file

### Gemini
- Read `RESPONSE_FROM_CLAUDE.md` — Claude has flagged two issues requiring Gemini action:
  1. Mark 45–55% calibration edge as REJECTED in `PROGRESS.md`
  2. The malformed `CLAUDE.md` section needs restoring
- Once H_001 hypothesis file exists, verify Claude's backtest script and merge if clean
- User scripts committed to `main` do NOT need a research branch — just verify and approve

### Claude
- User scripts always first: when the user says "do X", do X before checking the hypothesis queue
- After completing user work, check `research/hypotheses/` for any unprocessed H_XXX files
- When writing research scripts, always output the standard JSON block + save chart

---

## Candidate Hypotheses for Codex OpenAI Queue (H_002 onward)

| ID | Hypothesis | Variables | Why it might work |
|---|---|---|---|
| H_001 | Updated venue baselines (2019+ data) improve ROI | `venue_name`, `season`, `bf_implied_home`, `result` | Home advantage declining trend (p=0.015); stale baselines underestimate edge |
| H_002 | Suncorp Stadium as FADE HOME venue | `venue_name='Suncorp Stadium'`, `result`, `bk_implied_home` | 46.4% HW rate (2019+), p=0.02, n=151 — but multi-team venue, needs decomposition |
| H_003 | Referee assignment day-of-week effect | `day_of_week`, `result`, `margin` | Friday HW 58.2% vs Thursday 54.6%; Wednesday 100% (small n); pattern may persist |
| H_004 | AAMI Park edge is Melbourne Storm only (not neutral venue games) | `venue_name='AAMI Park'`, `home_team`, `result` | All 57 Betfair games at AAMI Park are Storm home games — but verify no neutral games |
| H_005 | Away teams on long interstate travel (QLD↔NSW) perform worse in heat | `location`, `temperature`, `away_win`, `season` | Travel fatigue not significant overall but heat-adjusted travel not yet tested |

---

*All three models should re-read this file at the start of each session.*
ion.*
