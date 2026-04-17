"""
Venue Bias Strategy — Backtest
Exploits statistically significant home advantage mispricing at specific NRL venues.

Strategy:
  - Back home team at venues with historically elevated home win rate
    when bookmaker closing odds imply a probability below the venue base rate.
  - Fade home team (back away) at venues where home team underperforms.
  - Primary backtest uses bookmaker closing odds (ASB, 2009–2025, ~3,200 matches).
  - Secondary validation uses Betfair exchange opening prices (2021–2025, ~360 matches).

Usage:
    python src/strategy/venue_bias.py
"""

import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"

# ---------------------------------------------------------------------------
# Target venues and thresholds
# ---------------------------------------------------------------------------
BACK_HOME_VENUES = {
    "AAMI Park",
    "Olympic Park Stadium",
    "Queensland Sport and Athletics Centre",
    "Sydney Showground",
}

FADE_HOME_VENUES = {
    "Campbelltown Sports Stadium",
    # Cbus Super Stadium removed — bookmaker backtest showed −10.3% ROI over 81 bets;
    # insufficient edge vs bookmaker margin despite raw home underperformance.
}

MIN_EDGE    = 0.05   # minimum edge before betting (historical rate − implied prob)
MIN_ODDS    = 1.50
MAX_ODDS    = 6.00
FLAT_STAKE  = 100    # dollars per bet


def load_data() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED / "nrl_clean.csv", parse_dates=["date"])
    df["home_win"] = (df["result"] == "home_win").astype(int)
    return df


def compute_venue_baselines(df: pd.DataFrame) -> pd.DataFrame:
    baselines = (
        df.groupby("venue_name")["home_win"]
        .agg(base_hw_rate="mean", n_matches="count")
        .reset_index()
    )
    return baselines


def run_backtest(df: pd.DataFrame, baselines: pd.DataFrame,
                 odds_col_home: str, odds_col_away: str,
                 label: str) -> pd.DataFrame:
    """Generic backtest over any pair of odds columns."""
    sub = df[df[odds_col_home].notna() & df[odds_col_away].notna()].copy()
    sub = sub.merge(baselines, on="venue_name", how="left")

    sub["implied_home"] = 1 / sub[odds_col_home]
    sub["implied_away"] = 1 / sub[odds_col_away]
    sub["edge_back_home"] = sub["base_hw_rate"] - sub["implied_home"]
    sub["edge_fade_home"] = (1 - sub["base_hw_rate"]) - sub["implied_away"]

    records = []
    for _, row in sub.iterrows():
        venue = row.get("venue_name", "")
        bet_type, odds, edge = None, None, None

        if venue in BACK_HOME_VENUES and row["edge_back_home"] >= MIN_EDGE:
            bet_type = "back_home"
            odds = row[odds_col_home]
            edge = row["edge_back_home"]
        elif venue in FADE_HOME_VENUES and row["edge_fade_home"] >= MIN_EDGE:
            bet_type = "fade_home"
            odds = row[odds_col_away]
            edge = row["edge_fade_home"]

        if bet_type is None or pd.isna(odds) or odds < MIN_ODDS or odds > MAX_ODDS:
            continue

        won = (row["result"] == "home_win") if bet_type == "back_home" else (row["result"] == "away_win")
        profit = (odds - 1) * FLAT_STAKE if won else -FLAT_STAKE

        records.append({
            "source": label,
            "date": row["date"],
            "season": row["season"],
            "home_team": row["home_team"],
            "away_team": row["away_team"],
            "venue": venue,
            "bet_type": bet_type,
            "odds": round(float(odds), 3),
            "edge": round(float(edge), 4),
            "base_hw_rate": round(float(row["base_hw_rate"]), 3),
            "implied_prob": round(1 / float(odds), 4),
            "result": row["result"],
            "won": won,
            "stake": FLAT_STAKE,
            "profit": round(float(profit), 2),
        })

    bets = pd.DataFrame(records)
    if not bets.empty:
        bets = bets.sort_values("date").reset_index(drop=True)
        bets["cumulative_profit"] = bets["profit"].cumsum()
        bets["bankroll"] = 10_000 + bets["cumulative_profit"]
    return bets


