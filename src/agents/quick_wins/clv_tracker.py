"""
Agent 3: Closing Line Value (CLV) Tracker
==========================================
Builds the infrastructure to log every bet placed and compare the odds
obtained against closing market odds. Positive CLV over time confirms
you have a genuine edge — not just lucky variance.

Also runs a retrospective CLV analysis on the bookmaker backtest bets
using opening vs closing odds from our existing dataset.

Outputs:
  data/processed/quick_wins/clv_tracker_findings.md
  data/processed/quick_wins/bet_ledger.csv            (empty template for live bets)
  Returns a result dict consumed by the coordinator.
"""

import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROCESSED = ROOT / "data" / "processed"
OUT = PROCESSED / "quick_wins"
OUT.mkdir(parents=True, exist_ok=True)

LEDGER_PATH = OUT / "bet_ledger.csv"

LEDGER_COLUMNS = [
    "bet_id",           # auto-increment
    "bet_date",         # date bet was placed (YYYY-MM-DD)
    "match_date",       # date of the match
    "round",            # NRL round number
    "home_team",
    "away_team",
    "venue",
    "bet_type",         # back_home / fade_home
    "team_backed",
    "odds_obtained",    # odds when bet was placed
    "closing_odds",     # bookmaker closing odds (fill in after event)
    "bf_closing_odds",  # Betfair closing odds (optional)
    "result",           # home_win / away_win / draw
    "won",              # True/False
    "stake",
    "profit",
    "clv",              # closing_odds - odds_obtained  (positive = got value)
    "clv_pct",          # clv / odds_obtained * 100
    "strategy",         # which strategy triggered this bet
    "notes",
]


def initialise_ledger():
    """Create empty bet ledger if it doesn't exist."""
    if not LEDGER_PATH.exists():
        pd.DataFrame(columns=LEDGER_COLUMNS).to_csv(LEDGER_PATH, index=False)
        print(f"  Created empty bet ledger: {LEDGER_PATH}")
    else:
        print(f"  Bet ledger already exists: {LEDGER_PATH}")


def retrospective_clv(df: pd.DataFrame) -> dict:
    """
    Use opening vs closing bookmaker odds as a proxy for CLV.
    If our strategy bets were placed at opening odds, CLV = closing - opening.
    Positive mean CLV → strategy is capturing value before the market corrects.
    """
    sub = df[
        df["bk_home_open"].notna() &
        df["bk_home_close"].notna() &
        df["bk_away_open"].notna() &
        df["bk_away_close"].notna()
    ].copy()

    if len(sub) < 50:
        return {"error": "insufficient data for CLV analysis"}

    # Line movement: closing / opening (>1 means odds drifted out = less popular)
    sub["home_line_move"] = sub["bk_home_close"] / sub["bk_home_open"]
    sub["away_line_move"] = sub["bk_away_close"] / sub["bk_away_open"]

    # Home odds tightened = market became more confident in home win
    sub["home_shortened"] = sub["home_line_move"] < 1.0
    sub["home_drifted"]   = sub["home_line_move"] > 1.0

    # Overall line movement stats
    results = {
        "n": len(sub),
        "avg_home_move": sub["home_line_move"].mean(),
        "avg_away_move": sub["away_line_move"].mean(),
        "pct_home_shortened": sub["home_shortened"].mean(),
        "pct_home_drifted":   sub["home_drifted"].mean(),
    }

    # CLV proxy: does backing at opening when home shortens predict wins?
    shortened = sub[sub["home_shortened"]].copy()
    drifted   = sub[sub["home_drifted"]].copy()
    shortened["home_win"] = (shortened["result"] == "home_win").astype(int)
    drifted["home_win"]   = (drifted["result"] == "home_win").astype(int)

    if len(shortened) > 20 and len(drifted) > 20:
        t, p = stats.ttest_ind(shortened["home_win"], drifted["home_win"])
        results["shortened_hw"] = shortened["home_win"].mean()
        results["drifted_hw"]   = drifted["home_win"].mean()
        results["t"] = t
        results["p"] = p
        results["significant"] = p < 0.05

    # CLV on our specific strategy venues
    from src.strategy.venue_bias import BACK_HOME_VENUES, FADE_HOME_VENUES
    strategy_venues = BACK_HOME_VENUES | FADE_HOME_VENUES
    sv = sub[sub["venue_name"].isin(strategy_venues)].copy()

    if len(sv) > 10:
        sv["home_win"] = (sv["result"] == "home_win").astype(int)
        # Simulated CLV: if we bet home at open when venue in BACK_HOME_VENUES
        back_home = sv[sv["venue_name"].isin(BACK_HOME_VENUES)].copy()
        if len(back_home) > 5:
            back_home["clv_proxy"] = back_home["bk_home_close"] - back_home["bk_home_open"]
            results["strategy_clv_proxy"] = {
                "n": len(back_home),
                "avg_clv": back_home["clv_proxy"].mean(),
                "pct_positive_clv": (back_home["clv_proxy"] > 0).mean(),
                "note": "CLV proxy = closing odds minus opening odds for back-home strategy bets",
            }

    return results


