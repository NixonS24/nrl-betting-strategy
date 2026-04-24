"""
H_002 Analysis — Suncorp Stadium FADE HOME Venue

Hypothesis: Suncorp Stadium functions as a systematic fade-home venue. The bookmaker
prices the home side as if Suncorp carries standard home advantage, while actual home
win performance is weaker than implied by market prices.

Test type: HOLDOUT (out-of-sample)
  - Signal discovery window: pre-2022 (compute baseline, confirm signal)
  - Backtest window: 2022–2025 (unseen bets)
  - Exploratory flag: raised if test is inadvertently in-sample

Design note: Suncorp is a multi-team venue (Brisbane Broncos, Dolphins, QLD SOO).
  Analysis is broken down by home_team to detect whether the fade signal is
  venue-wide or team-specific.

Output:
  - research/results/R_002.json
  - research/visuals/H_002_plot.png
"""

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
RESULTS_DIR = ROOT / "research" / "results"
VISUALS_DIR = ROOT / "research" / "visuals"
RESULTS_DIR.mkdir(exist_ok=True)
VISUALS_DIR.mkdir(exist_ok=True)

VENUE = "Suncorp Stadium"
TRAIN_CUTOFF = 2022
MIN_EDGE   = 0.0    # no edge filter for base-rate test; applied for backtest
BET_EDGE   = 0.03   # minimum edge for backtest (lower than global to preserve n)
MIN_ODDS   = 1.50
MAX_ODDS   = 6.00
FLAT_STAKE = 100


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_data() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED / "nrl_clean.csv", parse_dates=["date"])
    df["home_win"] = (df["result"] == "home_win").astype(int)
    df = df[df["venue_name"].notna() & df["result"].notna()]
    return df


# ---------------------------------------------------------------------------
# Core signal test
# ---------------------------------------------------------------------------
def test_suncorp_signal(df: pd.DataFrame, window_label: str) -> dict:
    """
    Test whether actual home win rate at Suncorp is significantly below
    bookmaker-implied home probability.
    """
    sub = df[(df["venue_name"] == VENUE) & df["bk_implied_home"].notna()].copy()

    if sub.empty:
        return {"error": "no data", "window": window_label}

    n = len(sub)
    actual_hw_rate = sub["home_win"].mean()
    mean_implied   = sub["bk_implied_home"].mean()

    # One-sample t-test: is actual HW rate < mean implied probability?
    # Null: actual HW rate == mean_implied
    # This is a proportions test framed as one-sample t-test on (home_win - implied)
    residuals = sub["home_win"] - sub["bk_implied_home"]
    t_stat, p_val_two = stats.ttest_1samp(residuals, popmean=0)
    # One-sided: we expect actual < implied (negative residual)
    p_val_one = p_val_two / 2 if t_stat < 0 else 1.0 - p_val_two / 2

    calibration_error = actual_hw_rate - mean_implied   # negative = bookmaker over-prices home

    # Breakdown by home team
    by_team = (
        sub.groupby("home_team")
        .agg(
            n=("home_win", "count"),
            actual_hw=("home_win", "mean"),
            implied_hw=("bk_implied_home", "mean"),
        )
        .assign(delta=lambda x: x["actual_hw"] - x["implied_hw"])
        .sort_values("n", ascending=False)
        .reset_index()
    )

    return {
        "window": window_label,
        "n": int(n),
        "actual_hw_rate": float(round(actual_hw_rate, 4)),
        "mean_implied_hw": float(round(mean_implied, 4)),
        "calibration_error": float(round(calibration_error, 4)),
        "t_stat": float(round(float(t_stat), 4)),
        "p_value_one_sided": float(round(p_val_one, 4)),
        "p_value_two_sided": float(round(float(p_val_two), 4)),
        "significant_one_sided": bool(p_val_one < 0.05),
        "by_team": by_team.to_dict("records"),
    }


