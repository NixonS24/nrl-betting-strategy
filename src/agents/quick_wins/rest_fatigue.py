"""
Agent 1: Rest Days / Travel Fatigue
====================================
Tests whether short rest (< 7 days since last game) or long travel
(interstate / cross-timezone) causes teams to underperform market odds.

Outputs:
  data/processed/quick_wins/rest_fatigue_findings.md
  Returns a result dict consumed by the coordinator.
"""

import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROCESSED = ROOT / "data" / "processed"
OUT = PROCESSED / "quick_wins"
OUT.mkdir(parents=True, exist_ok=True)

# Approximate state/territory for each venue — used to flag interstate travel
VENUE_STATE = {
    "AAMI Park":                               "VIC",
    "Olympic Park Stadium":                    "VIC",
    "Marvel Stadium":                          "VIC",
    "GIO Stadium":                             "ACT",
    "Canberra Stadium":                        "ACT",
    "Suncorp Stadium":                         "QLD",
    "Queensland Country Bank Stadium":         "QLD",
    "Cbus Super Stadium":                      "QLD",
    "Go Media Stadium":                        "NZ",
    "Mt Smart Stadium":                        "NZ",
    "Accor Stadium":                           "NSW",
    "Sydney Football Stadium (Old)":           "NSW",
    "Allianz Stadium":                         "NSW",
    "CommBank Stadium":                        "NSW",
    "Parramatta Stadium":                      "NSW",
    "BlueBet Stadium":                         "NSW",
    "Campbelltown Sports Stadium":             "NSW",
    "Netstrata Jubilee Stadium":               "NSW",
    "Sharks Stadium":                          "NSW",
    "Leichhardt Oval":                         "NSW",
    "Sydney Showground":                       "NSW",
    "Sydney Cricket Ground":                   "NSW",
    "Industree Group Stadium":                 "NSW",
    "WIN Stadium":                             "NSW",
    "4 Pines Park":                            "NSW",
    "Pepper Stadium":                          "NSW",
    "McDonald Jones Stadium":                  "NSW",
    "Willows Sports Complex":                  "QLD",
    "Queensland Sport and Athletics Centre":   "QLD",
    "TIO Stadium":                             "NT",
    "TIO Traeger Park":                        "NT",
    "Kayo Stadium":                            "QLD",
    "Brisbane Stadium":                        "QLD",
}

# Team home states (for travel estimation)
TEAM_HOME_STATE = {
    "Melbourne Storm":               "VIC",
    "Canberra Raiders":              "ACT",
    "Brisbane Broncos":              "QLD",
    "Gold Coast Titans":             "QLD",
    "North Queensland Cowboys":      "QLD",
    "Dolphins":                      "QLD",
    "New Zealand Warriors":          "NZ",
    "South Sydney Rabbitohs":        "NSW",
    "Sydney Roosters":               "NSW",
    "Parramatta Eels":               "NSW",
    "Canterbury Bankstown Bulldogs": "NSW",
    "Wests Tigers":                  "NSW",
    "Cronulla Sutherland Sharks":    "NSW",
    "Manly Warringah Sea Eagles":    "NSW",
    "Penrith Panthers":              "NSW",
    "Newcastle Knights":             "NSW",
    "St George Illawarra Dragons":   "NSW",
    "Illawarra Steelers":            "NSW",
    "Northern Eagles":               "NSW",
}


def load_data() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED / "nrl_clean.csv", parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df["home_win"] = (df["result"] == "home_win").astype(int)
    return df


def compute_rest_days(df: pd.DataFrame) -> pd.DataFrame:
    """Add home_rest_days and away_rest_days columns."""
    last_game: dict = {}
    home_rest, away_rest = [], []

    for _, row in df.iterrows():
        ht, at, dt = row["home_team"], row["away_team"], row["date"]

        home_rest.append((dt - last_game[ht]).days if ht in last_game else None)
        away_rest.append((dt - last_game[at]).days if at in last_game else None)

        last_game[ht] = dt
        last_game[at] = dt

    df = df.copy()
    df["home_rest_days"] = home_rest
    df["away_rest_days"] = away_rest
    return df


def is_interstate(team: str, venue: str) -> bool:
    team_state  = TEAM_HOME_STATE.get(team)
    venue_state = VENUE_STATE.get(venue)
    if team_state is None or venue_state is None:
        return False
    return team_state != venue_state


