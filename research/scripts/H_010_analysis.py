"""
H_010 Analysis — Near-Flip Calibration Edge (Prospective Design)

Hypothesis: Matches where the bookmaker prices the home side close to a coin-flip
(near-flip bucket) show systematic home underpricing not captured in the broader
calibration curve (H_009). This is a prospective-style follow-up to the rejected
45–55% bucket test.

Critical design note:
  H_009 revealed a concerning REVERSAL between training and holdout:
    - Training (pre-2022): near-flip homes OVER-priced by market (actual 41.8% vs implied 45.7%)
    - Holdout (2022+):     near-flip homes UNDER-priced by market (actual 55.3% vs implied 45.6%)
  This script explicitly tests for this structural shift and breaks the data into
  sub-periods to detect whether any stable signal exists.

Near-flip definition: bk_implied_home in [0.40, 0.60] (home priced within 10pp of 50/50).

Test type: HOLDOUT (out-of-sample) + sub-period stability check
  - Training window: pre-2022
  - Holdout window: 2022+
  - Stability check: pre-2019, 2019–2021, 2022+

Output:
  - research/results/R_010.json
  - research/visuals/H_010_plot.png
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

# Near-flip bucket boundaries
FLIP_LOW  = 0.40
FLIP_HIGH = 0.60
TRAIN_CUTOFF = 2022
FLAT_STAKE   = 100
MIN_ODDS     = 1.50
MAX_ODDS     = 6.00


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_data() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED / "nrl_clean.csv", parse_dates=["date"])
    df["home_win"] = (df["result"] == "home_win").astype(int)
    df = df[df["venue_name"].notna() & df["result"].notna() & df["bk_implied_home"].notna()]
    df["near_flip"] = df["bk_implied_home"].between(FLIP_LOW, FLIP_HIGH)
    return df


# ---------------------------------------------------------------------------
# Core signal test per window
# ---------------------------------------------------------------------------
def test_near_flip_signal(df: pd.DataFrame, label: str) -> dict:
    sub = df[df["near_flip"]].copy()
    if sub.empty or len(sub) < 10:
        return {"label": label, "n": 0, "error": "insufficient data"}

    n = len(sub)
    actual_hw  = float(sub["home_win"].mean())
    implied_hw = float(sub["bk_implied_home"].mean())
    residuals  = sub["home_win"] - sub["bk_implied_home"]
    t_stat, p_two = stats.ttest_1samp(residuals, popmean=0)
    # One-sided: test for under-pricing of home (actual > implied)
    p_one_over  = float(p_two / 2 if t_stat > 0 else 1.0 - p_two / 2)
    # One-sided: test for over-pricing of home (actual < implied)
    p_one_under = float(p_two / 2 if t_stat < 0 else 1.0 - p_two / 2)

    # Venue composition of near-flip matches
    venue_comp = (
        sub.groupby("venue_name")
        .agg(n_matches=("home_win", "count"), hw_rate=("home_win", "mean"))
        .sort_values("n_matches", ascending=False)
        .head(10)
        .reset_index()
        .to_dict("records")
    )

    return {
        "label": label,
        "n": int(n),
        "actual_hw_rate": round(actual_hw, 4),
        "mean_implied_hw": round(implied_hw, 4),
        "calibration_error": round(actual_hw - implied_hw, 4),
        "t_stat": round(float(t_stat), 4),
        "p_value_two_sided": round(float(p_two), 4),
        "p_one_sided_underpriced": round(p_one_over, 4),
        "p_one_sided_overpriced": round(p_one_under, 4),
        "direction": "underpriced" if actual_hw > implied_hw else "overpriced",
        "significant_underpriced": bool(p_one_over < 0.05),
        "significant_overpriced": bool(p_one_under < 0.05),
        "top_venues": venue_comp,
    }


# ---------------------------------------------------------------------------
# Sub-period stability check
# ---------------------------------------------------------------------------
def stability_check(df: pd.DataFrame) -> list:
    periods = [
        ("pre-2019", df[df["season"] < 2019]),
        ("2019–2021", df[(df["season"] >= 2019) & (df["season"] < 2022)]),
        ("2022+", df[df["season"] >= 2022]),
    ]
    results = []
    for label, sub in periods:
        res = test_near_flip_signal(sub, label)
        results.append(res)
    return results


# ---------------------------------------------------------------------------
# Backtest: back home in near-flip matches (holdout only)
# ---------------------------------------------------------------------------
def run_backtest(test_df: pd.DataFrame, training_base_rate: float) -> pd.DataFrame:
    """
    Back home in near-flip matches where bookmaker implied < training base rate.
    No venue restriction — pure calibration play.
    """
    sub = test_df[test_df["near_flip"] & test_df["bk_home_close"].notna()].copy()
    sub["implied_home"] = 1 / sub["bk_home_close"]
    sub["edge"] = training_base_rate - sub["implied_home"]

    records = []
    for _, row in sub.iterrows():
        if row["edge"] < 0.03:   # low bar — testing whether ANY edge exists
            continue
        odds = row["bk_home_close"]
        if odds < MIN_ODDS or odds > MAX_ODDS:
            continue
        won = row["result"] == "home_win"
        profit = (odds - 1) * FLAT_STAKE if won else -FLAT_STAKE
        records.append({
            "date": row["date"],
            "season": int(row["season"]),
            "home_team": row["home_team"],
            "away_team": row["away_team"],
            "venue": row["venue_name"],
            "odds": round(float(odds), 3),
            "edge": round(float(row["edge"]), 4),
            "implied_home": round(float(row["implied_home"]), 4),
            "bk_implied_home": round(float(row["bk_implied_home"]), 4),
            "result": row["result"],
            "won": bool(won),
            "profit": round(float(profit), 2),
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
        "win_rate": round(wins / n, 4),
        "profit": round(profit, 2),
        "roi": round(profit / (n * FLAT_STAKE), 4),
        "is_exploratory": bool(n < 30),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    df = load_data()
    train_df = df[df["season"] < TRAIN_CUTOFF]
    test_df  = df[df["season"] >= TRAIN_CUTOFF]

    total_near_flip = int(df["near_flip"].sum())
    print("=" * 60)
    print(f"H_010: Near-Flip Calibration Edge ({FLIP_LOW:.0%}–{FLIP_HIGH:.0%} implied home)")
    print("=" * 60)
    print(f"\n  Near-flip matches in full dataset: {total_near_flip} / {len(df)} ({total_near_flip/len(df):.1%})")
    print(f"  Near-flip in training (pre-{TRAIN_CUTOFF}): {int(train_df['near_flip'].sum())}")
    print(f"  Near-flip in holdout ({TRAIN_CUTOFF}+): {int(test_df['near_flip'].sum())}")

    # ── Training window signal ────────────────────────────────────────────────
    train_signal = test_near_flip_signal(train_df, f"Training (pre-{TRAIN_CUTOFF})")
    test_signal  = test_near_flip_signal(test_df,  f"Holdout ({TRAIN_CUTOFF}+)")

    print(f"\n[Training signal] n={train_signal['n']}, "
          f"actual={train_signal['actual_hw_rate']:.1%}, "
          f"implied={train_signal['mean_implied_hw']:.1%}, "
          f"error={train_signal['calibration_error']:+.1%}, "
          f"direction={train_signal['direction']}, "
          f"p(under)={train_signal['p_one_sided_underpriced']:.3f}")

    print(f"[Holdout signal]  n={test_signal['n']}, "
          f"actual={test_signal['actual_hw_rate']:.1%}, "
          f"implied={test_signal['mean_implied_hw']:.1%}, "
          f"error={test_signal['calibration_error']:+.1%}, "
          f"direction={test_signal['direction']}, "
          f"p(under)={test_signal['p_one_sided_underpriced']:.3f}")

    # ── Structural shift warning ──────────────────────────────────────────────
    direction_reversal = (train_signal["direction"] != test_signal.get("direction"))
    if direction_reversal:
        print(f"\n  *** DIRECTION REVERSAL DETECTED ***")
        print(f"  Training: {train_signal['direction']} | Holdout: {test_signal.get('direction')}")
        print(f"  This indicates no stable signal — result likely noise.")

    # ── Sub-period stability ──────────────────────────────────────────────────
    stability = stability_check(df)
    print(f"\n[Sub-period stability]")
    for s in stability:
        if s.get("n", 0) == 0:
            print(f"  {s['label']}: no data")
        else:
            print(f"  {s['label']:<15} n={s['n']:>3}  "
                  f"actual={s['actual_hw_rate']:.1%}  implied={s['mean_implied_hw']:.1%}  "
                  f"error={s['calibration_error']:+.1%}  dir={s['direction']}")

    # ── Holdout backtest ──────────────────────────────────────────────────────
    train_base = float(train_df[train_df["near_flip"]]["home_win"].mean()) \
                 if train_df["near_flip"].sum() > 0 else 0.5
    bets = run_backtest(test_df, train_base)
    s = summarise(bets)

    print(f"\n[Holdout backtest — back home in near-flip matches where edge ≥ 3%]")
    print(f"  Training base rate: {train_base:.1%}")
    print(f"  n={s['n']}, wins={s['wins']}, win_rate={s['win_rate']:.1%}, "
          f"ROI={s['roi']:.2%}, exploratory={s['is_exploratory']}")

    # ── Significance assessment ───────────────────────────────────────────────
    primary_p = float(test_signal.get("p_one_sided_underpriced", 1.0))
    is_sig = bool(primary_p < 0.05 and not direction_reversal)

    # ── Save JSON ─────────────────────────────────────────────────────────────
    result_json = {
        "hypothesis_id": "H_010",
        "p_value": primary_p,
        "sample_size": int(test_signal.get("n", 0)),
        "roi_impact": float(s["roi"]),
        "is_significant": is_sig,
        "method": (
            f"One-sample t-test on (home_win − bk_implied_home) residuals, "
            f"one-sided (actual > implied), near-flip bucket "
            f"bk_implied_home in [{FLIP_LOW}, {FLIP_HIGH}]"
        ),
        "data_window": f"Training: pre-{TRAIN_CUTOFF}. Holdout: {TRAIN_CUTOFF}–2025.",
        "backtest_type": "holdout",
        "flip_bucket": {"low": FLIP_LOW, "high": FLIP_HIGH},
        "direction_reversal_detected": bool(direction_reversal),
        "training_signal": train_signal,
        "holdout_signal": test_signal,
        "sub_period_stability": stability,
        "holdout_backtest": s,
        "summary": (
            f"Near-flip bucket ({FLIP_LOW:.0%}–{FLIP_HIGH:.0%} implied home) "
            f"{'shows' if is_sig else 'does NOT show'} a significant edge in holdout "
            f"(p={primary_p:.3f}, n={test_signal.get('n', 0)}). "
            f"Direction reversal between training and holdout: {direction_reversal}. "
            f"Holdout backtest ROI: {s['roi']:.2%} over {s['n']} bets "
            f"({'exploratory' if s['is_exploratory'] else 'sufficient sample'})."
        ),
    }

    with open(RESULTS_DIR / "R_010.json", "w") as f:
        json.dump(result_json, f, indent=2)
    print(f"\nSaved → research/results/R_010.json")

    # ── Visualisation ─────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Panel 1: Calibration error by sub-period
    ax1 = axes[0]
    sub_labels = [s["label"] for s in stability if s.get("n", 0) > 0]
    sub_errors = [s["calibration_error"] for s in stability if s.get("n", 0) > 0]
    sub_ns     = [s["n"] for s in stability if s.get("n", 0) > 0]
    colors = ["steelblue" if e > 0 else "tomato" for e in sub_errors]
    bars = ax1.bar(range(len(sub_labels)), sub_errors, color=colors, alpha=0.85)
    ax1.axhline(0, color="grey", linestyle="--", linewidth=0.8)
    ax1.set_xticks(range(len(sub_labels)))
    ax1.set_xticklabels(sub_labels, fontsize=9)
    ax1.set_ylabel("Calibration error (actual − implied HW)")
    ax1.set_title(f"Near-Flip Calibration Error by Era\n(blue = home underpriced, red = overpriced)")
    for bar, n in zip(bars, sub_ns):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                 f"n={n}", ha="center",
                 va="bottom" if bar.get_height() >= 0 else "top", fontsize=8)

    # Panel 2: Cumulative profit from holdout backtest
    ax2 = axes[1]
    if not bets.empty:
        ax2.plot(range(len(bets)), bets["cumulative_profit"], color="darkorange",
                 label=f"Near-flip back home (n={s['n']}, ROI={s['roi']:.1%})")
        ax2.axhline(0, color="grey", linestyle="--", linewidth=0.8)
        ax2.set_xlabel("Bet number")
        ax2.set_ylabel("Cumulative profit ($)")
        ax2.set_title(f"Holdout Backtest ({TRAIN_CUTOFF}+): Near-Flip Back Home")
        ax2.legend(fontsize=8)
    else:
        ax2.text(0.5, 0.5, "No qualifying bets in holdout period",
                 ha="center", va="center", transform=ax2.transAxes)
        ax2.set_title("Holdout Backtest: No Data")

    if direction_reversal:
        fig.text(0.5, 0.01,
                 "⚠ Direction reversal detected between training and holdout — result likely noise",
                 ha="center", color="red", fontsize=9)

    plt.suptitle("H_010: Near-Flip Calibration Edge (Prospective Design)", fontsize=12)
    plt.tight_layout(rect=[0, 0.04, 1, 1])
    plt.savefig(VISUALS_DIR / "H_010_plot.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved → research/visuals/H_010_plot.png")

    return result_json


if __name__ == "__main__":
    result = main()
    print("\n" + "=" * 60)
    print("Result JSON:")
    print(json.dumps(result, indent=2, default=str))