# ---------------------------------------------------------------------------
# Backtest: fade-home rule at Suncorp
# ---------------------------------------------------------------------------
def run_fade_backtest(test_df: pd.DataFrame, base_hw_rate: float, label: str) -> pd.DataFrame:
    """
    Fade the home team at Suncorp when bookmaker over-prices home side.
    Edge = (1 - base_hw_rate) - implied_away  [we want to back away team]
    """
    sub = test_df[
        (test_df["venue_name"] == VENUE)
        & test_df["bk_home_close"].notna()
        & test_df["bk_away_close"].notna()
    ].copy()

    if sub.empty:
        return pd.DataFrame()

    sub["implied_away"] = 1 / sub["bk_away_close"]
    sub["edge_fade"] = (1 - base_hw_rate) - sub["implied_away"]

    records = []
    for _, row in sub.iterrows():
        if row["edge_fade"] < BET_EDGE:
            continue
        odds = row["bk_away_close"]
        if pd.isna(odds) or odds < MIN_ODDS or odds > MAX_ODDS:
            continue
        won = row["result"] == "away_win"
        profit = (odds - 1) * FLAT_STAKE if won else -FLAT_STAKE
        records.append({
            "label": label,
            "date": row["date"],
            "season": row["season"],
            "home_team": row["home_team"],
            "away_team": row["away_team"],
            "odds": round(float(odds), 3),
            "edge": round(float(row["edge_fade"]), 4),
            "result": row["result"],
            "won": won,
            "profit": round(float(profit), 2),
        })

    bets = pd.DataFrame(records)
    if not bets.empty:
        bets = bets.sort_values("date").reset_index(drop=True)
        bets["cumulative_profit"] = bets["profit"].cumsum()
    return bets


