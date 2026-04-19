"""
Weekend Picks Generator
Applies the venue bias strategy to this weekend's NRL fixtures,
fetches live rain forecasts for qualifying venues, and outputs
a betting card with Kelly-sized stakes.

Usage:
    python src/strategy/weekend_picks.py --bankroll 113.04 --round 8 --season 2026
"""

import argparse
import json
import time
import urllib.request
from datetime import datetime, date
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
}

VENUE_BASELINES = {
    "AAMI Park":                              0.760,
    "Olympic Park Stadium":                   0.765,
    "Queensland Sport and Athletics Centre":  0.754,
    "Sydney Showground":                      0.657,
    "Campbelltown Sports Stadium":            0.379,
}

VENUE_COORDS = {
    "AAMI Park":                               (-37.8200, 144.9830),
    "Olympic Park Stadium":                    (-37.8200, 144.9830),
    "Queensland Sport and Athletics Centre":   (-27.5005, 153.0144),
    "Sydney Showground":                       (-33.8468, 151.0630),
    "Campbelltown Sports Stadium":             (-34.0744, 150.8144),
    "GIO Stadium":                             (-35.2041, 149.1369),
    "Suncorp Stadium":                         (-27.4649, 153.0097),
    "Accor Stadium":                           (-33.8468, 151.0630),
    "Allianz Stadium":                         (-33.8914, 151.2246),
    "CommBank Stadium":                        (-33.8136, 151.0034),
    "4 Pines Park":                            (-33.7969, 151.2876),
    "McDonald Jones Stadium":                  (-32.9283, 151.7817),
    "Go Media Stadium":                        (-36.9241, 174.7301),
    "TIO Stadium":                             (-12.3921, 130.8776),
    "Queensland Country Bank Stadium":         (-19.2576, 146.8178),
    "BlueBet Stadium":                         (-33.7507, 150.6941),
    "Leichhardt Oval":                         (-33.8824, 151.1557),
    "Netstrata Jubilee Stadium":               (-33.9668, 151.1584),
    "Industree Group Stadium":                 (-33.4201, 151.3424),
    "Sharks Stadium":                          (-34.0543, 151.1033),
    "WIN Stadium":                             (-34.4278, 150.8936),
}

# Weather thresholds (from Agent 2 findings)
WET_THRESHOLD_MM   = 5.0    # mm precipitation = wet game
WET_SCORE_IMPACT   = -5.6   # points suppressed in wet conditions (p=0.0001)

MIN_EDGE   = 0.05
MIN_ODDS   = 1.50
MAX_ODDS   = 6.00
KELLY_FRAC = 0.25


# ---------------------------------------------------------------------------
# Weather forecast
# ---------------------------------------------------------------------------

def fetch_rain_forecast(lat: float, lon: float, game_date: str) -> dict | None:
    """Fetch precipitation forecast from Open-Meteo for a given date and location."""
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=precipitation_sum,weathercode"
        f"&start_date={game_date}&end_date={game_date}"
        f"&timezone=auto"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        precip = data["daily"]["precipitation_sum"][0]
        code   = data["daily"]["weathercode"][0]
        return {
            "precipitation_mm": precip or 0.0,
            "weather_code": code,
            "wet": (precip or 0.0) >= WET_THRESHOLD_MM,
        }
    except Exception:
        return None


def weather_description(code: int | None) -> str:
    if code is None:
        return "Unknown"
    if code == 0:   return "Clear"
    if code <= 3:   return "Partly cloudy"
    if code <= 48:  return "Foggy/overcast"
    if code <= 57:  return "Drizzle"
    if code <= 67:  return "Rain"
    if code <= 77:  return "Snow/sleet"
    if code <= 82:  return "Rain showers"
    if code <= 99:  return "Thunderstorm"
    return "Unknown"


# ---------------------------------------------------------------------------
# Strategy
# ---------------------------------------------------------------------------

