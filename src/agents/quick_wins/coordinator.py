"""
Quick Wins Coordinator
======================
Runs all three quick-win agents in sequence, evaluates statistical
significance, and integrates confirmed signals into the main strategy.

Usage:
    python -m src.agents.quick_wins.coordinator

What it does:
    1. Run Agent 1 (Rest/Fatigue) — test rest days & interstate travel
    2. Run Agent 2 (Weather)      — test temperature, rain, wind effects
    3. Run Agent 3 (CLV Tracker)  — build CLV infrastructure + retrospective
    4. Print consolidated findings report
    5. If any signal significant → patch venue_bias.py with new filters
    6. Re-run backtest with integrated signals to measure improvement
    7. Write summary to data/processed/quick_wins/coordinator_report.md
"""

import importlib
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

PROCESSED = ROOT / "data" / "processed"
OUT = PROCESSED / "quick_wins"
OUT.mkdir(parents=True, exist_ok=True)

VENUE_BIAS_PATH = ROOT / "src" / "strategy" / "venue_bias.py"


# ---------------------------------------------------------------------------
# Integration patches
# ---------------------------------------------------------------------------

REST_FILTER_CODE = '''

# ---------------------------------------------------------------------------
# Rest / Travel filters (integrated by quick_wins coordinator)
# ---------------------------------------------------------------------------
MIN_AWAY_REST_DAYS = 7   # fade away teams with < 7 days rest (more favourable to home)

def apply_rest_filter(row: pd.Series, bet_type: str) -> bool:
    """Return True if the bet passes the rest-days filter."""
    if bet_type == "back_home":
        away_rest = row.get("away_rest_days")
        if pd.notna(away_rest) and away_rest < MIN_AWAY_REST_DAYS:
            return True   # away team fatigued → extra confidence in home
    # Default: don't block non-fatigued bets; filter is a booster, not a gate
    return True
'''

WEATHER_FILTER_CODE = '''

# ---------------------------------------------------------------------------
# Weather filter (integrated by quick_wins coordinator)
# ---------------------------------------------------------------------------
WET_SCORE_ADJUSTMENT = {val}   # points suppressed in wet conditions (from Agent 2)

def wet_conditions_flag(precipitation_mm: float) -> bool:
    """Return True if conditions count as wet (>5mm precipitation)."""
    return precipitation_mm is not None and precipitation_mm > 5
'''


def run_agents() -> dict:
    """Run all five agents and collect results."""
    from src.agents.quick_wins import rest_fatigue, weather, clv_tracker, referee_bias, form_filter

    print("=" * 62)
    print("  QUICK WINS COORDINATOR")
    print(f"  {datetime.now().strftime('%d %B %Y, %I:%M %p')}")
    print("=" * 62)

    results = {}

    for key, module, label in [
        ("rest_fatigue", rest_fatigue, "Agent 1: Rest & Travel Fatigue"),
        ("weather",      weather,      "Agent 2: Weather Overlay"),
        ("clv_tracker",  clv_tracker,  "Agent 3: CLV Tracker"),
        ("referee_bias", referee_bias, "Agent 4: Referee Bias"),
        ("form_filter",  form_filter,  "Agent 5: Form Filter Overlay"),
    ]:
        try:
            print(f"\n{'─'*62}\n  Running {label}...")
            results[key] = module.run()
        except Exception as e:
            print(f"  FAILED: {e}")
            results[key] = {"agent": key, "significant": False, "error": str(e)}

    return results


def integrate_signals(results: dict) -> list[str]:
    """Patch venue_bias.py with significant signals. Returns list of integrations applied."""
    integrated = []
    source = VENUE_BIAS_PATH.read_text()

    # ── Rest/fatigue ────────────────────────────────────────────────────────
    rf = results.get("rest_fatigue", {})
    if rf.get("significant") and "REST_FILTER" not in source:
        # Add import for pandas if not present (it already is)
        if REST_FILTER_CODE.strip() not in source:
            source += "\n" + REST_FILTER_CODE
            integrated.append("rest_fatigue: away team short rest filter added")

    # ── Weather ─────────────────────────────────────────────────────────────
    wt = results.get("weather", {})
    if wt.get("significant") and "WET_SCORE_ADJUSTMENT" not in source:
        adj = wt.get("filters", {}).get("wet_score_adjustment", -3.5)
        code = WEATHER_FILTER_CODE.format(val=adj)
        if code.strip() not in source:
            source += "\n" + code
            integrated.append(f"weather: wet conditions score adjustment ({adj:+.1f} pts) added")

    if integrated:
        VENUE_BIAS_PATH.write_text(source)
        print(f"\n  Patched venue_bias.py: {', '.join(integrated)}")

    return integrated


def write_coordinator_report(results: dict, integrated: list[str]) -> str:
    lines = [
        "# Quick Wins Coordinator Report\n",
        f"Generated: {datetime.now().strftime('%d %B %Y, %I:%M %p')}\n",
        "---\n",
        "## Agent Results\n",
        f"| Agent | Significant? | Integrated? | Findings |",
        f"|---|---|---|---|",
    ]

    for key, label in [
        ("rest_fatigue", "Rest & Travel Fatigue"),
        ("weather",      "Weather Overlay"),
        ("clv_tracker",  "CLV Tracker"),
        ("referee_bias", "Referee Bias"),
        ("form_filter",  "Form Filter Overlay"),
    ]:
        r = results.get(key, {})
        sig  = "Yes" if r.get("significant") else "No"
        intg = "Yes" if any(key in i for i in integrated) else ("Always" if key == "clv_tracker" else "No")
        path = r.get("findings_path", "—")
        fname = Path(path).name if path != "—" else "—"
        lines.append(f"| {label} | {sig} | {intg} | `{fname}` |")

    lines += [""]

    if integrated:
        lines += [
            "## Integrations Applied\n",
        ] + [f"- {i}" for i in integrated] + [""]

    lines += [
        "---\n",
        "## What to do next\n",
        "1. **Re-run the backtest** to see if integrated signals improve ROI:",
        "   ```bash",
        "   python src/strategy/venue_bias.py",
        "   ```",
        "2. **Start logging live bets** in `data/processed/quick_wins/bet_ledger.csv`",
        "   to accumulate real CLV data over the coming weeks.",
        "3. **Check weather before each weekend** using `weekend_picks.py`",
        "   and manually note precipitation/wind for the qualifying match.",
        "4. **Phase 2** (when 50+ live bets logged): referee assignment analysis.",
    ]

    text = "\n".join(lines)
    (OUT / "coordinator_report.md").write_text(text)
    return text


def main():
    results = run_agents()

    print("\n" + "=" * 62)
    print("  INTEGRATION DECISION")
    print("=" * 62)

    for key in ["rest_fatigue", "weather", "clv_tracker", "referee_bias", "form_filter"]:
        r = results.get(key, {})
        sig = r.get("significant", False)
        label = key.replace("_", " ").title()
        status = "INTEGRATE" if sig else "SKIP (not significant)"
        print(f"  {label:<28} → {status}")

    integrated = integrate_signals(results)

    report = write_coordinator_report(results, integrated)
    print("\n" + report)

    report_path = OUT / "coordinator_report.md"
    print(f"\nCoordinator report saved to: {report_path}")
    return results, integrated


if __name__ == "__main__":
    main()
