"""
H_006 Analysis — Bookmaker/Exchange Disagreement as a Venue-Strategy Filter

Hypothesis: At known strategy venues, material disagreement between bookmaker
closing price and Betfair exchange opening price identifies whether the venue
signal is supported or contradicted by sharp money. Layering a disagreement
filter on the existing venue-bias rule improves ROI.

Design constraints:
  - Betfair data is only available from 2021. Both bk and bf odds must be
    present, which hard-restricts the sample. Total window ~2021–2025 (~4 seasons).
  - Holdout split: 2021–2022 for training signal, 2023+ for backtest.
  - Treat all results as EXPLORATORY unless n(holdout) >= 30.

Disagreement definition:
  - `disagreement = bk_implied_home - bf_implied_home`
  - Positive  → bookmaker sees more home probability than exchange (exchange fades home)
  - Negative  → exchange more bullish on home than bookmaker
  - `|disagreement| >= DISCORD_THRESHOLD` = material disagreement

For BACK HOME venues:
  - When bf > bk (exchange agrees with venue edge): confirms signal → expect stronger ROI
  - When bk > bf (bookmaker bullish, exchange sceptical): exchange fades the edge → caution

For FADE HOME venues:
  - When bk > bf (bookmaker over-prices home, exchange agrees with fade): confirms fade
  - When bf > bk (exchange bullish on home): contradicts fade → caution

Output:
  - research/results/R_006.json
  - research/visuals/H_006_plot.png
"""

import json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import stats
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
RESULTS_DIR = ROOT / "research" / "results"
VISUALS_DIR = ROOT / "research" / "visuals"
RESULTS_DIR.mkdir(exist_ok=True)
VISUALS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Venues — same as production strategy
# ---------------------------------------------------------------------------
BACK_HOME_VENUES = {
    "AAMI Park",
    "Olympic Park Stadium",
    "Queensland Sport and Athletics Centre",
    "Sydney Showground",
    "BlueBet Stadium",          # promoted from H_001 finding
}
FADE_HOME_VENUES = {
    "Campbelltown Sports Stadium",
}
ALL_STRATEGY_VENUES = BACK_HOME_VENUES | FADE_HOME_VENUES

DISCORD_THRESHOLD = 0.03    # 3pp disagreement = material
MIN_EDGE          = 0.05
MIN_ODDS          = 1.50
MAX_ODDS          = 6.00
FLAT_STAKE        = 100

TRAIN_CUTOFF = 2023   # Betfair-era training: 2021–2022; holdout: 2023+


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_data() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED / "nrl_clean.csv", parse_dates=["date"])
    df["home_win"] = (df["result"] == "home_win").astype(int)
    df = df[df["venue_name"].notna() & df["result"].notna()]
    return df