def kelly_stake(edge: float, odds: float, bankroll: float) -> float:
    p = (1 / odds) + edge
    q = 1 - p
    b = odds - 1
    kelly = (b * p - q) / b
    return max(0.0, round(kelly * KELLY_FRAC * bankroll, 2))


def expected_value(edge: float, odds: float, stake: float) -> float:
    p = (1 / odds) + edge
    return round((odds - 1) * p * stake - (1 - p) * stake, 2)


def parse_game_date(date_str: str) -> str | None:
    """Convert 'Sat 25 Apr' to '2026-04-25' for API calls."""
    try:
        parts = date_str.strip().split()
        day   = int(parts[1])
        month = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
                 "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}[parts[2]]
        return date(datetime.now().year, month, day).strftime("%Y-%m-%d")
    except Exception:
        return None


def analyse_fixtures(fixtures: list[dict], bankroll: float) -> list[dict]:
    picks = []
    for f in fixtures:
        venue     = f["venue"]
        home_odds = f["home_odds"]
        away_odds = f["away_odds"]
        base_hw   = VENUE_BASELINES.get(venue)

        if base_hw is None:
            continue

        implied_home   = 1 / home_odds
        implied_away   = 1 / away_odds
        edge_back_home = base_hw - implied_home
        edge_fade_home = (1 - base_hw) - implied_away

        if venue in BACK_HOME_VENUES and edge_back_home >= MIN_EDGE:
            if MIN_ODDS <= home_odds <= MAX_ODDS:
                stake = kelly_stake(edge_back_home, home_odds, bankroll)
                picks.append({
                    **f,
                    "bet_type":        "Back Home",
                    "bet_on":          f["home_team"],
                    "odds":            home_odds,
                    "base_hw_rate":    base_hw,
                    "implied_prob":    round(implied_home, 4),
                    "edge":            round(edge_back_home, 4),
                    "stake":           stake,
                    "expected_profit": expected_value(edge_back_home, home_odds, stake),
                })

        elif venue in FADE_HOME_VENUES and edge_fade_home >= MIN_EDGE:
            if MIN_ODDS <= away_odds <= MAX_ODDS:
                stake = kelly_stake(edge_fade_home, away_odds, bankroll)
                picks.append({
                    **f,
                    "bet_type":        "Fade Home (Back Away)",
                    "bet_on":          f["away_team"],
                    "odds":            away_odds,
                    "base_hw_rate":    base_hw,
                    "implied_prob":    round(implied_away, 4),
                    "edge":            round(edge_fade_home, 4),
                    "stake":           stake,
                    "expected_profit": expected_value(edge_fade_home, away_odds, stake),
                })

    return picks