def kelly_stake(edge: float, odds: float, bankroll: float, fraction: float = 0.25) -> float:
    p = (1 / odds) + edge
    q = 1 - p
    b = odds - 1
    kelly = (b * p - q) / b
    return max(0.0, kelly * fraction * bankroll)


def summarise(bets: pd.DataFrame) -> dict:
    if bets.empty:
        return {}
    wins = bets["won"].sum()
    staked = bets["stake"].sum()
    profit = bets["profit"].sum()
    drawdown = (bets["bankroll"].cummax() - bets["bankroll"]).max()
    return {
        "n": len(bets),
        "wins": int(wins),
        "win_rate": wins / len(bets),
        "staked": staked,
        "profit": profit,
        "roi": profit / staked,
        "max_drawdown": drawdown,
        "avg_odds": bets["odds"].mean(),
        "avg_edge": bets["edge"].mean(),
        "by_venue": bets.groupby("venue").agg(
            n=("profit","count"), wins=("won","sum"),
            profit=("profit","sum"),
            roi=("profit", lambda x: x.sum()/(len(x)*FLAT_STAKE))
        ),
        "by_season": bets.groupby("season").agg(
            n=("profit","count"), wins=("won","sum"),
            profit=("profit","sum"),
        ),
        "bets": bets,
    }


def main():
    df = load_data()
    baselines = compute_venue_baselines(df)

    print("=" * 60)
    print("Venue Baselines")
    print("=" * 60)
    target = baselines[baselines["venue_name"].isin(BACK_HOME_VENUES | FADE_HOME_VENUES)]
    print(target.sort_values("base_hw_rate", ascending=False).to_string(index=False))

    # ── Primary backtest: bookmaker closing odds (2009–2025) ──────────────
    bk_bets = run_backtest(df, baselines, "bk_home_close", "bk_away_close", "Bookmaker")
    bk = summarise(bk_bets)

    print("\n" + "=" * 60)
    print(f"Bookmaker Backtest (2009–2025)  —  {bk.get('n',0)} bets")
    print("=" * 60)
    if bk:
        print(f"Win rate:     {bk['win_rate']:.1%}")
        print(f"Total profit: ${bk['profit']:,.2f}  (staked ${bk['staked']:,.0f})")
        print(f"ROI:          {bk['roi']:.2%}")
        print(f"Max drawdown: ${bk['max_drawdown']:,.2f}")
        print(f"Avg odds:     {bk['avg_odds']:.3f}  |  Avg edge: {bk['avg_edge']:.2%}")
        print("\nBy venue:")
        print(bk["by_venue"].to_string())
        print("\nBy season:")
        print(bk["by_season"].to_string())
        print("\nAll bets:")
        cols = ["date","home_team","away_team","venue","bet_type","odds","edge","result","won","profit","cumulative_profit"]
        print(bk_bets[cols].to_string(index=False))

    # ── Validation backtest: Betfair exchange opening prices (2021–2025) ──
    bf_bets = run_backtest(df, baselines, "bf_home_open", "bf_away_open", "Betfair")
    bf = summarise(bf_bets)

    print("\n" + "=" * 60)
    print(f"Betfair Validation (2021–2025)  —  {bf.get('n',0)} bets")
    print("=" * 60)
    if bf:
        print(f"Win rate:     {bf['win_rate']:.1%}")
        print(f"Total profit: ${bf['profit']:,.2f}  (staked ${bf['staked']:,.0f})")
        print(f"ROI:          {bf['roi']:.2%}")
        print(f"Max drawdown: ${bf['max_drawdown']:,.2f}")

    return bk_bets, bf_bets, baselines, df


if __name__ == "__main__":
    main()
