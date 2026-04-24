"""
H_003 Analysis — Referee Day-of-Week Effect & Individual Bias

Hypothesis: 
1. Home advantage varies by day of the week, possibly due to referee assignment patterns.
2. Individual referees produce significantly different home win rates.

Test type: EXPLORATORY (Small sample size n=~250)
  - Data window: 2021-2025 (Scraped sample)

Output:
  - research/results/R_003.json
  - research/visuals/H_003_plot.png
"""

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
RESULTS_DIR = ROOT / "research" / "results"
VISUALS_DIR = ROOT / "research" / "visuals"
RESULTS_DIR.mkdir(exist_ok=True)
VISUALS_DIR.mkdir(exist_ok=True)

REF_DATA_PATH = RAW / "referee_assignments.csv"

def load_data() -> pd.DataFrame:
    # Load main dataset
    df = pd.read_csv(PROCESSED / "nrl_clean.csv", parse_dates=["date"])
    df["home_win"] = (df["result"] == "home_win").astype(int)
    df["day_of_week"] = df["date"].dt.day_name()
    
    # Load referee data
    if not REF_DATA_PATH.exists():
        return pd.DataFrame()
    
    ref_df = pd.read_csv(REF_DATA_PATH)
    
    # Standardize round format: "Round 1" vs 1
    def norm_round(r):
        if isinstance(r, str):
            r = r.replace("Round ", "").replace("round-", "").strip()
            if r.isdigit():
                return int(r)
            return r # Return string for finals (e.g. 'Minor Prelim Semi')
        return r
    
    df["round_num"] = df["round"].apply(norm_round)
    ref_df["round_num"] = ref_df["round"].apply(norm_round)
    
    # Join keys: season, round_num, home_nickname match
    # We'll do a slightly fuzzy join on team names
    # Map full names to nicknames
    team_map = {
        "Brisbane Broncos": "Broncos",
        "Canberra Raiders": "Raiders",
        "Canterbury Bankstown Bulldogs": "Bulldogs",
        "Cronulla Sutherland Sharks": "Sharks",
        "Dolphins": "Dolphins",
        "Gold Coast Titans": "Titans",
        "Manly Warringah Sea Eagles": "Sea Eagles",
        "Melbourne Storm": "Storm",
        "New Zealand Warriors": "Warriors",
        "Newcastle Knights": "Knights",
        "North Queensland Cowboys": "Cowboys",
        "Parramatta Eels": "Eels",
        "Penrith Panthers": "Panthers",
        "South Sydney Rabbitohs": "Rabbitohs",
        "St George Illawarra Dragons": "Dragons",
        "Sydney Roosters": "Roosters",
        "Wests Tigers": "Wests Tigers"
    }
    df["home_nickname"] = df["home_team"].map(team_map)
    df["away_nickname"] = df["away_team"].map(team_map)
    
    # Merge
    merged = pd.merge(
        df, 
        ref_df[["season", "round_num", "home_nickname", "referee"]], 
        on=["season", "round_num", "home_nickname"], 
        how="inner"
    )
    
    return merged

def main():
    df = load_data()
    if df.empty:
        print("No referee data found. Run fetch_referees.py first.")
        return
    
    print("=" * 60)
    print(f"H_003: Referee & Day-of-Week Analysis (n={len(df)})")
    print("=" * 60)
    
    # 1. Day of Week Analysis
    dow_stats = df.groupby("day_of_week").agg(
        n=("home_win", "count"),
        actual_hw=("home_win", "mean"),
        implied_hw=("bk_implied_home", "mean")
    ).reset_index()
    
    dow_stats["calibration_error"] = dow_stats["actual_hw"] - dow_stats["implied_hw"]
    
    print("\n[Day of Week Results]")
    for _, row in dow_stats.iterrows():
        print(f"  {row['day_of_week']:<12} n={row['n']:>3}  actual={row['actual_hw']:.1%}  implied={row['implied_hw']:.1%}  err={row['calibration_error']:+.1%}")

    # 2. Referee Analysis (MIN_GAMES = 10)
    ref_stats = df.groupby("referee").agg(
        n=("home_win", "count"),
        actual_hw=("home_win", "mean"),
        implied_hw=("bk_implied_home", "mean")
    ).reset_index()
    
    ref_stats = ref_stats[ref_stats["n"] >= 10].sort_values("actual_hw", ascending=False)
    ref_stats["calibration_error"] = ref_stats["actual_hw"] - ref_stats["implied_hw"]
    
    print("\n[Individual Referee Results (n >= 10)]")
    for _, row in ref_stats.iterrows():
        print(f"  {row['referee']:<20} n={row['n']:>3}  actual={row['actual_hw']:.1%}  implied={row['implied_hw']:.1%}  err={row['calibration_error']:+.1%}")

    # ANOVA on day of week
    groups_dow = [df[df["day_of_week"] == day]["home_win"].values for day in df["day_of_week"].unique()]
    f_dow, p_dow = stats.f_oneway(*groups_dow)
    
    # ANOVA on referees
    groups_ref = [df[df["referee"] == ref]["home_win"].values for ref in ref_stats["referee"]]
    f_ref, p_ref = stats.f_oneway(*groups_ref) if len(groups_ref) > 1 else (0, 1)

    result_json = {
        "hypothesis_id": "H_003",
        "p_value": float(p_dow),
        "sample_size": int(len(df)),
        "roi_impact": 0.0,
        "is_significant": bool(p_dow < 0.05 or p_ref < 0.05),
        "method": "ANOVA on HW rate by day-of-week and individual referee",
        "data_window": "2021-2025 scraped sample",
        "backtest_type": "in-sample",
        "dow_stats": dow_stats.to_dict("records"),
        "ref_stats": ref_stats.to_dict("records"),
        "anova": {
            "p_dow": float(p_dow),
            "p_ref": float(p_ref)
        },
        "summary": (
            f"Referee analysis (n={len(df)}) shows "
            f"Day-of-Week significance: p={p_dow:.3f}, "
            f"Referee significance: p={p_ref:.3f}."
        )
    }

    with open(RESULTS_DIR / "R_003.json", "w") as f:
        json.dump(result_json, f, indent=2)
    
    # Visualization
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # DOW Calibration Error
    ax1.bar(dow_stats["day_of_week"], dow_stats["calibration_error"], color='teal', alpha=0.7)
    ax1.axhline(0, color='black', linewidth=0.8)
    ax1.set_title("Home Win Calibration Error by Day of Week")
    ax1.set_ylabel("Actual HW - Implied HW")
    ax1.tick_params(axis='x', rotation=45)
    
    # Referee Calibration Error
    ax2.bar(ref_stats["referee"], ref_stats["calibration_error"], color='purple', alpha=0.7)
    ax2.axhline(0, color='black', linewidth=0.8)
    ax2.set_title("Home Win Calibration Error by Referee (n>=10)")
    ax2.set_ylabel("Actual HW - Implied HW")
    ax2.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.savefig(VISUALS_DIR / "H_003_plot.png")
    
    print(f"\nSaved → research/results/R_003.json")
    print(f"Saved → research/visuals/H_003_plot.png")

if __name__ == "__main__":
    main()