def enrich_with_weather(fixtures: list[dict]) -> list[dict]:
    """Add weather forecast to every fixture with known coordinates."""
    print("  Fetching weather forecasts...")
    enriched = []
    seen_coords = {}
    for f in fixtures:
        coords = VENUE_COORDS.get(f["venue"])
        game_date = parse_game_date(f["date"])
        weather = None
        if coords and game_date:
            key = (coords, game_date)
            if key not in seen_coords:
                seen_coords[key] = fetch_rain_forecast(coords[0], coords[1], game_date)
                time.sleep(0.3)
            weather = seen_coords[key]
        enriched.append({**f, "weather": weather})
    return enriched


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_report(fixtures: list[dict], picks: list[dict],
                 bankroll: float, round_num: int, output_path: Path):
    now          = datetime.now().strftime("%d %B %Y, %I:%M %p")
    total_staked = sum(p["stake"] for p in picks)
    total_ev     = sum(p["expected_profit"] for p in picks)

    lines = [
        "=" * 62,
        "  NRL WEEKEND BETTING CARD",
        f"  Generated: {now}",
        f"  Round: {round_num}  |  Bankroll: ${bankroll:,.2f}  |  ¼ Kelly staking",
        "=" * 62,
        "",
        "STRATEGY RULES",
        "-" * 62,
        "  Back home at venues with elevated historical HW rate when",
        "  bookmaker odds imply prob < (venue base rate − 5%).",
        "  Fade home at venues where home team chronically underperforms.",
        f"  Min edge: {MIN_EDGE:.0%}  |  Odds: ${MIN_ODDS}–${MAX_ODDS}  |  Stake: ¼ Kelly",
        "",
        "WEATHER KEY",
        "-" * 62,
        f"  Wet (>{WET_THRESHOLD_MM:.0f}mm) suppresses total score by ~{abs(WET_SCORE_IMPACT):.1f} pts (p=0.0001).",
        "  Consider backing UNDERS on total points line in wet games.",
        "",
    ]

    # Fixture scan
    lines += [
        f"ROUND {round_num} FIXTURES — STRATEGY SCAN",
        "-" * 62,
        f"  {'Match':<40} {'Venue':<28} {'Weather':<14} {'Status'}",
        f"  {'-'*40} {'-'*28} {'-'*14} {'-'*16}",
    ]
    for f in fixtures:
        match_str  = f"{f['home_team']} vs {f['away_team']}"
        w          = f.get("weather")
        if w:
            wx_str = f"{w['precipitation_mm']:.1f}mm {'WET' if w['wet'] else 'dry'}"
        else:
            wx_str = "N/A"
        qualified  = any(p["home_team"] == f["home_team"] and p["date"] == f["date"] for p in picks)
        in_strat   = f["venue"] in (BACK_HOME_VENUES | FADE_HOME_VENUES)
        if qualified:
            status = "*** QUALIFIES ***"
        elif in_strat:
            # Explain why it didn't qualify
            base = VENUE_BASELINES.get(f["venue"], 0)
            impl = 1 / f["home_odds"]
            edge = base - impl
            if f["venue"] in BACK_HOME_VENUES:
                status = f"strat venue (edge {edge:+.1%})"
            else:
                impl_a = 1 / f["away_odds"]
                edge_a = (1 - base) - impl_a
                status = f"strat venue (edge {edge_a:+.1%})"
        else:
            status = "no action"
        lines.append(f"  {match_str:<40} {f['venue']:<28} {wx_str:<14} {status}")

    lines += [""]

    if picks:
        lines += ["RECOMMENDED BETS", "=" * 62]
        for i, p in enumerate(picks, 1):
            w = p.get("weather")
            wet_flag = ""
            if w and w["wet"]:
                wet_flag = f"  *** WET CONDITIONS ({w['precipitation_mm']:.1f}mm forecast) — consider UNDERS on total points ***"
            lines += [
                "",
                f"  BET #{i}",
                f"  {'Match:':<22} {p['home_team']} vs {p['away_team']}",
                f"  {'Date/Time:':<22} {p['date']} {p['time']} AEST",
                f"  {'Venue:':<22} {p['venue']}",
                f"  {'Bet type:':<22} {p['bet_type']}",
                f"  {'Back:':<22} {p['bet_on']}",
                f"  {'Odds:':<22} ${p['odds']:.2f}",
                f"  {'Venue base HW rate:':<22} {p['base_hw_rate']:.1%}",
                f"  {'Market implied prob:':<22} {p['implied_prob']:.1%}",
                f"  {'Edge:':<22} {p['edge']:.1%}",
                f"  {'Stake (¼ Kelly):':<22} ${p['stake']:.2f}",
                f"  {'Expected profit:':<22} ${p['expected_profit']:.2f}",
            ]
            if wet_flag:
                lines.append(wet_flag)
        lines += [
            "",
            "-" * 62,
            f"  Total staked:    ${total_staked:.2f} of ${bankroll:.2f} ({total_staked/bankroll:.1%})",
            f"  Expected profit: ${total_ev:.2f}",
            f"  In reserve:      ${bankroll - total_staked:.2f}",
        ]
    else:
        lines += [
            "NO QUALIFYING BETS THIS ROUND",
            "-" * 62,
            "  No fixtures at strategy venues with sufficient edge.",
            "",
            "STRATEGY VENUE NOTES",
            "-" * 62,
        ]
        for f in fixtures:
            if f["venue"] in (BACK_HOME_VENUES | FADE_HOME_VENUES):
                base = VENUE_BASELINES.get(f["venue"], 0)
                if f["venue"] in BACK_HOME_VENUES:
                    impl = 1 / f["home_odds"]
                    edge = base - impl
                    lines.append(f"  {f['home_team']} (home) at {f['venue']}: edge {edge:+.1%} — need >{MIN_EDGE:.0%}")
                else:
                    impl = 1 / f["away_odds"]
                    edge = (1 - base) - impl
                    lines.append(f"  Fade {f['home_team']} at {f['venue']}: edge {edge:+.1%} — need >{MIN_EDGE:.0%}")

    lines += [
        "",
        "=" * 62,
        "DISCLAIMER",
        "-" * 62,
        "  Statistical model only. Bet responsibly.",
        "  National Gambling Helpline: 1800 858 858.",
        "=" * 62,
    ]

    output_path.write_text("\n".join(lines))
    print("\n".join(lines))
    print(f"\nSaved to: {output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bankroll", type=float, default=100.0)
    parser.add_argument("--round",    type=int,   default=8)
    parser.add_argument("--season",   type=int,   default=2026)
    args = parser.parse_args()

    # -------------------------------------------------------------------------
    # Round 8, 2026 — ANZAC Round (fixtures from ESPN/NRL.com, 2026-04-19)
    # Odds sourced from current market
    # -------------------------------------------------------------------------
    fixtures = [
        {
            "date": "Thu 23 Apr", "time": "7:50pm",
            "home_team": "Wests Tigers", "away_team": "Canberra Raiders",
            "venue": "Leichhardt Oval",
            "home_odds": 2.10, "away_odds": 1.72,
        },
        {
            "date": "Fri 24 Apr", "time": "6:00pm",
            "home_team": "North Queensland Cowboys", "away_team": "Cronulla Sutherland Sharks",
            "venue": "Queensland Country Bank Stadium",
            "home_odds": 1.65, "away_odds": 2.20,
        },
        {
            "date": "Fri 24 Apr", "time": "8:00pm",
            "home_team": "Brisbane Broncos", "away_team": "Canterbury Bankstown Bulldogs",
            "venue": "Suncorp Stadium",
            "home_odds": 1.50, "away_odds": 2.55,
        },
        {
            "date": "Sat 25 Apr", "time": "4:05pm",
            "home_team": "St George Illawarra Dragons", "away_team": "Sydney Roosters",
            "venue": "Allianz Stadium",
            "home_odds": 3.20, "away_odds": 1.33,
        },
        {
            "date": "Sat 25 Apr", "time": "6:05pm",
            "home_team": "New Zealand Warriors", "away_team": "Dolphins",
            "venue": "Go Media Stadium",
            "home_odds": 1.55, "away_odds": 2.40,
        },
        {
            "date": "Sat 25 Apr", "time": "8:10pm",
            "home_team": "Melbourne Storm", "away_team": "South Sydney Rabbitohs",
            "venue": "AAMI Park",
            "home_odds": 1.20, "away_odds": 4.50,
        },
        {
            "date": "Sun 26 Apr", "time": "2:00pm",
            "home_team": "Newcastle Knights", "away_team": "Penrith Panthers",
            "venue": "McDonald Jones Stadium",
            "home_odds": 2.60, "away_odds": 1.50,
        },
        {
            "date": "Sun 26 Apr", "time": "4:05pm",
            "home_team": "Manly Warringah Sea Eagles", "away_team": "Parramatta Eels",
            "venue": "4 Pines Park",
            "home_odds": 1.72, "away_odds": 2.10,
        },
    ]

    fixtures = enrich_with_weather(fixtures)
    picks    = analyse_fixtures(fixtures, args.bankroll)

    output_path = ROOT / "data" / "processed" / f"weekend_picks_r{args.round}_{args.season}.txt"
    write_report(fixtures, picks, args.bankroll, args.round, output_path)


if __name__ == "__main__":
    main()
