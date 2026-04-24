"""
H_009 Analysis — Asymmetric Market Calibration

Hypothesis: Favorites and longshots are miscalibrated differently across the odds curve.

Test type: HOLDOUT (out-of-sample)
  - Training window: pre-2022
  - Test window: 2022-2025

Output:
  - research/results/R_009.json
  - research/visuals/H_009_plot.png
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

def load_data() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED / "nrl_clean.csv", parse_dates=["date"])
    df["home_win"] = (df["result"] == "home_win").astype(int)
    # Filter for rows with bookmaker implied probabilities
    df = df[df["bk_home_close"].notna()].copy()
    
    # Define odds buckets based on bk_home_close
    # 1.0 - 1.4: Heavy Favorite
    # 1.4 - 1.9: Favorite
    # 1.9 - 2.5: Near Coin-flip
    # 2.5 - 4.0: Underdog
    # 4.0+: Heavy Underdog
    bins = [1.0, 1.4, 1.9, 2.5, 4.0, 100.0]
    labels = ["heavy_fav", "fav", "near_flip", "underdog", "heavy_underdog"]
    df["odds_bucket"] = pd.cut(df["bk_home_close"], bins=bins, labels=labels)
    
    return df

def analyze_buckets(df: pd.DataFrame) -> dict:
    buckets = df.groupby("odds_bucket").agg(
        n=("home_win", "count"),
        actual_hw=("home_win", "mean"),
        implied_hw=("bk_implied_home", "mean")
    ).reset_index()
    
    buckets["calibration_error"] = buckets["actual_hw"] - buckets["implied_hw"]
    
    results = []
    for _, row in buckets.iterrows():
        b_name = row["odds_bucket"]
        sub = df[df["odds_bucket"] == b_name]
        if sub.empty: continue
        residuals = sub["home_win"] - sub["bk_implied_home"]
        t_stat, p_val = stats.ttest_1samp(residuals, popmean=0)
        
        results.append({
            "bucket": str(b_name),
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
    print("H_009: Asymmetric Market Calibration Analysis")
    print("=" * 60)
    
    train_results = analyze_buckets(train_df)
    test_results = analyze_buckets(test_df)
    
    print("\n[Training Results]")
    for r in train_results:
        sig = "***" if r["significant"] else ""
        print(f"  {r['bucket']:<15} n={r['n']:>4}  actual={r['actual_hw']:.1%}  implied={r['implied_hw']:.1%}  err={r['calibration_error']:+.1%}  p={r['p_value']:.3f} {sig}")

    print("\n[Holdout Results]")
    for r in test_results:
        sig = "***" if r["significant"] else ""
        print(f"  {r['bucket']:<15} n={r['n']:>4}  actual={r['actual_hw']:.1%}  implied={r['implied_hw']:.1%}  err={r['calibration_error']:+.1%}  p={r['p_value']:.3f} {sig}")

    # Primary significance: strongest signal in training
    primary_p = min([r["p_value"] for r in train_results])
    is_sig = any([r["significant"] for r in train_results])
    
    result_json = {
        "hypothesis_id": "H_009",
        "p_value": float(primary_p),
        "sample_size": int(len(test_df)),
        "roi_impact": 0.0, # Exploratory, no specific strategy filter yet
        "is_significant": bool(is_sig),
        "method": "Odds-based bucketing + calibration t-test",
        "data_window": f"Train: pre-{TRAIN_CUTOFF}, Test: {TRAIN_CUTOFF}-2025",
        "backtest_type": "holdout",
        "training_results": train_results,
        "test_results": test_results,
        "summary": (
            f"Market calibration {'shows' if is_sig else 'does NOT show'} significant asymmetry. "
            f"Primary training p-value: {primary_p:.3f}."
        )
    }

    with open(RESULTS_DIR / "R_009.json", "w") as f:
        json.dump(result_json, f, indent=2)
    
    # Visualization
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Calibration Error by Bucket (Training)
    names_tr = [r["bucket"] for r in train_results]
    errs_tr = [r["calibration_error"] for r in train_results]
    ax1.bar(names_tr, errs_tr, color='skyblue', alpha=0.8)
    ax1.axhline(0, color='black', linewidth=0.8)
    ax1.set_title("Calibration Error by Odds Bucket (Training)")
    ax1.set_ylabel("Actual HW - Implied HW")
    ax1.tick_params(axis='x', rotation=45)

    # Calibration Error by Bucket (Holdout)
    names_te = [r["bucket"] for r in test_results]
    errs_te = [r["calibration_error"] for r in test_results]
    ax2.bar(names_te, errs_te, color='salmon', alpha=0.8)
    ax2.axhline(0, color='black', linewidth=0.8)
    ax2.set_title("Calibration Error by Odds Bucket (Holdout)")
    ax2.set_ylabel("Actual HW - Implied HW")
    ax2.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.savefig(VISUALS_DIR / "H_009_plot.png")
    
    print(f"\nSaved → research/results/R_009.json")
    print(f"Saved → research/visuals/H_009_plot.png")

if __name__ == "__main__":
    main()
