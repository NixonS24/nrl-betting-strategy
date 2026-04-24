"""
H_007 Analysis — Bookmaker Closing Line Movement (CLM)

Hypothesis: Bookmaker price movement (shortening/drifting) between open and close
carries independent predictive signal.

Test type: HOLDOUT (out-of-sample)
  - Training window: pre-2022
  - Test window: 2022-2025

Output:
  - research/results/R_007.json
  - research/visuals/H_007_plot.png
"""

import json
import pandas as pd
import numpy as np
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

TRAIN_CUTOFF = 2022
FLAT_STAKE = 100

# Strategy venues from production/H_001 findings
STRATEGY_VENUES = {
    "AAMI Park",
    "Olympic Park Stadium",
    "Queensland Sport and Athletics Centre",
    "Sydney Showground",
    "BlueBet Stadium",
    "Campbelltown Sports Stadium"
}

def load_data() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED / "nrl_clean.csv", parse_dates=["date"])
    df["home_win"] = (df["result"] == "home_win").astype(int)
    # Filter for rows with both open and close odds
    df = df[df["bk_home_open"].notna() & df["bk_home_close"].notna()].copy()
    
    # Calculate movement
    # move < 0 means price shortened (implied prob increased)
    # move > 0 means price drifted (implied prob decreased)
    df["bk_home_move"] = df["bk_home_close"] - df["bk_home_open"]
    df["bk_home_pct_move"] = (df["bk_home_close"] / df["bk_home_open"]) - 1
    
    def bucket_move(pct):
        if pct < -0.05: return "shortened_strong"
        if pct < -0.01: return "shortened_mild"
        if pct > 0.05:  return "drifted_strong"
        if pct > 0.01:  return "drifted_mild"
        return "stable"
    
    df["move_bucket"] = df["bk_home_pct_move"].apply(bucket_move)
    return df

def analyze_buckets(df: pd.DataFrame, label: str) -> dict:
    buckets = df.groupby("move_bucket").agg(
        n=("home_win", "count"),
        actual_hw=("home_win", "mean"),
        implied_hw=("bk_implied_home", "mean")
    ).reset_index()
    
    buckets["calibration_error"] = buckets["actual_hw"] - buckets["implied_hw"]
    
    results = []
    for _, row in buckets.iterrows():
        bucket_name = row["move_bucket"]
        sub = df[df["move_bucket"] == bucket_name]
        residuals = sub["home_win"] - sub["bk_implied_home"]
        t_stat, p_val = stats.ttest_1samp(residuals, popmean=0)
        
        results.append({
            "bucket": bucket_name,
            "n": int(row["n"]),
            "actual_hw": float(round(row["actual_hw"], 4)),
            "implied_hw": float(round(row["implied_hw"], 4)),
            "calibration_error": float(round(row["calibration_error"], 4)),
            "p_value": float(round(p_val, 4)),
            "significant": bool(p_val < 0.05)
        })
    return results

