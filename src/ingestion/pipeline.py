"""
NRL Data Pipeline
Merges three data sources into a unified analysis dataset:
  1. AusSportsBetting (data/raw/nrlmanualdownlaod.xlsx) — bookmaker odds 2009–present (primary odds)
  2. uselessnrlstats (data/raw/uselessnrlstats/match_data.csv) — match results 1998–present
  3. Betfair (data/raw/betfair/) — exchange odds 2021–present
"""

import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
PROCESSED.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Top-8 clubs (historically dominant NRL franchises)
# ---------------------------------------------------------------------------
TOP_8_CLUBS = {
    "Sydney Roosters", "South Sydney Rabbitohs", "Melbourne Storm",
    "Penrith Panthers", "Brisbane Broncos", "Parramatta Eels",
    "Canterbury Bulldogs", "Manly Sea Eagles", "North Queensland Cowboys",
    "Cronulla Sharks", "St George Illawarra Dragons",
}

# Betfair short names → canonical full names
BETFAIR_NAME_MAP = {
    "Melbourne":   "Melbourne Storm",
    "Parramatta":  "Parramatta Eels",
    "Brisbane":    "Brisbane Broncos",
    "Penrith":     "Penrith Panthers",
    "NZ Warriors": "New Zealand Warriors",
    "Newcastle":   "Newcastle Knights",
    "Roosters":    "Sydney Roosters",
    "Rabbitohs":   "South Sydney Rabbitohs",
    "Bulldogs":    "Canterbury Bulldogs",
    "Sharks":      "Cronulla Sharks",
    "Raiders":     "Canberra Raiders",
    "Knights":     "Newcastle Knights",
    "Tigers":      "Wests Tigers",
    "Cowboys":     "North Queensland Cowboys",
    "Titans":      "Gold Coast Titans",
    "Warriors":    "New Zealand Warriors",
    "Sea Eagles":  "Manly Sea Eagles",
    "Eels":        "Parramatta Eels",
    "Panthers":    "Penrith Panthers",
    "Storm":       "Melbourne Storm",
    "Broncos":     "Brisbane Broncos",
    "Dragons":     "St George Illawarra Dragons",
    "Wests Tigers":"Wests Tigers",
    "Dolphins":    "Dolphins",
}


def load_match_history() -> pd.DataFrame:
    """Load uselessnrlstats NRL match data (1998-present)."""
    path = RAW / "uselessnrlstats" / "match_data.csv"
    df = pd.read_csv(path)
    df = df[df["competition"] == "NRL"].copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    df = df.rename(columns={
        "home_team_score": "home_score",
        "away_team_score": "away_score",
    })
    # Normalise team names to canonical set
    df["home_team"] = df["home_team"].map(lambda x: CANONICAL_TEAM_MAP.get(x, x))
    df["away_team"] = df["away_team"].map(lambda x: CANONICAL_TEAM_MAP.get(x, x))

    # Derived columns
    df["result"] = np.where(
        df["home_score"] > df["away_score"], "home_win",
        np.where(df["home_score"] < df["away_score"], "away_win", "draw")
    )
    df["margin"] = df["home_score"] - df["away_score"]
    df["total_points"] = df["home_score"] + df["away_score"]
    df["season"] = df["date"].dt.year
    df["is_top8_home"] = df["home_team"].isin(TOP_8_CLUBS)
    df["is_top8_away"] = df["away_team"].isin(TOP_8_CLUBS)
    df["both_top8"] = df["is_top8_home"] & df["is_top8_away"]

    return df[[
        "date", "season", "round", "home_team", "away_team",
        "home_score", "away_score", "result", "margin", "total_points",
        "venue_id", "is_top8_home", "is_top8_away", "both_top8",
        "crowd", "match_id"
    ]]