def summarise(bets: pd.DataFrame) -> dict:
    if bets.empty:
        return {"n": 0, "wins": 0, "win_rate": 0, "profit": 0, "roi": 0}
    n = len(bets)
    wins = int(bets["won"].sum())
    profit = bets["profit"].sum()
    return {
        "n": n,
        "wins": wins,
        "win_rate": round(wins / n, 4),
        "profit": round(float(profit), 2),
        "roi": round(float(profit / (n * FLAT_STAKE)), 4),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    df = load_data()

    train_df = df[df["season"] < TRAIN_CUTOFF]
    test_df  = df[df["season"] >= TRAIN_CUTOFF]

    print("=" * 60)
    print(f"H_002: Suncorp Stadium FADE HOME Analysis")
    print("=" * 60)

    # ── Signal test on training window (discovery) ────────────────────────────
    train_signal = test_suncorp_signal(train_df, f"Training (pre-{TRAIN_CUTOFF})")
    print(f"\n[Training window: pre-{TRAIN_CUTOFF}]")
    print(f"  n={train_signal['n']}, actual HW={train_signal['actual_hw_rate']:.1%}, "
          f"implied={train_signal['mean_implied_hw']:.1%}, "
          f"error={train_signal['calibration_error']:+.1%}, "
          f"p(one-sided)={train_signal['p_value_one_sided']:.3f}")

    if train_signal["by_team"]:
        print("\n  Home team breakdown (training window):")
        for row in train_signal["by_team"]:
            print(f"    {row['home_team']:<30} n={row['n']:>3}  "
                  f"actual={row['actual_hw']:.1%}  implied={row['implied_hw']:.1%}  "
                  f"delta={row['delta']:+.1%}")

    # ── Signal test on holdout window (confirmation) ──────────────────────────
    test_signal = test_suncorp_signal(test_df, f"Holdout ({TRAIN_CUTOFF}+)")
    print(f"\n[Holdout window: {TRAIN_CUTOFF}+]")
    print(f"  n={test_signal['n']}, actual HW={test_signal['actual_hw_rate']:.1%}, "
          f"implied={test_signal['mean_implied_hw']:.1%}, "
          f"error={test_signal['calibration_error']:+.1%}, "
          f"p(one-sided)={test_signal['p_value_one_sided']:.3f}")

    if test_signal.get("by_team"):
        print("\n  Home team breakdown (holdout window):")
        for row in test_signal["by_team"]:
            print(f"    {row['home_team']:<30} n={row['n']:>3}  "
                  f"actual={row['actual_hw']:.1%}  implied={row['implied_hw']:.1%}  "
                  f"delta={row['delta']:+.1%}")

    # ── Backtest on holdout using training baseline ────────────────────────────
    train_base_hw = train_signal.get("actual_hw_rate", 0.5)
    bets = run_fade_backtest(test_df, train_base_hw, label="Holdout fade")
    s = summarise(bets)

    print(f"\n[Holdout Backtest: fade home at Suncorp (edge ≥ {BET_EDGE:.0%})]")
    print(f"  Training base HW rate used: {train_base_hw:.1%}")
    print(f"  n={s['n']}, wins={s['wins']}, win_rate={s['win_rate']:.1%}, "
          f"ROI={s['roi']:.2%}, profit=${s['profit']:.2f}")
    print(f"  Backtest type: HOLDOUT (out-of-sample)")

    # ── Primary significance: use holdout test p-value ────────────────────────
    primary_p = test_signal.get("p_value_one_sided", 1.0)
    is_sig = primary_p < 0.05

    # ── Save JSON result ──────────────────────────────────────────────────────
    result_json = {
        "hypothesis_id": "H_002",
        "p_value": primary_p,
        "sample_size": test_signal.get("n", 0),
        "roi_impact": s["roi"],
        "is_significant": is_sig,
        "method": "One-sample t-test on (home_win − bk_implied_home) residuals, one-sided (actual < implied)",
        "data_window": f"Signal: pre-{TRAIN_CUTOFF}. Backtest: {TRAIN_CUTOFF}–2025.",
        "backtest_type": "holdout",
        "training_signal": {
            "n": train_signal["n"],
            "actual_hw_rate": train_signal["actual_hw_rate"],
            "implied_hw": train_signal["mean_implied_hw"],
            "calibration_error": train_signal["calibration_error"],
            "p_one_sided": train_signal["p_value_one_sided"],
            "significant": train_signal["significant_one_sided"],
        },
        "holdout_signal": {
            "n": test_signal.get("n", 0),
            "actual_hw_rate": test_signal.get("actual_hw_rate"),
            "implied_hw": test_signal.get("mean_implied_hw"),
            "calibration_error": test_signal.get("calibration_error"),
            "p_one_sided": test_signal.get("p_value_one_sided"),
            "significant": test_signal.get("significant_one_sided"),
        },
        "holdout_backtest": s,
        "venue_team_breakdown": train_signal.get("by_team", []),
        "summary": (
            f"Suncorp Stadium {'shows' if is_sig else 'does NOT show'} a significant "
            f"fade-home signal in holdout data. "
            f"Holdout HW rate: {test_signal.get('actual_hw_rate', 0):.1%} vs "
            f"implied {test_signal.get('mean_implied_hw', 0):.1%} "
            f"(p={primary_p:.3f}, one-sided, n={test_signal.get('n', 0)}). "
            f"Holdout backtest ROI: {s['roi']:.2%} over {s['n']} bets."
        ),
    }

    with open(RESULTS_DIR / "R_002.json", "w") as f:
        json.dump(result_json, f, indent=2)
    print(f"\nSaved → research/results/R_002.json")

    # ── Visualisation ─────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Panel 1: Season-by-season HW rate at Suncorp vs implied
    ax1 = axes[0]
    suncorp = df[df["venue_name"] == VENUE].copy()
    by_season = (
        suncorp[suncorp["bk_implied_home"].notna()]
        .groupby("season")
        .agg(actual_hw=("home_win", "mean"), implied_hw=("bk_implied_home", "mean"), n=("home_win", "count"))
        .reset_index()
    )
    if not by_season.empty:
        ax1.plot(by_season["season"], by_season["actual_hw"], marker="o",
                 color="darkorange", label="Actual HW rate")
        ax1.plot(by_season["season"], by_season["implied_hw"], marker="s",
                 color="steelblue", linestyle="--", label="Bookmaker implied")
        ax1.axhline(0.5, color="grey", linestyle=":", linewidth=0.8)
        ax1.axvline(TRAIN_CUTOFF - 0.5, color="red", linestyle="--", linewidth=0.8,
                    label=f"Train/holdout split ({TRAIN_CUTOFF})")
        ax1.set_xlabel("Season")
        ax1.set_ylabel("Home Win Rate")
        ax1.set_title("Suncorp Stadium: Actual vs Implied HW Rate by Season")
        ax1.legend(fontsize=8)
        ax1.set_ylim(0, 1)

    # Panel 2: Cumulative profit from fade backtest
    ax2 = axes[1]
    if not bets.empty:
        ax2.plot(range(len(bets)), bets["cumulative_profit"], color="darkorange",
                 label=f"Fade Suncorp home (n={s['n']}, ROI={s['roi']:.1%})")
        ax2.axhline(0, color="grey", linestyle="--", linewidth=0.8)
        ax2.set_xlabel("Bet number")
        ax2.set_ylabel("Cumulative profit ($)")
        ax2.set_title(f"Holdout Backtest ({TRAIN_CUTOFF}+): Fade Home at Suncorp")
        ax2.legend(fontsize=8)
    else:
        ax2.text(0.5, 0.5, "No qualifying bets in holdout period",
                 ha="center", va="center", transform=ax2.transAxes)
        ax2.set_title("Holdout Backtest: No Data")

    plt.suptitle("H_002: Suncorp Stadium FADE HOME Signal", fontsize=12)
    plt.tight_layout()
    plt.savefig(VISUALS_DIR / "H_002_plot.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved → research/visuals/H_002_plot.png")

    return result_json


if __name__ == "__main__":
    result = main()
    print("\n" + "=" * 60)
    print("Result JSON:")
    print(json.dumps(result, indent=2, default=str))
