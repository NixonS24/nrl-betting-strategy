"""
Weekend Picks Generator
Applies the venue bias strategy to this weekend's NRL fixtures and outputs
a betting card with Kelly-sized stakes for a given bankroll.

Usage:
    python src/strategy/weekend_picks.py --bankroll 100
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Strategy parameters (must match venue_bias.py)
# ---------------------------------------------------------------------------
BACK_HOME_VENUES = {
    "AAMI Park",
    "Olympic Park Stadium",
    "Queensland Sport and Athletics Centre",
    "Sydney Showground",
}

FADE_HOME_VENUES = {
    "Campbelltown Sports Stadium",
    # Cbus Super Stadium removed — insufficient edge vs bookmaker margin
}

# Venue baselines from full dataset (1998–2025)
VENUE_BASELINES = {
    "AAMI Park":                              0.760,
    "Olympic Park Stadium":                   0.765,
    "Queensland Sport and Athletics Centre":  0.754,
    "Sydney Showground":                      0.657,
    "Campbelltown Sports Stadium":            0.379,
}

MIN_EDGE   = 0.05
MIN_ODDS   = 1.50
MAX_ODDS   = 6.00
KELLY_FRAC = 0.25   # quarter Kelly


def kelly_stake(edge: float, odds: float, bankroll: float) -> float:
    p = (1 / odds) + edge
    q = 1 - p
    b = odds - 1
    kelly = (b * p - q) / b
    return max(0.0, round(kelly * KELLY_FRAC * bankroll, 2))


def expected_value(edge: float, odds: float, stake: float) -> float:
    """Expected profit on this bet."""
    p = (1 / odds) + edge
    return round((odds - 1) * p * stake - (1 - p) * stake, 2)


def analyse_fixtures(fixtures: list[dict], bankroll: float) -> list[dict]:
    picks = []
    for f in fixtures:
        venue = f["venue"]
        home_odds = f["home_odds"]
        away_odds = f["away_odds"]
        base_hw = VENUE_BASELINES.get(venue)

        if base_hw is None:
            continue  # venue not in strategy

        implied_home = 1 / home_odds
        implied_away = 1 / away_odds
        edge_back_home = base_hw - implied_home
        edge_fade_home = (1 - base_hw) - implied_away

        if venue in BACK_HOME_VENUES and edge_back_home >= MIN_EDGE:
            if MIN_ODDS <= home_odds <= MAX_ODDS:
                stake = kelly_stake(edge_back_home, home_odds, bankroll)
                picks.append({
                    **f,
                    "bet_type":      "Back Home",
                    "bet_on":        f["home_team"],
                    "odds":          home_odds,
                    "base_hw_rate":  base_hw,
                    "implied_prob":  round(implied_home, 4),
                    "edge":          round(edge_back_home, 4),
                    "stake":         stake,
                    "expected_profit": expected_value(edge_back_home, home_odds, stake),
                })

        elif venue in FADE_HOME_VENUES and edge_fade_home >= MIN_EDGE:
            if MIN_ODDS <= away_odds <= MAX_ODDS:
                stake = kelly_stake(edge_fade_home, away_odds, bankroll)
                picks.append({
                    **f,
                    "bet_type":      "Fade Home (Back Away)",
                    "bet_on":        f["away_team"],
                    "odds":          away_odds,
                    "base_hw_rate":  base_hw,
                    "implied_prob":  round(implied_away, 4),
                    "edge":          round(edge_fade_home, 4),
                    "stake":         stake,
                    "expected_profit": expected_value(edge_fade_home, away_odds, stake),
                })

    return picks


def write_report(fixtures: list[dict], picks: list[dict], bankroll: float, output_path: Path):
    now = datetime.now().strftime("%d %B %Y, %I:%M %p")
    total_staked = sum(p["stake"] for p in picks)
    total_ev = sum(p["expected_profit"] for p in picks)

    lines = [
        "=" * 62,
        "  NRL WEEKEND BETTING CARD",
        f"  Generated: {now}",
        f"  Bankroll:  ${bankroll:,.0f}   |   Strategy: Venue Bias (Quarter Kelly)",
        "=" * 62,
        "",
        "STRATEGY RULES",
        "-" * 62,
        "  Back home team at venues with historically elevated home win",
        "  rate when bookmaker odds imply probability below venue base",
        "  rate minus minimum edge threshold (5%).",
        "",
        "  Fade home team at venues where home team historically",
        "  underperforms vs market-implied probability.",
        "",
        f"  Min edge: {MIN_EDGE:.0%}  |  Odds range: ${MIN_ODDS}–${MAX_ODDS}  |  Stake: ¼ Kelly",
        "",
    ]

    # All fixtures
    lines += [
        "ROUND 7 FIXTURES — STRATEGY SCAN",
        "-" * 62,
        f"  {'Match':<44} {'Venue':<32} {'Status'}",
        f"  {'-'*44} {'-'*32} {'-'*12}",
    ]
    for f in fixtures:
        match_str = f"{f['home_team']} vs {f['away_team']}"
        in_strategy = f["venue"] in (BACK_HOME_VENUES | FADE_HOME_VENUES)
        status = "*** QUALIFIES ***" if any(p["date"] == f["date"] and p["home_team"] == f["home_team"] for p in picks) else ("strategy venue" if in_strategy else "no action")
        lines.append(f"  {match_str:<44} {f['venue']:<32} {status}")

    lines += [""]

    if picks:
        lines += [
            "RECOMMENDED BETS",
            "=" * 62,
        ]
        for i, p in enumerate(picks, 1):
            lines += [
                f"",
                f"  BET #{i}",
                f"  {'Match:':<20} {p['home_team']} vs {p['away_team']}",
                f"  {'Date/Time:':<20} {p['date']} {p['time']} AEST",
                f"  {'Venue:':<20} {p['venue']}",
                f"  {'Bet type:':<20} {p['bet_type']}",
                f"  {'Back:':<20} {p['bet_on']}",
                f"  {'Odds:':<20} ${p['odds']:.2f}",
                f"  {'Venue base HW rate:':<20} {p['base_hw_rate']:.1%}",
                f"  {'Implied prob (mkt):':<20} {p['implied_prob']:.1%}",
                f"  {'Edge:':<20} {p['edge']:.1%}",
                f"  {'Stake (¼ Kelly):':<20} ${p['stake']:.2f}",
                f"  {'Expected profit:':<20} ${p['expected_profit']:.2f}",
            ]
        lines += [
            "",
            "-" * 62,
            f"  Total staked this weekend:  ${total_staked:.2f} of ${bankroll:.0f} bankroll ({total_staked/bankroll:.1%})",
            f"  Total expected profit:      ${total_ev:.2f}",
            f"  Remaining in reserve:       ${bankroll - total_staked:.2f}",
        ]
    else:
        lines += [
            "NO QUALIFYING BETS THIS WEEKEND",
            "-" * 62,
            "  None of this weekend's fixtures are at strategy venues,",
            "  or no match meets the minimum edge threshold.",
        ]

    lines += [
        "",
        "=" * 62,
        "DISCLAIMER",
        "-" * 62,
        "  This output is generated by a statistical backtesting model.",
        "  Past performance does not guarantee future results.",
        "  Bet responsibly. If gambling is causing harm, call the",
        "  National Gambling Helpline: 1800 858 858.",
        "=" * 62,
    ]

    output_path.write_text("\n".join(lines))
    print("\n".join(lines))
    print(f"\nSaved to: {output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bankroll", type=float, default=100.0)
    args = parser.parse_args()

    # -----------------------------------------------------------------------
    # Round 7, 2026 fixtures (from ESPN / NRL.com, fetched 2026-04-17)
    # -----------------------------------------------------------------------
    fixtures = [
        {
            "date": "Thu 16 Apr", "time": "7:50pm",
            "home_team": "North Queensland Cowboys", "away_team": "Manly Warringah Sea Eagles",
            "venue": "Queensland Country Bank Stadium",
            "home_odds": 1.57, "away_odds": 2.35,
            "note": "Already played",
        },
        {
            "date": "Fri 17 Apr", "time": "6:00pm",
            "home_team": "Canberra Raiders", "away_team": "Melbourne Storm",
            "venue": "GIO Stadium",
            "home_odds": 2.10, "away_odds": 1.72,
            "note": "",
        },
        {
            "date": "Fri 17 Apr", "time": "8:00pm",
            "home_team": "Dolphins", "away_team": "Penrith Panthers",
            "venue": "TIO Stadium",
            "home_odds": 4.30, "away_odds": 1.20,
            "note": "",
        },
        {
            "date": "Sat 18 Apr", "time": "3:00pm",
            "home_team": "New Zealand Warriors", "away_team": "Gold Coast Titans",
            "venue": "Go Media Stadium",
            "home_odds": 1.30, "away_odds": 3.50,
            "note": "",
        },
        {
            "date": "Sat 18 Apr", "time": "5:30pm",
            "home_team": "South Sydney Rabbitohs", "away_team": "St George Illawarra Dragons",
            "venue": "Accor Stadium",
            "home_odds": 1.23, "away_odds": 4.00,
            "note": "",
        },
        {
            "date": "Sat 18 Apr", "time": "7:35pm",
            "home_team": "Wests Tigers", "away_team": "Brisbane Broncos",
            "venue": "Campbelltown Sports Stadium",
            "home_odds": 1.53, "away_odds": 2.45,
            "note": "",
        },
        {
            "date": "Sun 19 Apr", "time": "2:00pm",
            "home_team": "Sydney Roosters", "away_team": "Newcastle Knights",
            "venue": "Allianz Stadium",
            "home_odds": 1.33, "away_odds": 3.20,
            "note": "",
        },
        {
            "date": "Sun 19 Apr", "time": "4:05pm",
            "home_team": "Parramatta Eels", "away_team": "Canterbury Bankstown Bulldogs",
            "venue": "CommBank Stadium",
            "home_odds": 3.70, "away_odds": 1.27,
            "note": "",
        },
    ]

    picks = analyse_fixtures(fixtures, args.bankroll)

    output_path = ROOT / "data" / "processed" / "weekend_picks_r7_2026.txt"
    write_report(fixtures, picks, args.bankroll, output_path)


if __name__ == "__main__":
    main()