def add_rolling_form(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """Add rolling win % (last N games) for home and away teams."""
    df = df.sort_values("date").copy()
    records = []
    team_results: dict = {}

    for _, row in df.iterrows():
        ht, at = row["home_team"], row["away_team"]

        def win_rate(team, result_val):
            hist = team_results.get(team, [])
            if len(hist) == 0:
                return np.nan
            recent = hist[-window:]
            return sum(1 for r in recent if r == result_val) / len(recent)

        home_form = win_rate(ht, "win")
        away_form = win_rate(at, "win")
        records.append({"home_form_last5": home_form, "away_form_last5": away_form})

        # Update history
        if row["result"] == "home_win":
            team_results.setdefault(ht, []).append("win")
            team_results.setdefault(at, []).append("loss")
        elif row["result"] == "away_win":
            team_results.setdefault(ht, []).append("loss")
            team_results.setdefault(at, []).append("win")
        else:
            team_results.setdefault(ht, []).append("draw")
            team_results.setdefault(at, []).append("draw")

    form_df = pd.DataFrame(records, index=df.index)
    return pd.concat([df, form_df], axis=1)


def load_betfair_odds() -> pd.DataFrame:
    """Load and pivot Betfair Match Odds CSVs (2021-2026) into one row per match."""
    dfs = []
    for path in sorted((RAW / "betfair").glob("NRL_*_Match_Odds.csv")):
        df = pd.read_csv(path, encoding="utf-8-sig")
        dfs.append(df)
    if not dfs:
        return pd.DataFrame()

    raw = pd.concat(dfs, ignore_index=True)
    raw["EVENT_DATE"] = pd.to_datetime(raw["EVENT_DATE"], utc=True).dt.tz_localize(None).dt.normalize()

    # Normalise runner names
    raw["runner_canonical"] = raw["RUNNER_NAME"].map(BETFAIR_NAME_MAP).fillna(raw["RUNNER_NAME"])
    raw["home_canonical"] = raw["HOME_TEAM"].map(BETFAIR_NAME_MAP).fillna(raw["HOME_TEAM"])

    # One row per selection; pivot to one row per match
    home_rows = raw[raw["runner_canonical"] == raw["home_canonical"]].copy()
    away_rows = raw[raw["runner_canonical"] != raw["home_canonical"]].copy()

    home_odds = home_rows[["EVENT_DATE", "HOME_TEAM", "AWAY_TEAM",
                            "HOME_SCORE", "AWAY_SCORE", "IS_WINNER",
                            "BEST_BACK_FIRST_BOUNCE", "BEST_BACK_PRICE_HALF_TIME",
                            "TOTAL_MATCHED_VOLUME"]].rename(columns={
        "HOME_TEAM": "home_team", "AWAY_TEAM": "away_team",
        "HOME_SCORE": "bf_home_score", "AWAY_SCORE": "bf_away_score",
        "BEST_BACK_FIRST_BOUNCE": "bf_home_open",
        "BEST_BACK_PRICE_HALF_TIME": "bf_home_ht",
        "TOTAL_MATCHED_VOLUME": "bf_volume",
        "EVENT_DATE": "date",
    })

    away_odds = away_rows[["EVENT_DATE", "HOME_TEAM", "AWAY_TEAM",
                            "BEST_BACK_FIRST_BOUNCE", "BEST_BACK_PRICE_HALF_TIME"]].rename(columns={
        "HOME_TEAM": "home_team", "AWAY_TEAM": "away_team",
        "EVENT_DATE": "date",
        "BEST_BACK_FIRST_BOUNCE": "bf_away_open",
        "BEST_BACK_PRICE_HALF_TIME": "bf_away_ht",
    })

    bf = home_odds.merge(away_odds, on=["date", "home_team", "away_team"], how="left")

    # Implied probabilities from best-back prices (1/odds)
    bf["bf_implied_home"] = 1 / bf["bf_home_open"]
    bf["bf_implied_away"] = 1 / bf["bf_away_open"]

    # Normalise team names to canonical set
    bf["home_team"] = bf["home_team"].map(lambda x: CANONICAL_TEAM_MAP.get(x, x))
    bf["away_team"] = bf["away_team"].map(lambda x: CANONICAL_TEAM_MAP.get(x, x))

    return bf


# AusSportsBetting venue name → canonical (to match uselessnrlstats)
ASB_VENUE_MAP = {
    "AAMI Park": "AAMI Park",
    "Accor Stadium": "Accor Stadium",
    "Stadium Australia": "Accor Stadium",
    "ANZ Stadium": "Accor Stadium",
    "Suncorp Stadium": "Suncorp Stadium",
    "Lang Park": "Suncorp Stadium",
    "McDonald Jones Stadium": "McDonald Jones Stadium",
    "Hunter Stadium": "McDonald Jones Stadium",
    "BlueBet Stadium": "BlueBet Stadium",
    "Penrith Stadium": "BlueBet Stadium",
    "CommBank Stadium": "CommBank Stadium",
    "Bankwest Stadium": "CommBank Stadium",
    "Parramatta Stadium": "Parramatta Stadium",
    "Campbelltown Sports Stadium": "Campbelltown Sports Stadium",
    "Leichhardt Oval": "Leichhardt Oval",
    "Cbus Super Stadium": "Cbus Super Stadium",
    "Robina Stadium": "Cbus Super Stadium",
    "GIO Stadium": "GIO Stadium",
    "Canberra Stadium": "GIO Stadium",
    "4 Pines Park": "4 Pines Park",
    "Brookvale Oval": "4 Pines Park",
    "WIN Stadium": "WIN Stadium",
    "Netstrata Jubilee Stadium": "Netstrata Jubilee Stadium",
    "Sydney Cricket Ground": "Sydney Cricket Ground",
    "Queensland Country Bank Stadium": "Queensland Country Bank Stadium",
    "Go Media Stadium": "Go Media Stadium",
    "Mount Smart Stadium": "Go Media Stadium",
}

# Canonical team names — uselessnrlstats modern-era spellings are the authority
# Both ASB and Betfair names are mapped to these
CANONICAL_TEAM_MAP = {
    # AusSportsBetting variants
    "Canterbury Bulldogs":           "Canterbury Bankstown Bulldogs",
    "Canterbury-Bankstown Bulldogs": "Canterbury Bankstown Bulldogs",
    "Cronulla Sharks":               "Cronulla Sutherland Sharks",
    "Cronulla-Sutherland Sharks":    "Cronulla Sutherland Sharks",
    "Manly Sea Eagles":              "Manly Warringah Sea Eagles",
    "Manly-Warringah Sea Eagles":    "Manly Warringah Sea Eagles",
    "North QLD Cowboys":             "North Queensland Cowboys",
    "St. George Illawarra Dragons":  "St George Illawarra Dragons",
    "St George Dragons":             "St George Illawarra Dragons",
    # Betfair short names
    "Melbourne":   "Melbourne Storm",
    "Parramatta":  "Parramatta Eels",
    "Brisbane":    "Brisbane Broncos",
    "Penrith":     "Penrith Panthers",
    "NZ Warriors": "New Zealand Warriors",
    "Newcastle":   "Newcastle Knights",
    "Roosters":    "Sydney Roosters",
    "Rabbitohs":   "South Sydney Rabbitohs",
    "Bulldogs":    "Canterbury Bankstown Bulldogs",
    "Sharks":      "Cronulla Sutherland Sharks",
    "Raiders":     "Canberra Raiders",
    "Knights":     "Newcastle Knights",
    "Tigers":      "Wests Tigers",
    "Cowboys":     "North Queensland Cowboys",
    "Titans":      "Gold Coast Titans",
    "Warriors":    "New Zealand Warriors",
    "Sea Eagles":  "Manly Warringah Sea Eagles",
    "Eels":        "Parramatta Eels",
    "Panthers":    "Penrith Panthers",
    "Storm":       "Melbourne Storm",
    "Broncos":     "Brisbane Broncos",
    "Dragons":     "St George Illawarra Dragons",
}

# Alias for backwards compat in existing functions
ASB_TEAM_MAP = CANONICAL_TEAM_MAP


def load_aussportsbetting() -> pd.DataFrame:
    """Load AusSportsBetting bookmaker odds (2009–present)."""
    path = RAW / "nrlmanualdownlaod.xlsx"
    if not path.exists():
        print("  AusSportsBetting file not found — skipping")
        return pd.DataFrame()

    df = pd.read_excel(path, engine="openpyxl", header=1)
    df = df[df["Date"].notna() & (df["Date"] != "Date")].copy()
    df["date"] = pd.to_datetime(df["Date"], errors="coerce").dt.normalize()
    df = df[df["date"].notna()].copy()

    # Normalise team names
    df["home_team"] = df["Home Team"].map(ASB_TEAM_MAP).fillna(df["Home Team"])
    df["away_team"] = df["Away Team"].map(ASB_TEAM_MAP).fillna(df["Away Team"])

    # Normalise venue names
    df["venue_asb"] = df["Venue"].map(ASB_VENUE_MAP).fillna(df["Venue"])

    # Select and rename key odds columns
    df = df.rename(columns={
        "Home Odds": "bk_home_close",
        "Away Odds": "bk_away_close",
        "Draw Odds": "bk_draw_close",
        "Home Odds Open": "bk_home_open",
        "Away Odds Open": "bk_away_open",
        "Home Score": "asb_home_score",
        "Away Score": "asb_away_score",
    })

    # Implied probabilities from closing bookmaker odds
    df["bk_implied_home"] = pd.to_numeric(df["bk_home_close"], errors="coerce").rdiv(1)
    df["bk_implied_away"] = pd.to_numeric(df["bk_away_close"], errors="coerce").rdiv(1)
    df["bk_implied_draw"] = pd.to_numeric(df["bk_draw_close"], errors="coerce").rdiv(1)

    keep = ["date", "home_team", "away_team", "venue_asb",
            "bk_home_open", "bk_away_open",
            "bk_home_close", "bk_away_close", "bk_draw_close",
            "bk_implied_home", "bk_implied_away", "bk_implied_draw",
            "asb_home_score", "asb_away_score"]
    return df[[c for c in keep if c in df.columns]]


def build_pipeline() -> pd.DataFrame:
    print("Loading match history...")
    matches = load_match_history()
    print(f"  NRL matches: {len(matches)} ({matches['date'].min().date()} - {matches['date'].max().date()})")

    print("Adding rolling form features...")
    matches = add_rolling_form(matches)

    print("Loading AusSportsBetting bookmaker odds...")
    asb = load_aussportsbetting()
    if not asb.empty:
        print(f"  ASB matches: {len(asb)} ({asb['date'].min().date()} - {asb['date'].max().date()})")
        matches = matches.merge(asb, on=["date", "home_team", "away_team"], how="left")
        asb_joined = matches["bk_home_close"].notna().sum()
        print(f"  ASB join: {asb_joined} matches with bookmaker odds")
    else:
        print("  No AusSportsBetting data — continuing without bookmaker odds")

    print("Loading Betfair exchange odds...")
    bf = load_betfair_odds()
    if not bf.empty:
        print(f"  Betfair matches: {len(bf)} ({bf['date'].min().date()} - {bf['date'].max().date()})")
        matches = matches.merge(bf, on=["date", "home_team", "away_team"], how="left")
        bf_joined = matches["bf_home_open"].notna().sum()
        print(f"  Betfair join: {bf_joined} matches with exchange odds")
    else:
        print("  No Betfair data found — continuing without exchange odds")

    # Add venue names from uselessnrlstats lookup
    venue_path = RAW / "uselessnrlstats" / "venue_data.csv"
    if venue_path.exists():
        venues = pd.read_csv(venue_path)[["venue_id", "venue_name", "location"]]
        matches = matches.merge(venues, on="venue_id", how="left")
        # Prefer uselessnrlstats venue_name; fall back to ASB venue
        if "venue_asb" in matches.columns:
            matches["venue_name"] = matches["venue_name"].fillna(matches["venue_asb"])

    out = PROCESSED / "nrl_clean.csv"
    matches.to_csv(out, index=False)
    print(f"\nWrote {len(matches)} rows → {out}")

    print("\n--- Data Quality Report ---")
    print(f"Shape:        {matches.shape}")
    print(f"Date range:   {matches['date'].min().date()} to {matches['date'].max().date()}")
    print(f"Draws:        {(matches['result'] == 'draw').sum()} ({(matches['result']=='draw').mean()*100:.2f}%)")
    print(f"Both top-8:   {matches['both_top8'].sum()} matches")
    print(f"Key nulls:")
    for col in ["home_form_last5", "bk_home_close", "bf_home_open", "venue_name"]:
        if col in matches.columns:
            print(f"  {col}: {matches[col].isna().sum()} nulls")

    return matches


if __name__ == "__main__":
    build_pipeline()