def compute_travel(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["away_interstate"] = df.apply(
        lambda r: is_interstate(r["away_team"], r.get("venue_name", "")), axis=1
    )
    return df


def analyse(df: pd.DataFrame) -> dict:
    overall_hw = df["home_win"].mean()
    results = {}

    # ── Rest day buckets ────────────────────────────────────────────────────
    sub = df[df["home_rest_days"].notna() & df["away_rest_days"].notna()].copy()
    sub["home_short_rest"] = sub["home_rest_days"] < 7
    sub["away_short_rest"] = sub["away_rest_days"] < 7

    # Home on short rest
    home_short = sub[sub["home_short_rest"]]
    home_normal = sub[~sub["home_short_rest"]]
    t_hs, p_hs = stats.ttest_ind(home_short["home_win"], home_normal["home_win"])

    # Away on short rest (does away team on short rest hurt them → home wins more?)
    away_short = sub[sub["away_short_rest"]]
    away_normal = sub[~sub["away_short_rest"]]
    t_as, p_as = stats.ttest_ind(away_short["home_win"], away_normal["home_win"])

    results["home_short_rest"] = {
        "n_short": len(home_short), "n_normal": len(home_normal),
        "hw_short": home_short["home_win"].mean(),
        "hw_normal": home_normal["home_win"].mean(),
        "t": t_hs, "p": p_hs,
        "significant": p_hs < 0.05,
    }
    results["away_short_rest"] = {
        "n_short": len(away_short), "n_normal": len(away_normal),
        "hw_short": away_short["home_win"].mean(),
        "hw_normal": away_normal["home_win"].mean(),
        "t": t_as, "p": p_as,
        "significant": p_as < 0.05,
    }

    # Rest day buckets (fine-grained)
    sub["away_rest_bucket"] = pd.cut(
        sub["away_rest_days"],
        bins=[0, 5, 6, 7, 10, 99],
        labels=["≤5d", "6d", "7d", "8-10d", "10d+"],
    )
    rest_buckets = sub.groupby("away_rest_bucket", observed=True)["home_win"].agg(
        ["mean", "count"]
    )
    rest_buckets.columns = ["home_win_rate", "n"]
    results["away_rest_buckets"] = rest_buckets

    # ── Interstate travel ───────────────────────────────────────────────────
    interstate = df[df["away_interstate"]]
    domestic   = df[~df["away_interstate"]]
    t_it, p_it = stats.ttest_ind(interstate["home_win"], domestic["home_win"])
    results["interstate"] = {
        "n_interstate": len(interstate), "n_domestic": len(domestic),
        "hw_interstate": interstate["home_win"].mean(),
        "hw_domestic":   domestic["home_win"].mean(),
        "t": t_it, "p": p_it,
        "significant": p_it < 0.05,
    }

    # ── Combined: away team interstate AND short rest ───────────────────────
    combined = df[df.get("away_interstate", False) & (df.get("away_rest_days", 99) < 7)]
    if len(combined) > 20:
        t_c, p_c = stats.ttest_1samp(combined["home_win"], overall_hw)
        results["combined"] = {
            "n": len(combined),
            "hw_rate": combined["home_win"].mean(),
            "overall_hw": overall_hw,
            "t": t_c, "p": p_c,
            "significant": p_c < 0.05,
        }

    return results


def write_findings(results: dict, df: pd.DataFrame) -> str:
    hs  = results["home_short_rest"]
    aws = results["away_short_rest"]
    it  = results["interstate"]
    rb  = results["away_rest_buckets"]

    lines = [
        "# Agent 1 — Rest Days & Travel Fatigue Findings\n",
        f"Dataset: {len(df):,} matches, {df['date'].min().date()} – {df['date'].max().date()}\n",
        "---\n",
        "## Home Team on Short Rest (< 7 days)",
        f"- Short rest matches: {hs['n_short']}  |  Normal rest: {hs['n_normal']}",
        f"- Home win rate — short rest: **{hs['hw_short']:.1%}**  |  normal: {hs['hw_normal']:.1%}",
        f"- t={hs['t']:.3f}, p={hs['p']:.4f} — {'**SIGNIFICANT**' if hs['significant'] else 'not significant'}\n",
        "## Away Team on Short Rest (< 7 days)",
        f"- Short rest matches: {aws['n_short']}  |  Normal rest: {aws['n_normal']}",
        f"- Home win rate when away on short rest: **{aws['hw_short']:.1%}**  |  normal: {aws['hw_normal']:.1%}",
        f"- t={aws['t']:.3f}, p={aws['p']:.4f} — {'**SIGNIFICANT**' if aws['significant'] else 'not significant'}\n",
        "## Away Rest Day Buckets",
        rb.to_string(), "\n",
        "## Interstate Travel (Away Team)",
        f"- Interstate away matches: {it['n_interstate']}  |  Domestic: {it['n_domestic']}",
        f"- Home win rate — interstate away: **{it['hw_interstate']:.1%}**  |  domestic: {it['hw_domestic']:.1%}",
        f"- t={it['t']:.3f}, p={it['p']:.4f} — {'**SIGNIFICANT**' if it['significant'] else 'not significant'}\n",
    ]

    if "combined" in results:
        c = results["combined"]
        lines += [
            "## Combined: Away Team Interstate + Short Rest",
            f"- n={c['n']}, home win rate: **{c['hw_rate']:.1%}** vs overall {c['overall_hw']:.1%}",
            f"- t={c['t']:.3f}, p={c['p']:.4f} — {'**SIGNIFICANT**' if c['significant'] else 'not significant'}\n",
        ]

    # Recommendation
    any_sig = any([hs["significant"], aws["significant"], it["significant"]])
    lines += [
        "---\n",
        "## Recommendation",
        "**INTEGRATE** — add as filter in venue_bias.py" if any_sig
        else "**DO NOT INTEGRATE** — no statistically significant fatigue effect found",
    ]

    text = "\n".join(lines)
    (OUT / "rest_fatigue_findings.md").write_text(text)
    return text


def run() -> dict:
    print("\n[Agent 1] Rest Days & Travel Fatigue — starting...")
    df = load_data()
    df = compute_rest_days(df)
    df = compute_travel(df)
    results = analyse(df)
    text = write_findings(results, df)
    print(text)

    any_sig = any([
        results["home_short_rest"]["significant"],
        results["away_short_rest"]["significant"],
        results["interstate"]["significant"],
    ])

    # Build filter kwargs to pass back to coordinator
    filters = {}
    if results["away_short_rest"]["significant"] and results["away_short_rest"]["hw_short"] > results["away_short_rest"]["hw_normal"]:
        filters["boost_home_if_away_short_rest"] = True
    if results["interstate"]["significant"] and results["interstate"]["hw_interstate"] > results["interstate"]["hw_domestic"]:
        filters["boost_home_if_away_interstate"] = True

    return {
        "agent": "rest_fatigue",
        "significant": any_sig,
        "results": results,
        "filters": filters,
        "findings_path": str(OUT / "rest_fatigue_findings.md"),
        "df_with_features": df,
    }


if __name__ == "__main__":
    run()
