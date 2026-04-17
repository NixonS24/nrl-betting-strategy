"""
Agent 5: Form Filter Overlay
=============================
Tests whether adding a form filter on top of the venue bias signal
improves strategy ROI without sacrificing too many bets.

Hypothesis: Only back home at AAMI Park when the home team also has
strong recent form (≥3 wins in last 5). The combination of venue
structural edge + momentum should produce higher win rates.

Also tests form as a fade filter at Campbelltown (only fade home
when home team is also in poor form).

Outputs:
  data/processed/quick_wins/form_filter_findings.md
  Returns result dict consumed by coordinator.
"""

import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path
import sys

ROOT      = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
PROCESSED = ROOT / "data" / "processed"
OUT       = PROCESSED / "quick_wins"
OUT.mkdir(parents=True, exist_ok=True)

from src.strategy.venue_bias import (
    BACK_HOME_VENUES, FADE_HOME_VENUES,
    MIN_EDGE, MIN_ODDS, MAX_ODDS, FLAT_STAKE,
    compute_venue_baselines, run_backtest, summarise,
)

FORM_THRESHOLD_BACK = 0.6   # home team needs ≥ 60% win rate in last 5 (= 3/5)
FORM_THRESHOLD_FADE = 0.4   # only fade home if home team form ≤ 40% (= ≤ 2/5)


def load_data() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED / "nrl_clean.csv", parse_dates=["date"])
    df["home_win"] = (df["result"] == "home_win").astype(int)
    return df


def run_filtered_backtest(df: pd.DataFrame, baselines: pd.DataFrame,
                           odds_col_home: str, odds_col_away: str,
                           label: str, form_filter: bool = True) -> pd.DataFrame:
    """
    Extended backtest that optionally applies form filter on top of venue bias.
    When form_filter=True:
      - back_home bets only fire if home_form_last5 >= FORM_THRESHOLD_BACK
      - fade_home bets only fire if home_form_last5 <= FORM_THRESHOLD_FADE
    """
    sub = df[df[odds_col_home].notna() & df[odds_col_away].notna()].copy()
    sub = sub.merge(baselines, on="venue_name", how="left")

    sub["implied_home"]   = 1 / sub[odds_col_home]
    sub["implied_away"]   = 1 / sub[odds_col_away]
    sub["edge_back_home"] = sub["base_hw_rate"] - sub["implied_home"]
    sub["edge_fade_home"] = (1 - sub["base_hw_rate"]) - sub["implied_away"]

    records = []
    for _, row in sub.iterrows():
        venue = row.get("venue_name", "")
        bet_type, odds, edge = None, None, None
        home_form = row.get("home_form_last5")

        if venue in BACK_HOME_VENUES and row["edge_back_home"] >= MIN_EDGE:
            # Apply form filter if requested
            if form_filter and pd.notna(home_form) and home_form < FORM_THRESHOLD_BACK:
                continue
            bet_type = "back_home"
            odds = row[odds_col_home]
            edge = row["edge_back_home"]

        elif venue in FADE_HOME_VENUES and row["edge_fade_home"] >= MIN_EDGE:
            # Apply form filter if requested
            if form_filter and pd.notna(home_form) and home_form > FORM_THRESHOLD_FADE:
                continue
            bet_type = "fade_home"
            odds = row[odds_col_away]
            edge = row["edge_fade_home"]

        if bet_type is None or pd.isna(odds) or odds < MIN_ODDS or odds > MAX_ODDS:
            continue

        won = (row["result"] == "home_win") if bet_type == "back_home" else (row["result"] == "away_win")
        profit = (odds - 1) * FLAT_STAKE if won else -FLAT_STAKE

        records.append({
            "source":             label,
            "date":               row["date"],
            "season":             row["season"],
            "home_team":          row["home_team"],
            "away_team":          row["away_team"],
            "venue":              venue,
            "bet_type":           bet_type,
            "odds":               round(float(odds), 3),
            "edge":               round(float(edge), 4),
            "home_form":          home_form,
            "base_hw_rate":       round(float(row["base_hw_rate"]), 3),
            "implied_prob":       round(1 / float(odds), 4),
            "result":             row["result"],
            "won":                won,
            "stake":              FLAT_STAKE,
            "profit":             round(float(profit), 2),
            "form_filter_active": form_filter,
        })

    bets = pd.DataFrame(records)
    if not bets.empty:
        bets = bets.sort_values("date").reset_index(drop=True)
        bets["cumulative_profit"] = bets["profit"].cumsum()
        bets["bankroll"] = 10_000 + bets["cumulative_profit"]
    return bets


def compare_strategies(df: pd.DataFrame, baselines: pd.DataFrame) -> dict:
    """Run baseline vs form-filtered backtest and compare."""

    # Baseline (no form filter) — bookmaker odds
    base_bets = run_backtest(df, baselines, "bk_home_close", "bk_away_close", "Baseline")
    base = summarise(base_bets)

    # Form-filtered — bookmaker odds
    filt_bets = run_filtered_backtest(df, baselines, "bk_home_close", "bk_away_close",
                                       "Form-Filtered", form_filter=True)
    filt = summarise(filt_bets)

    # Betfair validation — form filtered
    bf_filt_bets = run_filtered_backtest(df, baselines, "bf_home_open", "bf_away_open",
                                          "Betfair-Filtered", form_filter=True)
    bf_filt = summarise(bf_filt_bets)

    return {
        "baseline": base,
        "baseline_bets": base_bets,
        "filtered": filt,
        "filtered_bets": filt_bets,
        "bf_filtered": bf_filt,
        "bf_filtered_bets": bf_filt_bets,
    }


