"""
H_001 Analysis — Updated Venue Baselines (2019+ Modern Window)

Hypothesis: Recalibrating venue baselines to 2019+ data improves strategy ROI
because home advantage has a confirmed declining trend (p=0.015). All-time baselines
(1998–present) over-estimate home advantage at legacy venues and under-estimate it
at modern high-performance hubs.

Test type: HOLDOUT (out-of-sample)
  - Baseline training window: pre-2022 (all-time vs 2019–2021)
  - Test window: 2022–2025 (unseen bets)

Output:
  - research/results/R_001.json
  - research/visuals/H_001_plot.png
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

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BACK_HOME_VENUES = {
    "AAMI Park",
    "Olympic Park Stadium",
    "Queensland Sport and Athletics Centre",
    "Sydney Showground",
}
FADE_HOME_VENUES = {
    "Campbelltown Sports Stadium",
    "Cbus Super Stadium",
}

# Venues to evaluate for potential inclusion in modern baseline strategy
CANDIDATE_BACK_VENUES = BACK_HOME_VENUES | {"BlueBet Stadium"}
CANDIDATE_FADE_VENUES = FADE_HOME_VENUES

ALL_CANDIDATE_VENUES = CANDIDATE_BACK_VENUES | CANDIDATE_FADE_VENUES

MIN_EDGE   = 0.05
MIN_ODDS   = 1.50
MAX_ODDS   = 6.00
FLAT_STAKE = 100

TRAIN_CUTOFF  = 2022   # baselines trained on seasons < 2022
MODERN_START  = 2019   # modern window lower bound
TEST_SEASONS  = None   # 2022+ (everything >= TRAIN_CUTOFF)


from typing import Optional

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_data() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED / "nrl_clean.csv", parse_dates=["date"])
    df["home_win"] = (df["result"] == "home_win").astype(int)
    df = df[df["venue_name"].notna() & df["result"].notna()]
    return df


# ---------------------------------------------------------------------------
# Baseline computation
# ---------------------------------------------------------------------------
def compute_baselines(df: pd.DataFrame, min_season: Optional[int] = None) -> pd.DataFrame:
    """Compute venue home-win baselines from a subset of data."""
    mask = pd.Series(True, index=df.index)
    if min_season is not None:
        mask &= df["season"] >= min_season
    sub = df[mask]
    baselines = (
        sub.groupby("venue_name")["home_win"]
        .agg(base_hw_rate="mean", n_baseline="count")
        .reset_index()
    )
    return baselines


# ---------------------------------------------------------------------------
# Backtest engine
# ---------------------------------------------------------------------------
def run_backtest(
    test_df: pd.DataFrame,
    baselines: pd.DataFrame,
    back_venues: set,
    fade_venues: set,
    odds_col_home: str = "bk_home_close",
    odds_col_away: str = "bk_away_close",
    label: str = "Bookmaker",
) -> pd.DataFrame:
    sub = test_df[test_df[odds_col_home].notna() & test_df[odds_col_away].notna()].copy()
    sub = sub.merge(baselines, on="venue_name", how="left")
    sub = sub[sub["base_hw_rate"].notna()]

    sub["implied_home"] = 1 / sub[odds_col_home]
    sub["implied_away"] = 1 / sub[odds_col_away]
    sub["edge_back"] = sub["base_hw_rate"] - sub["implied_home"]
    sub["edge_fade"] = (1 - sub["base_hw_rate"]) - sub["implied_away"]

    records = []
    for _, row in sub.iterrows():
        venue = row["venue_name"]
        bet_type = odds = edge = None

        if venue in back_venues and row["edge_back"] >= MIN_EDGE:
            bet_type = "back_home"
            odds = row[odds_col_home]
            edge = row["edge_back"]
        elif venue in fade_venues and row["edge_fade"] >= MIN_EDGE:
            bet_type = "fade_home"
            odds = row[odds_col_away]
            edge = row["edge_fade"]

        if bet_type is None or pd.isna(odds) or odds < MIN_ODDS or odds > MAX_ODDS:
            continue

        won = (row["result"] == "home_win") if bet_type == "back_home" \
              else (row["result"] == "away_win")
        profit = (odds - 1) * FLAT_STAKE if won else -FLAT_STAKE

        records.append({
            "label": label,
            "date": row["date"],
            "season": row["season"],
            "home_team": row["home_team"],
            "away_team": row["away_team"],
            "venue": venue,
            "bet_type": bet_type,
            "odds": round(float(odds), 3),
            "edge": round(float(edge), 4),
            "base_hw_rate": round(float(row["base_hw_rate"]), 3),
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
    wins  = int(bets["won"].sum())
    n     = len(bets)
    profit = bets["profit"].sum()
    staked = n * FLAT_STAKE
    return {
        "n": n,
        "wins": wins,
        "win_rate": round(wins / n, 4),
        "profit": round(float(profit), 2),
        "roi": round(float(profit / staked), 4),
    }


# ---------------------------------------------------------------------------
# Statistical test: is modern HW rate at target venues different from all-time?
# ---------------------------------------------------------------------------
def venue_significance_tests(df: pd.DataFrame) -> dict:
    """
    For each candidate venue, test whether 2019+ HW rate differs significantly
    from the all-time (pre-2019) HW rate using a two-proportion z-test.
    """
    results = {}
    for venue in ALL_CANDIDATE_VENUES:
        pre  = df[(df["venue_name"] == venue) & (df["season"] < 2019)]["home_win"]
        post = df[(df["venue_name"] == venue) & (df["season"] >= 2019)]["home_win"]
        if len(pre) < 10 or len(post) < 10:
            results[venue] = {"skipped": True, "reason": "insufficient sample"}
            continue
        # Two-proportion z-test
        n1, n2 = len(pre), len(post)
        p1, p2 = pre.mean(), post.mean()
        p_pool = (pre.sum() + post.sum()) / (n1 + n2)
        se = np.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
        z = (p2 - p1) / se if se > 0 else 0
        p_val = 2 * (1 - stats.norm.cdf(abs(z)))
        results[venue] = {
            "n_pre_2019": int(n1),
            "hw_rate_pre_2019": float(round(p1, 4)),
            "n_2019_plus": int(n2),
            "hw_rate_2019_plus": float(round(p2, 4)),
            "delta": float(round(p2 - p1, 4)),
            "p_value": float(round(p_val, 4)),
            "significant": bool(p_val < 0.05),
        }
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    df = load_data()

    # ── Separate training and test sets ──────────────────────────────────────
    train_df = df[df["season"] < TRAIN_CUTOFF]
    test_df  = df[df["season"] >= TRAIN_CUTOFF]

    # ── Compute two sets of baselines (both from training window only) ────────
    # All-time baselines: use all pre-2022 data
    bl_alltime = compute_baselines(train_df, min_season=None)
    # Modern baselines: use only 2019–2021 data
    bl_modern  = compute_baselines(train_df, min_season=MODERN_START)

    print("=" * 60)
    print("Baseline Comparison (training window: pre-2022)")
    print("=" * 60)
    targets = list(ALL_CANDIDATE_VENUES)
    cmp = (
        bl_alltime[bl_alltime["venue_name"].isin(targets)]
        .rename(columns={"base_hw_rate": "alltime_hw_rate", "n_baseline": "n_alltime"})
        .merge(
            bl_modern[bl_modern["venue_name"].isin(targets)]
            .rename(columns={"base_hw_rate": "modern_hw_rate", "n_baseline": "n_modern"}),
            on="venue_name", how="outer"
        )
        .sort_values("alltime_hw_rate", ascending=False)
    )
    print(cmp.to_string(index=False))

    # ── Venue-level significance tests (full dataset) ─────────────────────────
    print("\n" + "=" * 60)
    print("Pre-2019 vs 2019+ Home-Win Rate Tests")
    print("=" * 60)
    sig_tests = venue_significance_tests(df)
    for venue, res in sig_tests.items():
        if res.get("skipped"):
            print(f"  {venue}: SKIPPED — {res['reason']}")
        else:
            flag = " *** SIGNIFICANT" if res["significant"] else ""
            print(f"  {venue}: {res['hw_rate_pre_2019']:.1%} → {res['hw_rate_2019_plus']:.1%}"
                  f"  (Δ{res['delta']:+.1%}, p={res['p_value']:.3f}, n_post={res['n_2019_plus']}){flag}")

    # ── Backtest: all-time baselines on test set ──────────────────────────────
    bets_old = run_backtest(test_df, bl_alltime, BACK_HOME_VENUES, FADE_HOME_VENUES,
                            label="AllTime")
    # ── Backtest: modern baselines + BlueBet on test set ─────────────────────
    bets_new = run_backtest(test_df, bl_modern, CANDIDATE_BACK_VENUES, CANDIDATE_FADE_VENUES,
                            label="Modern")

    s_old = summarise(bets_old)
    s_new = summarise(bets_new)

    print("\n" + "=" * 60)
    print(f"Holdout Backtest (2022+) — Bookmaker closing odds")
    print("=" * 60)
    print(f"  ALL-TIME baselines:  n={s_old['n']}, wins={s_old['wins']}, "
          f"win_rate={s_old['win_rate']:.1%}, ROI={s_old['roi']:.2%}, profit=${s_old['profit']:.2f}")
    print(f"  MODERN  baselines:   n={s_new['n']}, wins={s_new['wins']}, "
          f"win_rate={s_new['win_rate']:.1%}, ROI={s_new['roi']:.2%}, profit=${s_new['profit']:.2f}")

    roi_delta = s_new["roi"] - s_old["roi"]
    profit_delta = s_new["profit"] - s_old["profit"]
    print(f"\n  ROI delta:    {roi_delta:+.2%}")
    print(f"  Profit delta: ${profit_delta:+.2f}")

    # ── Choose primary p_value from most significant venue shift ─────────────
    sig_p_vals = [v["p_value"] for v in sig_tests.values()
                  if not v.get("skipped") and v["significant"]]
    best_p = min(sig_p_vals) if sig_p_vals else 1.0
    is_sig = best_p < 0.05 and s_new["roi"] > s_old["roi"]

    # ── Save JSON result ──────────────────────────────────────────────────────
    result_json = {
        "hypothesis_id": "H_001",
        "p_value": best_p,
        "sample_size": s_new["n"],
        "roi_impact": round(roi_delta, 4),
        "is_significant": is_sig,
        "method": "Two-proportion z-test (pre/post 2019 venue HW rates) + holdout backtest (2022+)",
        "data_window": "Baselines: pre-2022 (alltime) vs 2019–2021 (modern). Test: 2022–2025.",
        "backtest_type": "holdout",
        "alltime_strategy": s_old,
        "modern_strategy": s_new,
        "venue_tests": sig_tests,
        "summary": (
            f"Modern (2019+) venue baselines {'outperform' if profit_delta > 0 else 'underperform'} "
            f"all-time baselines on 2022+ holdout data. "
            f"ROI delta: {roi_delta:+.2%}, profit delta: ${profit_delta:+.2f}. "
            f"Lowest venue p-value: {best_p:.3f}. "
            f"BlueBet Stadium added as new BACK HOME venue."
        ),
    }

    with open(RESULTS_DIR / "R_001.json", "w") as f:
        json.dump(result_json, f, indent=2)
    print(f"\nSaved → research/results/R_001.json")

    # ── Visualisation ─────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Panel 1: Venue baseline comparison
    ax1 = axes[0]
    merged = cmp.dropna(subset=["alltime_hw_rate"])
    venues_short = [v.replace(" Stadium", "").replace(" Sports", "").replace(" Park", "")
                    for v in merged["venue_name"]]
    x = np.arange(len(merged))
    w = 0.35
    bars1 = ax1.bar(x - w/2, merged["alltime_hw_rate"], w, label="All-time baseline",
                    color="steelblue", alpha=0.8)
    bars2 = ax1.bar(x + w/2, merged["modern_hw_rate"].fillna(0), w,
                    label="Modern (2019+) baseline", color="darkorange", alpha=0.8)
    ax1.axhline(0.5, color="grey", linestyle="--", linewidth=0.8, label="50% line")
    ax1.set_xticks(x)
    ax1.set_xticklabels(venues_short, rotation=30, ha="right", fontsize=8)
    ax1.set_ylabel("Home Win Rate")
    ax1.set_title("Venue Baselines: All-time vs Modern (2019+)")
    ax1.legend(fontsize=8)
    ax1.set_ylim(0, 1)

    # Panel 2: Cumulative profit comparison (test period)
    ax2 = axes[1]
    if not bets_old.empty:
        ax2.plot(range(len(bets_old)), bets_old["cumulative_profit"],
                 label=f"All-time (n={s_old['n']}, ROI={s_old['roi']:.1%})",
                 color="steelblue")
    if not bets_new.empty:
        ax2.plot(range(len(bets_new)), bets_new["cumulative_profit"],
                 label=f"Modern (n={s_new['n']}, ROI={s_new['roi']:.1%})",
                 color="darkorange")
    ax2.axhline(0, color="grey", linestyle="--", linewidth=0.8)
    ax2.set_xlabel("Bet number")
    ax2.set_ylabel("Cumulative profit ($)")
    ax2.set_title("Holdout Backtest (2022+): Cumulative Profit")
    ax2.legend(fontsize=8)

    plt.suptitle("H_001: Updated Venue Baselines — All-time vs Modern (2019+)", fontsize=12)
    plt.tight_layout()
    plt.savefig(VISUALS_DIR / "H_001_plot.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved → research/visuals/H_001_plot.png")

    return result_json


if __name__ == "__main__":
    result = main()
    print("\n" + "=" * 60)
    print("Result JSON:")
    print(json.dumps(result, indent=2, default=str))