def main():
    df = load_data()
    train_df = df[df["season"] < TRAIN_CUTOFF]
    test_df = df[df["season"] >= TRAIN_CUTOFF]
    
    print("=" * 60)
    print("H_007: Bookmaker Line Movement Analysis")
    print("=" * 60)
    
    train_results = analyze_buckets(train_df, "Training")
    test_results = analyze_buckets(test_df, "Holdout")
    
    print("\n[Training Results]")
    for r in train_results:
        sig = "***" if r["significant"] else ""
        print(f"  {r['bucket']:<20} n={r['n']:>4}  actual={r['actual_hw']:.1%}  implied={r['implied_hw']:.1%}  err={r['calibration_error']:+.1%}  p={r['p_value']:.3f} {sig}")

    print("\n[Holdout Results]")
    for r in test_results:
        sig = "***" if r["significant"] else ""
        print(f"  {r['bucket']:<20} n={r['n']:>4}  actual={r['actual_hw']:.1%}  implied={r['implied_hw']:.1%}  err={r['calibration_error']:+.1%}  p={r['p_value']:.3f} {sig}")

    # Backtest: filter strategy by movement
    # Hypo: Strong shortening increases edge, Strong drift negates edge
    def run_backtest(sub_df, label):
        # Baseline (no CLM filter)
        sub_df = sub_df[sub_df["venue_name"].isin(STRATEGY_VENUES)].copy()
        if sub_df.empty: return {"n": 0, "roi": 0}
        
        # Simple ROI calculation for back-home venues (placeholder logic similar to venue_bias)
        # In a real run, we'd use the actual baselines, but here we just check if CLM helps
        sub_df["profit"] = np.where(sub_df["home_win"] == 1, (sub_df["bk_home_close"] - 1) * FLAT_STAKE, -FLAT_STAKE)
        
        baseline_roi = sub_df["profit"].sum() / (len(sub_df) * FLAT_STAKE)
        
        # Filtered ROI (exclude strong drifts)
        filtered = sub_df[sub_df["move_bucket"] != "drifted_strong"]
        filtered_roi = filtered["profit"].sum() / (len(filtered) * FLAT_STAKE) if not filtered.empty else 0
        
        return {
            "n_baseline": len(sub_df),
            "baseline_roi": float(round(baseline_roi, 4)),
            "n_filtered": len(filtered),
            "filtered_roi": float(round(filtered_roi, 4)),
            "roi_delta": float(round(filtered_roi - baseline_roi, 4))
        }

    bt_results = run_backtest(test_df, "Holdout")
    print(f"\n[Backtest ROI Filter (Holdout)]")
    print(f"  Baseline ROI: {bt_results['baseline_roi']:.2%}")
    print(f"  Filtered ROI: {bt_results['filtered_roi']:.2%} (excluding strong drifts)")
    print(f"  ROI Delta:    {bt_results['roi_delta']:+.2%}")

    # Primary significance: strongest signal in training
    primary_p = min([r["p_value"] for r in train_results])
    is_sig = any([r["significant"] for r in train_results]) and bt_results["roi_delta"] > 0
    
    result_json = {
        "hypothesis_id": "H_007",
        "p_value": float(primary_p),
        "sample_size": int(len(test_df)),
        "roi_impact": float(bt_results["roi_delta"]),
        "is_significant": bool(is_sig),
        "method": "One-sample t-test on residuals by CLM bucket + holdout backtest filter",
        "data_window": f"Train: pre-{TRAIN_CUTOFF}, Test: {TRAIN_CUTOFF}-2025",
        "backtest_type": "holdout",
        "training_results": train_results,
        "test_results": test_results,
        "backtest": bt_results,
        "summary": (
            f"Line movement {'shows' if is_sig else 'does NOT show'} significant predictive power. "
            f"Excluding strong drifts improved holdout ROI by {bt_results['roi_delta']:+.2%}. "
            f"Strongest training p-value: {primary_p:.3f}."
        )
    }

    with open(RESULTS_DIR / "R_007.json", "w") as f:
        json.dump(result_json, f, indent=2)
    
    # Visualization
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Calibration Error by Bucket
    names = [r["bucket"] for r in train_results]
    errs = [r["calibration_error"] for r in train_results]
    colors = ['green' if e > 0 else 'red' for e in errs]
    ax1.bar(names, errs, color=colors, alpha=0.6)
    ax1.axhline(0, color='black', linewidth=0.8)
    ax1.set_title("Calibration Error by CLM Bucket (Training)")
    ax1.set_ylabel("Actual HW - Implied HW")
    ax1.tick_params(axis='x', rotation=45)
    
    # ROI Comparison
    ax2.bar(["Baseline", "Filtered"], [bt_results["baseline_roi"], bt_results["filtered_roi"]], color=['gray', 'blue'], alpha=0.6)
    ax2.set_title("Holdout ROI: Baseline vs CLM Filter")
    ax2.set_ylabel("ROI")
    
    plt.tight_layout()
    plt.savefig(VISUALS_DIR / "H_007_plot.png")
    
    print(f"\nSaved → research/results/R_007.json")
    print(f"Saved → research/visuals/H_007_plot.png")

if __name__ == "__main__":
    main()