def analyse_form_impact(base_bets: pd.DataFrame, filt_bets: pd.DataFrame) -> dict:
    """Identify which bets were dropped by form filter and their P&L impact."""
    if base_bets.empty or filt_bets.empty:
        return {}

    # Bets in baseline but not in filtered = dropped by form filter
    base_keys = set(zip(base_bets["date"].astype(str), base_bets["home_team"], base_bets["away_team"]))
    filt_keys = set(zip(filt_bets["date"].astype(str), filt_bets["home_team"], filt_bets["away_team"]))
    dropped_keys = base_keys - filt_keys

    dropped = base_bets[
        base_bets.apply(lambda r: (str(r["date"]), r["home_team"], r["away_team"]) in dropped_keys, axis=1)
    ]

    return {
        "n_dropped": len(dropped),
        "dropped_profit": dropped["profit"].sum() if not dropped.empty else 0,
        "dropped_win_rate": dropped["won"].mean() if not dropped.empty else 0,
        "dropped": dropped,
    }


def write_findings(comparison: dict, impact: dict) -> str:
    base = comparison["baseline"]
    filt = comparison["filtered"]
    bf   = comparison["bf_filtered"]

    improved = (
        not filt.get("n") == 0 and
        filt.get("roi", -99) > base.get("roi", -99)
    )

    lines = [
        "# Agent 5 — Form Filter Overlay Findings\n",
        "Tests whether requiring strong home team form (≥3/5 recent wins) on top of",
        "venue bias improves ROI vs raw venue bias alone.\n",
        "---\n",
        "## Comparison: Baseline vs Form-Filtered (Bookmaker Odds, 2009–2025)\n",
        f"| Metric | Baseline | Form-Filtered | Change |",
        f"|---|---|---|---|",
        f"| Bets | {base.get('n', 0)} | {filt.get('n', 0)} | {filt.get('n', 0) - base.get('n', 0):+d} |",
        f"| Win rate | {base.get('win_rate', 0):.1%} | {filt.get('win_rate', 0):.1%} | {filt.get('win_rate', 0) - base.get('win_rate', 0):+.1%} |",
        f"| Total profit | ${base.get('profit', 0):,.0f} | ${filt.get('profit', 0):,.0f} | ${filt.get('profit', 0) - base.get('profit', 0):+,.0f} |",
        f"| ROI | {base.get('roi', 0):.2%} | {filt.get('roi', 0):.2%} | {filt.get('roi', 0) - base.get('roi', 0):+.2%} |",
        f"| Max drawdown | ${base.get('max_drawdown', 0):,.0f} | ${filt.get('max_drawdown', 0):,.0f} | ${filt.get('max_drawdown', 0) - base.get('max_drawdown', 0):+,.0f} |",
        "",
    ]

    if filt.get("n", 0) > 0:
        lines += [
            "## Form-Filtered: By Venue",
            comparison["filtered_bets"].groupby("venue").agg(
                n=("profit", "count"),
                wins=("won", "sum"),
                profit=("profit", "sum"),
                roi=("profit", lambda x: x.sum() / (len(x) * FLAT_STAKE))
            ).to_string(),
            "",
        ]

    if impact:
        lines += [
            "## Bets Dropped by Form Filter",
            f"- Dropped: {impact['n_dropped']} bets",
            f"- Their combined P&L: ${impact['dropped_profit']:+,.0f}",
            f"- Their win rate: {impact['dropped_win_rate']:.1%}",
            f"- Verdict: {'Good drop — those bets were losing' if impact['dropped_profit'] < 0 else 'Costly drop — those bets were winning'}",
            "",
        ]

    if bf.get("n", 0) > 0:
        lines += [
            "## Betfair Validation (Form-Filtered)",
            f"- {bf.get('n', 0)} bets, {bf.get('win_rate', 0):.1%} win rate, ROI {bf.get('roi', 0):.2%}",
            "",
        ]

    lines += [
        "---\n",
        "## Recommendation",
        f"**{'INTEGRATE' if improved else 'DO NOT INTEGRATE'}** — form filter "
        f"{'improves' if improved else 'does not improve'} ROI "
        f"({base.get('roi', 0):.2%} → {filt.get('roi', 0):.2%}).",
    ]

    if not improved and filt.get("roi", -99) > -0.05:
        lines.append("Consider raising FORM_THRESHOLD_BACK to 0.8 (4/5 wins) for a tighter filter.")

    text = "\n".join(lines)
    (OUT / "form_filter_findings.md").write_text(text)
    return text


def run() -> dict:
    print("\n[Agent 5] Form Filter Overlay — starting...")
    df = load_data()
    baselines = compute_venue_baselines(df)
    comparison = compare_strategies(df, baselines)
    impact = analyse_form_impact(
        comparison["baseline_bets"], comparison["filtered_bets"]
    )
    text = write_findings(comparison, impact)
    print(text)

    base_roi = comparison["baseline"].get("roi", 0)
    filt_roi = comparison["filtered"].get("roi", 0)
    improved = filt_roi > base_roi and comparison["filtered"].get("n", 0) > 0

    return {
        "agent": "form_filter",
        "significant": improved,
        "base_roi": base_roi,
        "filtered_roi": filt_roi,
        "roi_improvement": filt_roi - base_roi,
        "n_filtered": comparison["filtered"].get("n", 0),
        "findings_path": str(OUT / "form_filter_findings.md"),
        "comparison": comparison,
    }


if __name__ == "__main__":
    run()
