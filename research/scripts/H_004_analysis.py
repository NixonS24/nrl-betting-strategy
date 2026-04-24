"""
H_004 Analysis — AAMI Park: Venue Effect vs Melbourne Storm Team Effect

Hypothesis: The AAMI Park home-win edge is not a generic venue effect; it is a
Melbourne Storm home-team effect expressed through a venue they almost exclusively
occupy. Treating it as a portable venue signal overstates generalisability.

Test type: DESCRIPTIVE + SIGNIFICANCE TEST
  - Primary question: what fraction of AAMI Park home matches are Storm matches?
  - Secondary question: does the edge persist when framed as a Storm home-game signal?
  - Backtest: holdout (pre-2022 signal, 2022+ test) — same discipline as H_001/H_002.
  - Classification: if Storm = >90% of AAMI Park home matches, classify as
    "team-linked venue edge" not "generic venue edge".

Variables used: venue_name, home_team, away_team, season, result,
                bk_home_close, bk_implied_home, bf_home_open, bf_implied_home

Output:
  - research/results/R_004.json
  - research/visuals/H_004_plot.png
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

VENUE = "AAMI Park"
STORM = "Melbourne Storm"
TRAIN_CUTOFF = 2022
MIN_EDGE   = 0.05
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
# Sample composition analysis
# ---------------------------------------------------------------------------
def analyse_composition(df: pd.DataFrame) -> dict:
    """
    How many AAMI Park home matches are Storm matches, historically and by era?
    """
    aami = df[df["venue_name"] == VENUE].copy()

    total = len(aami)
    by_team = (
        aami.groupby("home_team")
        .agg(n=("home_win", "count"), hw_rate=("home_win", "mean"))
        .sort_values("n", ascending=False)
        .reset_index()
    )

    storm_n = int(aami[aami["home_team"] == STORM].shape[0])
    storm_pct = storm_n / total if total > 0 else 0

    # By era
    by_era = (
        aami.assign(era=lambda x: x["season"].apply(lambda s: "pre-2019" if s < 2019 else "2019+"))
        .groupby(["era", "home_team"])
        .agg(n=("home_win", "count"))
        .reset_index()
    )

    return {
        "total_aami_matches": int(total),
        "storm_matches": storm_n,
        "storm_pct": round(float(storm_pct), 4),
        "is_effectively_storm_only": storm_pct > 0.90,
        "by_team": by_team.to_dict("records"),
        "by_era": by_era.to_dict("records"),
    }


# ---------------------------------------------------------------------------
# Signal test: is edge venue-wide or Storm-specific?
# ---------------------------------------------------------------------------
def test_edge_source(df: pd.DataFrame, label: str) -> dict:
    """
    Compare HW rate vs bookmaker-implied for Storm home matches at AAMI Park
    vs all other teams' matches at AAMI Park.
    """
    aami = df[df["venue_name"] == VENUE & df["bk_implied_home"].notna()].copy() \
        if False else df[(df["venue_name"] == VENUE) & (df["bk_implied_home"].notna())].copy()

    if aami.empty:
        return {"error": "no data", "label": label}

    storm_mask = aami["home_team"] == STORM

    def compute_stats(sub: pd.DataFrame, name: str) -> dict:
        if sub.empty:
            return {"name": name, "n": 0}
        n = len(sub)
        actual_hw = sub["home_win"].mean()
        implied_hw = sub["bk_implied_home"].mean()
        residuals = sub["home_win"] - sub["bk_implied_home"]
        t_stat, p_two = stats.ttest_1samp(residuals, popmean=0)
        # One-sided: we expect actual > implied (back home = positive edge)
        p_one = p_two / 2 if t_stat > 0 else 1.0 - p_two / 2
        return {
            "name": name,
            "n": int(n),
            "actual_hw_rate": float(round(actual_hw, 4)),
            "mean_implied_hw": float(round(implied_hw, 4)),
            "calibration_error": float(round(actual_hw - implied_hw, 4)),
            "t_stat": float(round(float(t_stat), 4)),
            "p_value_one_sided": float(round(p_one, 4)),
            "p_value_two_sided": float(round(float(p_two), 4)),
            "significant": bool(p_one < 0.05),
        }

    return {
        "label": label,
        "storm_home": compute_stats(aami[storm_mask], f"Storm home at AAMI ({label})"),
        "other_home": compute_stats(aami[~storm_mask], f"Other teams at AAMI ({label})"),
        "combined": compute_stats(aami, f"All AAMI ({label})"),
    }


# ---------------------------------------------------------------------------
# Backtest: AAMI Park back-home rule on holdout
# ---------------------------------------------------------------------------
def run_backtest(test_df: pd.DataFrame, base_hw_rate: float,
                 filter_storm_only: bool, label: str) -> pd.DataFrame:
    """
    Back home at AAMI Park when edge >= MIN_EDGE.
    Optionally restrict to Storm home games only.
    """
    sub = test_df[
        (test_df["venue_name"] == VENUE)
        & test_df["bk_home_close"].notna()
    ].copy()

    if filter_storm_only:
        sub = sub[sub["home_team"] == STORM]

    if sub.empty:
        return pd.DataFrame()

    sub["implied_home"] = 1 / sub["bk_home_close"]
    sub["edge_back"] = base_hw_rate - sub["implied_home"]

    records = []
    for _, row in sub.iterrows():
        if row["edge_back"] < MIN_EDGE:
            continue
        odds = row["bk_home_close"]
        if pd.isna(odds) or odds < MIN_ODDS or odds > MAX_ODDS:
            continue
        won = row["result"] == "home_win"
        profit = (odds - 1) * FLAT_STAKE if won else -FLAT_STAKE
        records.append({
            "label": label,
            "date": row["date"],
            "season": int(row["season"]),
            "home_team": row["home_team"],
            "away_team": row["away_team"],
            "odds": round(float(odds), 3),
            "edge": round(float(row["edge_back"]), 4),
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
        return {"n": 0, "wins": 0, "win_rate": 0.0, "profit": 0.0, "roi": 0.0}
    n = len(bets)
    wins = int(bets["won"].sum())
    profit = float(bets["profit"].sum())
    return {
        "n": n,
        "wins": wins,
        "win_rate": round(wins / n, 4),
        "profit": round(profit, 2),
        "roi": round(profit / (n * FLAT_STAKE), 4),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    df = load_data()
    train_df = df[df["season"] < TRAIN_CUTOFF]
    test_df  = df[df["season"] >= TRAIN_CUTOFF]

    print("=" * 60)
    print("H_004: AAMI Park — Venue vs Storm Team Effect")
    print("=" * 60)

    # ── Sample composition ────────────────────────────────────────────────────
    comp = analyse_composition(df)
    print(f"\n[Sample composition — all time]")
    print(f"  Total AAMI Park home matches: {comp['total_aami_matches']}")
    print(f"  Melbourne Storm home matches: {comp['storm_matches']} "
          f"({comp['storm_pct']:.1%})")
    print(f"  Effectively Storm-only venue: {comp['is_effectively_storm_only']}")
    print("\n  By home team:")
    for row in comp["by_team"]:
        print(f"    {row['home_team']:<35} n={row['n']:>3}  HW={row['hw_rate']:.1%}")

    # ── Signal tests ──────────────────────────────────────────────────────────
    train_edge = test_edge_source(train_df, f"pre-{TRAIN_CUTOFF}")
    test_edge  = test_edge_source(test_df, f"{TRAIN_CUTOFF}+")

    for window, edge in [("Training", train_edge), ("Holdout", test_edge)]:
        label = edge.get("label", "")
        print(f"\n[{window} window: {label}]")
        for key in ("storm_home", "other_home", "combined"):
            s = edge.get(key, {})
            if not s or s.get("n", 0) == 0:
                print(f"  {key}: no data")
                continue
            sig = " ***" if s.get("significant") else ""
            print(f"  {key:<20} n={s['n']:>3}  actual={s['actual_hw_rate']:.1%}  "
                  f"implied={s['mean_implied_hw']:.1%}  "
                  f"error={s['calibration_error']:+.1%}  "
                  f"p(1-sided)={s['p_value_one_sided']:.3f}{sig}")

    # ── Training baseline for backtest ────────────────────────────────────────
    storm_train = train_df[
        (train_df["venue_name"] == VENUE) & (train_df["home_team"] == STORM)
    ]
    storm_hw_rate = float(storm_train["home_win"].mean()) if not storm_train.empty else 0.789

    all_aami_train = train_df[train_df["venue_name"] == VENUE]
    all_hw_rate = float(all_aami_train["home_win"].mean()) if not all_aami_train.empty else 0.760

    # ── Holdout backtests ─────────────────────────────────────────────────────
    bets_all   = run_backtest(test_df, all_hw_rate,   filter_storm_only=False, label="AllAAMI")
    bets_storm = run_backtest(test_df, storm_hw_rate, filter_storm_only=True,  label="StormOnly")

    s_all   = summarise(bets_all)
    s_storm = summarise(bets_storm)

    print(f"\n[Holdout Backtest ({TRAIN_CUTOFF}+): bookmaker closing odds]")
    print(f"  ALL AAMI matches:    n={s_all['n']}, wins={s_all['wins']}, "
          f"win_rate={s_all['win_rate']:.1%}, ROI={s_all['roi']:.2%}, profit=${s_all['profit']:.2f}")
    print(f"  Storm home only:     n={s_storm['n']}, wins={s_storm['wins']}, "
          f"win_rate={s_storm['win_rate']:.1%}, ROI={s_storm['roi']:.2%}, profit=${s_storm['profit']:.2f}")
    print(f"\n  Storm HW baseline used: {storm_hw_rate:.1%}  "
          f"| All AAMI baseline used: {all_hw_rate:.1%}")
    print(f"  Backtest type: HOLDOUT (out-of-sample)")

    # ── Classification ────────────────────────────────────────────────────────
    storm_pct = comp["storm_pct"]
    train_storm_sig = train_edge.get("storm_home", {}).get("significant", False)
    train_other_sig = train_edge.get("other_home", {}).get("significant", False)

    if storm_pct > 0.90:
        classification = "team_linked_venue_edge"
        classification_note = (
            f"AAMI Park is {storm_pct:.1%} Melbourne Storm home games. "
            "The edge cannot be separated from Storm's home-team performance. "
            "Recommend reframing as 'Melbourne Storm home edge' rather than 'AAMI Park venue edge'."
        )
    elif train_storm_sig and not train_other_sig:
        classification = "team_linked_venue_edge"
        classification_note = (
            "Storm home matches are significant; other teams are not. "
            "The venue label is a proxy for team identity."
        )
    else:
        classification = "generic_venue_edge"
        classification_note = "Insufficient evidence to separate venue from team effect."

    print(f"\n  Classification: {classification}")
    print(f"  {classification_note}")

    # ── Primary p-value: storm home signal in training window ─────────────────
    primary_p = train_edge.get("storm_home", {}).get("p_value_one_sided", 1.0)
    is_sig = bool(primary_p < 0.05 and comp["storm_pct"] > 0.80)

    # ── Save JSON ─────────────────────────────────────────────────────────────
    result_json = {
        "hypothesis_id": "H_004",
        "p_value": float(primary_p),
        "sample_size": int(comp["storm_matches"]),
        "roi_impact": float(s_storm["roi"]),
        "is_significant": is_sig,
        "method": (
            "Composition analysis (% Storm home) + one-sample t-test on "
            "(home_win − bk_implied_home) residuals, one-sided (actual > implied), "
            "separately for Storm home matches and other teams"
        ),
        "data_window": f"Signal: pre-{TRAIN_CUTOFF}. Backtest: {TRAIN_CUTOFF}–2025.",
        "backtest_type": "holdout",
        "composition": comp,
        "classification": classification,
        "classification_note": classification_note,
        "training_signal": {
            "storm_home": train_edge.get("storm_home", {}),
            "other_home": train_edge.get("other_home", {}),
            "combined": train_edge.get("combined", {}),
        },
        "holdout_signal": {
            "storm_home": test_edge.get("storm_home", {}),
            "other_home": test_edge.get("other_home", {}),
            "combined": test_edge.get("combined", {}),
        },
        "holdout_backtest_all_aami": s_all,
        "holdout_backtest_storm_only": s_storm,
        "summary": (
            f"AAMI Park is {storm_pct:.1%} Melbourne Storm home games. "
            f"Classification: {classification}. "
            f"Storm home training signal: p={primary_p:.3f} "
            f"({'significant' if is_sig else 'not significant'}). "
            f"Holdout ROI (Storm only): {s_storm['roi']:.2%} over {s_storm['n']} bets."
        ),
    }

    with open(RESULTS_DIR / "R_004.json", "w") as f:
        json.dump(result_json, f, indent=2)
    print(f"\nSaved → research/results/R_004.json")

    # ── Visualisation ─────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Panel 1: AAMI Park composition (pie or bar by home team)
    ax1 = axes[0]
    by_team_df = pd.DataFrame(comp["by_team"])
    if not by_team_df.empty:
        colors = ["steelblue" if t == STORM else "lightgrey"
                  for t in by_team_df["home_team"]]
        ax1.bar(range(len(by_team_df)), by_team_df["n"], color=colors)
        labels = [t.replace("Melbourne ", "").replace(" ", "\n") for t in by_team_df["home_team"]]
        ax1.set_xticks(range(len(by_team_df)))
        ax1.set_xticklabels(labels, rotation=30, ha="right", fontsize=7)
        ax1.set_ylabel("Number of home matches")
        ax1.set_title(f"AAMI Park: Home Team Composition (n={comp['total_aami_matches']})")
        # Add Storm % annotation
        ax1.text(0, by_team_df["n"].max() * 0.9,
                 f"Storm: {storm_pct:.1%} of all AAMI home matches",
                 fontsize=9, color="steelblue")

    # Panel 2: Cumulative profit — all AAMI vs Storm only (holdout)
    ax2 = axes[1]
    if not bets_all.empty:
        ax2.plot(range(len(bets_all)), bets_all["cumulative_profit"],
                 label=f"All AAMI (n={s_all['n']}, ROI={s_all['roi']:.1%})",
                 color="steelblue", linestyle="--")
    if not bets_storm.empty:
        ax2.plot(range(len(bets_storm)), bets_storm["cumulative_profit"],
                 label=f"Storm only (n={s_storm['n']}, ROI={s_storm['roi']:.1%})",
                 color="darkorange")
    ax2.axhline(0, color="grey", linestyle=":", linewidth=0.8)
    ax2.set_xlabel("Bet number")
    ax2.set_ylabel("Cumulative profit ($)")
    ax2.set_title(f"Holdout Backtest ({TRAIN_CUTOFF}+): AAMI Park Back-Home")
    ax2.legend(fontsize=8)

    plt.suptitle("H_004: AAMI Park — Venue Effect vs Melbourne Storm Team Effect", fontsize=12)
    plt.tight_layout()
    plt.savefig(VISUALS_DIR / "H_004_plot.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved → research/visuals/H_004_plot.png")

    return result_json


if __name__ == "__main__":
    result = main()
    print("\n" + "=" * 60)
    print("Result JSON:")
    print(json.dumps(result, indent=2, default=str))