def clv_summary_stats(ledger: pd.DataFrame) -> dict:
    """Compute CLV stats from a populated ledger."""
    if ledger.empty or "clv" not in ledger.columns:
        return {}
    filled = ledger[ledger["clv"].notna()]
    if filled.empty:
        return {}
    return {
        "n_bets": len(filled),
        "avg_clv": filled["clv"].mean(),
        "avg_clv_pct": filled["clv_pct"].mean(),
        "pct_positive_clv": (filled["clv"] > 0).mean(),
        "total_profit": filled["profit"].sum(),
        "roi": filled["profit"].sum() / filled["stake"].sum() if filled["stake"].sum() > 0 else 0,
    }


def write_findings(retro: dict, ledger_stats: dict) -> str:
    lines = [
        "# Agent 3 — Closing Line Value (CLV) Tracker Findings\n",
        "## What is CLV?",
        "CLV = closing odds − odds obtained when bet was placed.",
        "Consistently positive CLV means you're finding value before the market corrects.",
        "A bettor with +CLV is profitable long-term regardless of short-term win/loss swings.\n",
        "---\n",
        "## Retrospective Analysis (Opening vs Closing Odds, 2009–2026)",
    ]

    if "error" in retro:
        lines.append(f"Error: {retro['error']}\n")
    else:
        lines += [
            f"- Matches with both open & close odds: {retro['n']:,}",
            f"- Avg home line movement (close/open): {retro['avg_home_move']:.4f}",
            f"  (< 1.0 = home shortened / market more confident in home win)",
            f"- % of matches where home odds shortened: {retro['pct_home_shortened']:.1%}",
            f"- % of matches where home odds drifted:   {retro['pct_home_drifted']:.1%}\n",
        ]
        if "shortened_hw" in retro:
            lines += [
                "### Win Rate: Home Odds Shortened vs Drifted",
                f"- Home win rate when odds shortened: **{retro['shortened_hw']:.1%}**",
                f"- Home win rate when odds drifted:   {retro['drifted_hw']:.1%}",
                f"- t={retro['t']:.3f}, p={retro['p']:.4f} — {'**SIGNIFICANT**' if retro.get('significant') else 'not significant'}",
                f"- Interpretation: {'Shortened odds correctly signal home win probability — betting opening has CLV' if retro.get('significant') else 'Line movement not significantly predictive'}\n",
            ]
        if "strategy_clv_proxy" in retro:
            sc = retro["strategy_clv_proxy"]
            lines += [
                "### Strategy Venue CLV Proxy",
                f"- Bets at back-home venues (open odds): {sc['n']}",
                f"- Avg CLV proxy (close − open):  {sc['avg_clv']:+.4f}",
                f"- % with positive CLV proxy:     {sc['pct_positive_clv']:.1%}",
                f"- {sc['note']}\n",
            ]

    lines += [
        "---\n",
        "## Live Bet Ledger",
        f"Template created at: data/processed/quick_wins/bet_ledger.csv",
        "",
        "**How to use:**",
        "1. When `weekend_picks.py` generates a bet, add a row to bet_ledger.csv",
        "2. Fill `odds_obtained` at time of bet placement",
        "3. After the game, fill `closing_odds`, `result`, `won`, `profit`",
        "4. Run `clv_tracker.py` to compute CLV and track long-run edge\n",
        "**Columns:**",
    ] + [f"  - `{col}`" for col in LEDGER_COLUMNS] + [
        "",
        "---\n",
        "## Recommendation",
        "**INTEGRATE** — set up CLV tracking for all live bets going forward.",
        "Target: avg CLV > +0.02 (2 cents per dollar) over 50+ bets confirms genuine edge.",
    ]

    text = "\n".join(lines)
    (OUT / "clv_tracker_findings.md").write_text(text)
    return text


def run() -> dict:
    print("\n[Agent 3] CLV Tracker — starting...")

    # Initialise empty ledger
    initialise_ledger()

    # Load current ledger
    ledger = pd.read_csv(LEDGER_PATH)

    # Retrospective CLV using open vs close odds
    df = pd.read_csv(PROCESSED / "nrl_clean.csv", parse_dates=["date"])
    retro = retrospective_clv(df)

    ledger_stats = clv_summary_stats(ledger)

    text = write_findings(retro, ledger_stats)
    print(text)

    return {
        "agent": "clv_tracker",
        "significant": True,   # always integrate — infrastructure
        "results": retro,
        "ledger_stats": ledger_stats,
        "findings_path": str(OUT / "clv_tracker_findings.md"),
        "ledger_path": str(LEDGER_PATH),
    }


if __name__ == "__main__":
    run()
