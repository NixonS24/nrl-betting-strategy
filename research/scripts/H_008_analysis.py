"""
H_008 Analysis — Bookmaker Margin Intensity (Overround)

Hypothesis: Matches with higher bookmaker margins (overround) may be less efficient
or provide different ROI characteristics for the venue-bias strategy.

Test type: HOLDOUT (out-of-sample)
  - Training window: pre-2022
  - Test window: 2022-2025

Output:
  - research/results/R_008.json
  - research/visuals/H_008_plot.png
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

TRAIN_CUTOFF = 2022
FLAT_STAKE = 100

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
    # Filter for rows with bookmaker implied probabilities
    df = df[df["bk_implied_home"].notna() & df["bk_implied_away"].notna()].copy()
    
    df["overround"] = df["bk_implied_home"] + df["bk_implied_away"]
    
    # Use quantiles from full dataset to define buckets
    df["overround_bucket"] = pd.qcut(df["overround"], 3, labels=["low", "med", "high"])
    
    return df

def analyze_buckets(df: pd.DataFrame) -> dict:
    buckets = df.groupby("overround_bucket").agg(
        n=("home_win", "count"),
        actual_hw=("home_win", "mean"),
        implied_hw=("bk_implied_home", "mean"),
        avg_overround=("overround", "mean")
    ).reset_index()
    
    buckets["calibration_error"] = buckets["actual_hw"] - buckets["implied_hw"]
    
    results = []
    for _, row in buckets.iterrows():
        b_name = row["overround_bucket"]
        sub = df[df["overround_bucket"] == b_name]
        residuals = sub["home_win"] - sub["bk_implied_home"]
        t_stat, p_val = stats.ttest_1samp(residuals, popmean=0)
        
        results.append({
            "bucket": str(b_name),
            "n": int(row["n"]),
            "avg_overround": float(round(row["avg_overround"], 4)),
            "actual_hw": float(round(row["actual_hw"], 4)),
            "implied_hw": float(round(row["implied_hw"], 4)),
            "calibration_error": float(round(row["calibration_error"], 4)),
            "p_value": float(round(p_val, 4)),
            "significant": bool(p_val < 0.05)
        })
    return results

def run_backtest(sub_df):
    sub_df = sub_df[sub_df["venue_name"].isin(STRATEGY_VENUES)].copy()
    if sub_df.empty: return []
    
    sub_df["profit"] = np.where(sub_df["home_win"] == 1, (sub_df["bk_home_close"] - 1) * FLAT_STAKE, -FLAT_STAKE)
    
    results = []
    for b_name in ["low", "med", "high"]:
        b_df = sub_df[sub_df["overround_bucket"] == b_name]
        if b_df.empty:
            roi = 0
            n = 0
        else:
            n = len(b_df)
            roi = b_df["profit"].sum() / (n * FLAT_STAKE)
        
        results.append({
            "bucket": b_name,
            "n": int(n),
            "roi": float(round(roi, 4))
        })
    return results

def main():
    df = load_data()
    train_df = df[df["season"] < TRAIN_CUTOFF]
    test_df = df[df["season"] >= TRAIN_CUTOFF]
    
    print("=" * 60)
    print("H_008: Bookmaker Margin Intensity Analysis")
    print("=" * 60)
    
    train_results = analyze_buckets(train_df)
    test_results = analyze_buckets(test_df)
    
    print("\n[Training Results]")
    for r in train_results:
        sig = "***" if r["significant"] else ""
        print(f"  {r['bucket']:<10} n={r['n']:>4}  avg_over={r['avg_overround']:.3f}  actual={r['actual_hw']:.1%}  err={r['calibration_error']:+.1%}  p={r['p_value']:.3f} {sig}")

    print("\n[Holdout Results]")
    for r in test_results:
        sig = "***" if r["significant"] else ""
        print(f"  {r['bucket']:<10} n={r['n']:>4}  avg_over={r['avg_overround']:.3f}  actual={r['actual_hw']:.1%}  err={r['calibration_error']:+.1%}  p={r['p_value']:.3f} {sig}")

    train_bt = run_backtest(train_df)
    test_bt = run_backtest(test_df)
    
    print("\n[Backtest ROI by Overround (Holdout)]")
    for r in test_bt:
        print(f"  {r['bucket']:<10} n={r['n']:>3}  ROI={r['roi']:.2%}")

    # Significance check: did high overround perform differently?
    # We look for p < 0.05 in any calibration bucket or large ROI difference.
    primary_p = min([r["p_value"] for r in train_results])
    is_sig = any([r["significant"] for r in train_results])
    
    # Calculate ROI delta for low vs high overround in holdout
    low_roi = next(r["roi"] for r in test_bt if r["bucket"] == "low")
    high_roi = next(r["roi"] for r in test_bt if r["bucket"] == "high")
    roi_delta = low_roi - high_roi

    result_json = {
        "hypothesis_id": "H_008",
        "p_value": float(primary_p),
        "sample_size": int(len(test_df)),
        "roi_impact": float(round(roi_delta, 4)),
        "is_significant": bool(is_sig),
        "method": "Overround tertile bucketing + calibration t-test + backtest segmenting",
        "data_window": f"Train: pre-{TRAIN_CUTOFF}, Test: {TRAIN_CUTOFF}-2025",
        "backtest_type": "holdout",
        "training_results": train_results,
        "test_results": test_results,
        "backtest_results": test_bt,
        "summary": (
            f"Margin intensity {'shows' if is_sig else 'does NOT show'} significant calibration differences. "
            f"Low overround ROI: {low_roi:.2%} vs High overround ROI: {high_roi:.2%}. "
            f"Primary training p-value: {primary_p:.3f}."
        )
    }

    with open(RESULTS_DIR / "R_008.json", "w") as f:
        json.dump(result_json, f, indent=2)
    
    # Visualization
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Calibration Error by Bucket
    names = [r["bucket"] for r in train_results]
    errs = [r["calibration_error"] for r in train_results]
    ax1.bar(names, errs, color='skyblue', alpha=0.8)
    ax1.axhline(0, color='black', linewidth=0.8)
    ax1.set_title("Calibration Error by Overround (Training)")
    ax1.set_ylabel("Actual HW - Implied HW")
    
    # ROI by Bucket (Holdout)
    ax2.bar([r["bucket"] for r in test_bt], [r["roi"] for r in test_bt], color='salmon', alpha=0.8)
    ax2.axhline(0, color='black', linewidth=0.8)
    ax2.set_title("Holdout ROI by Overround Bucket")
    ax2.set_ylabel("ROI")
    
    plt.tight_layout()
    plt.savefig(VISUALS_DIR / "H_008_plot.png")
    
    print(f"\nSaved → research/results/R_008.json")
    print(f"Saved → research/visuals/H_008_plot.png")

if __name__ == "__main__":
    main()