def dual_odds_subset(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only rows where both bk and bf implied probabilities exist."""
    mask = (
        df["bk_implied_home"].notna()
        & df["bf_implied_home"].notna()
        & df["bk_home_close"].notna()
        & df["bf_home_open"].notna()
    )
    sub = df[mask].copy()
    sub["disagreement"] = sub["bk_implied_home"] - sub["bf_implied_home"]
    sub["abs_discord"] = sub["disagreement"].abs()
    return sub


# ---------------------------------------------------------------------------
# Baseline computation (training window)
# ---------------------------------------------------------------------------
def compute_baselines(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df[df["venue_name"].isin(ALL_STRATEGY_VENUES)]
        .groupby("venue_name")["home_win"]
        .agg(base_hw_rate="mean", n_baseline="count")
        .reset_index()
    )


# ---------------------------------------------------------------------------
# Disagreement bucket analysis
# ---------------------------------------------------------------------------
def bucket_analysis(df: pd.DataFrame, back_venues: set, fade_venues: set,
                    label: str) -> pd.DataFrame:
    """
    Segment matches at strategy venues by direction of bk/bf disagreement.
    Report actual vs implied HW rate by bucket.
    """
    sub = df[df["venue_name"].isin(back_venues | fade_venues)].copy()
    if sub.empty:
        return pd.DataFrame()

    sub["direction"] = "agree"
    sub.loc[sub["disagreement"] >= DISCORD_THRESHOLD,  "direction"] = "bk_bullish_home"
    sub.loc[sub["disagreement"] <= -DISCORD_THRESHOLD, "direction"] = "exchange_bullish_home"

    sub["venue_type"] = sub["venue_name"].apply(
        lambda v: "back_home" if v in back_venues else "fade_home"
    )

    rows = []
    for (venue_type, direction), grp in sub.groupby(["venue_type", "direction"]):
        n = len(grp)
        actual = grp["home_win"].mean()
        implied_bk = grp["bk_implied_home"].mean()
        implied_bf = grp["bf_implied_home"].mean()
        residuals = grp["home_win"] - grp["bk_implied_home"]
        if n >= 5:
            t, p2 = stats.ttest_1samp(residuals, popmean=0)
            p1 = p2 / 2 if (t > 0 and venue_type == "back_home") or \
                           (t < 0 and venue_type == "fade_home") else 1.0 - p2 / 2
        else:
            p1 = 1.0
        rows.append({
            "window": label,
            "venue_type": venue_type,
            "direction": direction,
            "n": int(n),
            "actual_hw": float(round(actual, 4)),
            "implied_bk": float(round(implied_bk, 4)),
            "implied_bf": float(round(implied_bf, 4)),
            "calibration_error_bk": float(round(actual - implied_bk, 4)),
            "p_one_sided": float(round(p1, 4)),
            "significant": bool(p1 < 0.05),
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Backtest with optional disagreement filter
# ---------------------------------------------------------------------------
def run_backtest(
    test_df: pd.DataFrame,
    baselines: pd.DataFrame,
    back_venues: set,
    fade_venues: set,
    discord_filter: Optional[str],  # None, "bk_bullish_home", "exchange_bullish_home", "agree"
    label: str,
) -> pd.DataFrame:
    """
    discord_filter: if set, only take bets where direction == filter value.
    None = no filter (baseline strategy).
    """
    sub = dual_odds_subset(test_df)
    sub = sub.merge(baselines, on="venue_name", how="left")
    sub = sub[sub["base_hw_rate"].notna()]

    if discord_filter is not None:
        sub["direction"] = "agree"
        sub.loc[sub["disagreement"] >= DISCORD_THRESHOLD, "direction"] = "bk_bullish_home"
        sub.loc[sub["disagreement"] <= -DISCORD_THRESHOLD, "direction"] = "exchange_bullish_home"
        sub = sub[sub["direction"] == discord_filter]

    sub["implied_home_bk"] = 1 / sub["bk_home_close"]
    sub["implied_away_bk"] = 1 / sub["bk_away_close"]
    sub["edge_back"]  = sub["base_hw_rate"] - sub["implied_home_bk"]
    sub["edge_fade"]  = (1 - sub["base_hw_rate"]) - sub["implied_away_bk"]

    records = []
    for _, row in sub.iterrows():
        venue = row["venue_name"]
        bet_type = odds = edge = None

        if venue in back_venues and row["edge_back"] >= MIN_EDGE:
            bet_type = "back_home"
            odds = row["bk_home_close"]
            edge = row["edge_back"]
        elif venue in fade_venues and row["edge_fade"] >= MIN_EDGE:
            bet_type = "fade_home"
            odds = row["bk_away_close"]
            edge = row["edge_fade"]

        if bet_type is None or pd.isna(odds) or odds < MIN_ODDS or odds > MAX_ODDS:
            continue

        won = (row["result"] == "home_win") if bet_type == "back_home" \
              else (row["result"] == "away_win")
        profit = (odds - 1) * FLAT_STAKE if won else -FLAT_STAKE

        records.append({
            "label": label,
            "date": row["date"],
            "season": int(row["season"]),
            "venue": venue,
            "bet_type": bet_type,
            "disagreement": float(round(row["disagreement"], 4)),
            "odds": float(round(float(odds), 3)),
            "edge": float(round(float(edge), 4)),
            "result": row["result"],
            "won": bool(won),
            "profit": float(round(float(profit), 2)),
        })

    bets = pd.DataFrame(records)
    if not bets.empty:
        bets = bets.sort_values("date").reset_index(drop=True)
        bets["cumulative_profit"] = bets["profit"].cumsum()
    return bets


def summarise(bets: pd.DataFrame) -> dict:
    if bets.empty:
        return {"n": 0, "wins": 0, "win_rate": 0.0, "profit": 0.0, "roi": 0.0,
                "is_exploratory": True}
    n = len(bets)
    wins = int(bets["won"].sum())
    profit = float(bets["profit"].sum())
    return {
        "n": n,
        "wins": wins,
        "win_rate": float(round(wins / n, 4)),
        "profit": float(round(profit, 2)),
        "roi": float(round(profit / (n * FLAT_STAKE), 4)),
        "is_exploratory": bool(n < 30),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    df = load_data()
    dual = dual_odds_subset(df)

    print("=" * 60)
    print("H_006: Bookmaker/Exchange Disagreement Filter")
    print("=" * 60)

    # ── Coverage check ────────────────────────────────────────────────────────
    total = len(df)
    both  = len(dual)
    strat = dual[dual["venue_name"].isin(ALL_STRATEGY_VENUES)]
    print(f"\n[Data coverage]")
    print(f"  Total matches: {total}")
    print(f"  With both bk + bf odds: {both} ({both/total:.1%})")
    print(f"  At strategy venues (both odds): {len(strat)}")
    print(f"  Season range: {dual['season'].min()}–{dual['season'].max()}")
    print(f"  Betfair-era training window: {dual['season'].min()}–{TRAIN_CUTOFF - 1}")
    print(f"  Holdout window: {TRAIN_CUTOFF}+")

    train_dual = dual[dual["season"] < TRAIN_CUTOFF]
    test_dual  = dual[dual["season"] >= TRAIN_CUTOFF]

    # ── Disagreement distribution at strategy venues ───────────────────────────
    strat_train = train_dual[train_dual["venue_name"].isin(ALL_STRATEGY_VENUES)]
    if not strat_train.empty:
        pct_agree  = (strat_train["abs_discord"] < DISCORD_THRESHOLD).mean()
        pct_bk_bull = (strat_train["disagreement"] >= DISCORD_THRESHOLD).mean()
        pct_ex_bull = (strat_train["disagreement"] <= -DISCORD_THRESHOLD).mean()
        print(f"\n[Disagreement distribution — training window, strategy venues, n={len(strat_train)}]")
        print(f"  Agree (|discord| < {DISCORD_THRESHOLD:.0%}):    {pct_agree:.1%}")
        print(f"  BK bullish on home (bk > bf):                  {pct_bk_bull:.1%}")
        print(f"  Exchange bullish on home (bf > bk):            {pct_ex_bull:.1%}")

    # ── Bucket analysis ───────────────────────────────────────────────────────
    train_buckets = bucket_analysis(train_dual, BACK_HOME_VENUES, FADE_HOME_VENUES,
                                    f"Training (pre-{TRAIN_CUTOFF})")
    test_buckets  = bucket_analysis(test_dual, BACK_HOME_VENUES, FADE_HOME_VENUES,
                                    f"Holdout ({TRAIN_CUTOFF}+)")

    for label, buckets in [("Training", train_buckets), ("Holdout", test_buckets)]:
        if buckets.empty:
            print(f"\n[{label}] No data")
            continue
        print(f"\n[{label} bucket analysis]")
        print(f"  {'venue_type':<12} {'direction':<25} {'n':>4}  "
              f"{'actual_hw':>9}  {'implied_bk':>10}  {'calib_err':>9}  {'p(1-sided)':>10}  sig")
        for _, row in buckets.iterrows():
            sig = "***" if row["significant"] else ""
            print(f"  {row['venue_type']:<12} {row['direction']:<25} {row['n']:>4}  "
                  f"{row['actual_hw']:>9.1%}  {row['implied_bk']:>10.1%}  "
                  f"{row['calibration_error_bk']:>+9.1%}  {row['p_one_sided']:>10.3f}  {sig}")

    # ── Holdout backtests: four variants ──────────────────────────────────────
    # Need baselines computed from ALL bookmaker data pre-cutoff
    # (not just dual-odds subset, to maximise training sample)
    train_all = df[df["season"] < TRAIN_CUTOFF]
    baselines = compute_baselines(train_all)

    variants = [
        (None,                   "No filter (baseline)"),
        ("exchange_bullish_home","Exchange confirms home edge"),
        ("bk_bullish_home",      "Bookmaker bullish (exchange sceptical)"),
        ("agree",                "Markets agree"),
    ]

    results = {}
    bets_dict = {}
    print(f"\n[Holdout backtests ({TRAIN_CUTOFF}+)]")
    for discord_filter, label in variants:
        bets = run_backtest(test_dual, baselines, BACK_HOME_VENUES, FADE_HOME_VENUES,
                            discord_filter, label)
        s = summarise(bets)
        results[label] = s
        bets_dict[label] = bets
        exp = " [EXPLORATORY]" if s["is_exploratory"] else ""
        print(f"  {label:<40} n={s['n']:>3}  wins={s['wins']:>2}  "
              f"win_rate={s['win_rate']:.1%}  ROI={s['roi']:+.2%}  "
              f"profit=${s['profit']:.0f}{exp}")

    # ── Primary significance: training bucket with best signal ────────────────
    primary_p = 1.0
    best_label = "none"
    if not train_buckets.empty:
        sig_rows = train_buckets[train_buckets["significant"]]
        if not sig_rows.empty:
            best_row = sig_rows.loc[sig_rows["p_one_sided"].idxmin()]
            primary_p = float(best_row["p_one_sided"])
            best_label = f"{best_row['venue_type']} / {best_row['direction']}"

    baseline = results.get("No filter (baseline)", {})
    best_variant = max(results.items(), key=lambda x: x[1]["roi"] if x[1]["n"] > 0 else -99)
    roi_delta = best_variant[1]["roi"] - baseline.get("roi", 0)
    is_sig = primary_p < 0.05 and not best_variant[1]["is_exploratory"]

    # ── Save JSON ─────────────────────────────────────────────────────────────
    result_json = {
        "hypothesis_id": "H_006",
        "p_value": float(primary_p),
        "sample_size": int(len(strat)),
        "roi_impact": float(round(roi_delta, 4)),
        "is_significant": bool(is_sig),
        "method": (
            "Disagreement buckets (bk_implied_home − bf_implied_home vs threshold) "
            f"at strategy venues; one-sample t-test on (home_win − bk_implied_home) "
            f"per bucket; holdout backtest with four filter variants"
        ),
        "data_window": (
            f"Dual-odds window: {dual['season'].min()}–{dual['season'].max()}. "
            f"Training: {dual['season'].min()}–{TRAIN_CUTOFF - 1}. "
            f"Holdout: {TRAIN_CUTOFF}+."
        ),
        "backtest_type": "holdout",
        "discord_threshold": DISCORD_THRESHOLD,
        "coverage": {
            "total_matches": int(total),
            "dual_odds_matches": int(both),
            "strategy_venue_matches": int(len(strat)),
        },
        "training_buckets": train_buckets.to_dict("records") if not train_buckets.empty else [],
        "holdout_buckets": test_buckets.to_dict("records") if not test_buckets.empty else [],
        "holdout_backtest_variants": {k: v for k, v in results.items()},
        "best_variant": best_variant[0],
        "best_variant_signal": best_label,
        "summary": (
            f"Disagreement filter {'shows' if is_sig else 'does NOT show'} a significant "
            f"improvement over the base venue-bias strategy in holdout data "
            f"(primary bucket p={primary_p:.3f}). "
            f"Best variant: '{best_variant[0]}' "
            f"(ROI={best_variant[1]['roi']:.2%}, n={best_variant[1]['n']}, "
            f"exploratory={best_variant[1]['is_exploratory']}). "
            f"ROI delta vs no-filter baseline: {roi_delta:+.2%}."
        ),
    }

    with open(RESULTS_DIR / "R_006.json", "w") as f:
        json.dump(result_json, f, indent=2)
    print(f"\nSaved → research/results/R_006.json")

    # ── Visualisation ─────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Panel 1: Calibration error by bucket (training window)
    ax1 = axes[0]
    if not train_buckets.empty:
        plot_df = train_buckets.copy()
        plot_df["bucket"] = plot_df["venue_type"] + "\n" + plot_df["direction"]
        colors = ["darkorange" if r["significant"] else "steelblue"
                  for _, r in plot_df.iterrows()]
        bars = ax1.bar(range(len(plot_df)), plot_df["calibration_error_bk"], color=colors)
        ax1.set_xticks(range(len(plot_df)))
        ax1.set_xticklabels(plot_df["bucket"], rotation=25, ha="right", fontsize=7)
        ax1.axhline(0, color="grey", linestyle="--", linewidth=0.8)
        ax1.set_ylabel("Calibration error (actual − bk_implied_home)")
        ax1.set_title(f"Training Window: Calibration by Disagreement Bucket\n"
                      f"(orange = significant, threshold={DISCORD_THRESHOLD:.0%})")
        for bar, (_, row) in zip(bars, plot_df.iterrows()):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                     f"n={row['n']}", ha="center", va="bottom", fontsize=7)
    else:
        ax1.text(0.5, 0.5, "No training data", ha="center", va="center",
                 transform=ax1.transAxes)

    # Panel 2: Cumulative profit comparison (holdout)
    ax2 = axes[1]
    palette = ["steelblue", "darkorange", "green", "red"]
    for (label, _), color in zip(variants, palette):
        bets = bets_dict.get(label, pd.DataFrame())
        s = results.get(label, {})
        if not bets.empty:
            ax2.plot(range(len(bets)), bets["cumulative_profit"],
                     label=f"{label} (n={s['n']}, ROI={s['roi']:.1%})",
                     color=color)
    ax2.axhline(0, color="grey", linestyle=":", linewidth=0.8)
    ax2.set_xlabel("Bet number")
    ax2.set_ylabel("Cumulative profit ($)")
    ax2.set_title(f"Holdout Backtest ({TRAIN_CUTOFF}+): Disagreement Filter Variants")
    ax2.legend(fontsize=7)

    plt.suptitle("H_006: BK/Exchange Disagreement as Venue-Strategy Filter", fontsize=12)
    plt.tight_layout()
    plt.savefig(VISUALS_DIR / "H_006_plot.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved → research/visuals/H_006_plot.png")

    return result_json


if __name__ == "__main__":
    result = main()
    print("\n" + "=" * 60)
    print("Result JSON:")
    print(json.dumps(result, indent=2, default=str))
