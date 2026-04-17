"""
Agent 2: Weather Overlay
========================
Fetches historical daily weather (temperature, precipitation, wind) from
the Open-Meteo free API for each NRL venue, then tests whether conditions
correlate with total scoring and home win rate.

API: https://archive-api.open-meteo.com  (free, no key required)

Outputs:
  data/processed/quick_wins/weather_findings.md
  data/processed/quick_wins/weather_enriched.csv   (match data + weather)
  Returns a result dict consumed by the coordinator.
"""

import time
import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path
import urllib.request
import json

ROOT = Path(__file__).resolve().parents[3]
PROCESSED = ROOT / "data" / "processed"
OUT = PROCESSED / "quick_wins"
OUT.mkdir(parents=True, exist_ok=True)

# Venue lat/lon for Open-Meteo queries
VENUE_COORDS = {
    "AAMI Park":                               (-37.8200, 144.9830),
    "Olympic Park Stadium":                    (-37.8200, 144.9830),
    "Marvel Stadium":                          (-37.8166, 144.9475),
    "GIO Stadium":                             (-35.2041, 149.1369),
    "Canberra Stadium":                        (-35.2041, 149.1369),
    "Suncorp Stadium":                         (-27.4649, 153.0097),
    "Queensland Country Bank Stadium":         (-19.2576, 146.8178),
    "Cbus Super Stadium":                      (-28.0022, 153.4145),
    "Go Media Stadium":                        (-36.9241, 174.7301),
    "Mt Smart Stadium":                        (-36.9241, 174.7301),
    "Accor Stadium":                           (-33.8468, 151.0630),
    "Sydney Football Stadium (Old)":           (-33.8914, 151.2246),
    "Allianz Stadium":                         (-33.8914, 151.2246),
    "CommBank Stadium":                        (-33.8136, 151.0034),
    "Parramatta Stadium":                      (-33.8136, 151.0034),
    "BlueBet Stadium":                         (-33.7507, 150.6941),
    "Campbelltown Sports Stadium":             (-34.0744, 150.8144),
    "Netstrata Jubilee Stadium":               (-33.9668, 151.1584),
    "Sharks Stadium":                          (-34.0543, 151.1033),
    "Leichhardt Oval":                         (-33.8824, 151.1557),
    "Sydney Showground":                       (-33.8468, 151.0630),
    "Sydney Cricket Ground":                   (-33.8914, 151.2246),
    "Industree Group Stadium":                 (-33.4201, 151.3424),
    "WIN Stadium":                             (-34.4278, 150.8936),
    "4 Pines Park":                            (-33.7969, 151.2876),
    "McDonald Jones Stadium":                  (-32.9283, 151.7817),
    "Willows Sports Complex":                  (-23.3489, 150.5142),
    "Queensland Sport and Athletics Centre":   (-27.5005, 153.0144),
    "TIO Stadium":                             (-12.3921, 130.8776),
    "TIO Traeger Park":                        (-23.6980, 133.8807),
    "Kayo Stadium":                            (-26.6131, 153.0853),
    "Brisbane Stadium":                        (-27.4649, 153.0097),
}


def fetch_weather(lat: float, lon: float, start: str, end: str) -> pd.DataFrame:
    """Fetch daily weather from Open-Meteo archive API."""
    url = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat}&longitude={lon}"
        f"&start_date={start}&end_date={end}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max"
        f"&timezone=auto"
    )
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
        daily = data["daily"]
        df = pd.DataFrame({
            "date":          pd.to_datetime(daily["time"]),
            "temp_max":      daily["temperature_2m_max"],
            "temp_min":      daily["temperature_2m_min"],
            "precipitation": daily["precipitation_sum"],
            "wind_max":      daily["windspeed_10m_max"],
        })
        df["temp_avg"] = (df["temp_max"] + df["temp_min"]) / 2
        return df
    except Exception as e:
        print(f"    Weather fetch failed ({lat},{lon}): {e}")
        return pd.DataFrame()


def build_weather_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Attach weather to every match that has a known venue."""
    df = df.copy()
    df["date_only"] = df["date"].dt.date

    weather_rows = []
    venues_done = {}

    unique_venues = df["venue_name"].dropna().unique()
    print(f"  Fetching weather for {len(unique_venues)} venues...")

    for venue in unique_venues:
        coords = VENUE_COORDS.get(venue)
        if coords is None:
            continue

        lat, lon = coords
        venue_matches = df[df["venue_name"] == venue]
        min_date = venue_matches["date"].min().strftime("%Y-%m-%d")
        max_date = venue_matches["date"].max().strftime("%Y-%m-%d")

        if (lat, lon) in venues_done:
            wdf = venues_done[(lat, lon)]
        else:
            print(f"    {venue} ({lat},{lon}) {min_date}→{max_date}")
            wdf = fetch_weather(lat, lon, min_date, max_date)
            venues_done[(lat, lon)] = wdf
            time.sleep(0.3)   # be polite to free API

        if wdf.empty:
            continue

        wdf["venue_name"] = venue
        weather_rows.append(wdf)

    if not weather_rows:
        print("  No weather data fetched.")
        return df

    weather_all = pd.concat(weather_rows, ignore_index=True)
    weather_all["date_only"] = weather_all["date"].dt.date

    enriched = df.merge(
        weather_all[["date_only", "venue_name", "temp_avg", "precipitation", "wind_max"]],
        on=["date_only", "venue_name"],
        how="left",
    )
    return enriched


def analyse(df: pd.DataFrame) -> dict:
    sub = df[df["temp_avg"].notna()].copy()
    if len(sub) < 50:
        return {"error": "insufficient weather-matched data"}

    sub["home_win"] = (sub["result"] == "home_win").astype(int)
    results = {}

    # ── Temperature vs total score ─────────────────────────────────────────
    r_temp_score, p_temp_score = stats.pearsonr(sub["temp_avg"], sub["total_points"])
    results["temp_vs_score"] = {
        "r": r_temp_score, "p": p_temp_score,
        "significant": p_temp_score < 0.05,
        "direction": "higher temp → more points" if r_temp_score > 0 else "higher temp → fewer points",
    }

    # ── Wet conditions vs total score ──────────────────────────────────────
    sub["wet"] = sub["precipitation"] > 5   # mm threshold
    wet   = sub[sub["wet"]]["total_points"]
    dry   = sub[~sub["wet"]]["total_points"]
    t_wet, p_wet = stats.ttest_ind(wet, dry)
    results["wet_vs_score"] = {
        "n_wet": len(wet), "n_dry": len(dry),
        "avg_wet": wet.mean(), "avg_dry": dry.mean(),
        "t": t_wet, "p": p_wet,
        "significant": p_wet < 0.05,
    }

    # ── Wind vs total score ────────────────────────────────────────────────
    r_wind, p_wind = stats.pearsonr(sub["wind_max"].fillna(0), sub["total_points"])
    results["wind_vs_score"] = {
        "r": r_wind, "p": p_wind,
        "significant": p_wind < 0.05,
        "direction": "more wind → more points" if r_wind > 0 else "more wind → fewer points",
    }

    # ── Weather vs home win rate ───────────────────────────────────────────
    r_temp_hw, p_temp_hw = stats.pointbiserialr(sub["temp_avg"], sub["home_win"])
    results["temp_vs_hw"] = {
        "r": r_temp_hw, "p": p_temp_hw,
        "significant": p_temp_hw < 0.05,
    }

    wet_hw   = sub[sub["wet"]]["home_win"].mean()
    dry_hw   = sub[~sub["wet"]]["home_win"].mean()
    t_wet_hw, p_wet_hw = stats.ttest_ind(sub[sub["wet"]]["home_win"], sub[~sub["wet"]]["home_win"])
    results["wet_vs_hw"] = {
        "wet_hw": wet_hw, "dry_hw": dry_hw,
        "t": t_wet_hw, "p": p_wet_hw,
        "significant": p_wet_hw < 0.05,
    }

    # ── Cold conditions bucket ─────────────────────────────────────────────
    sub["cold"] = sub["temp_avg"] < 12
    cold_score = sub[sub["cold"]]["total_points"]
    warm_score = sub[~sub["cold"]]["total_points"]
    if len(cold_score) > 10:
        t_cold, p_cold = stats.ttest_ind(cold_score, warm_score)
        results["cold_vs_score"] = {
            "n_cold": len(cold_score), "n_warm": len(warm_score),
            "avg_cold": cold_score.mean(), "avg_warm": warm_score.mean(),
            "t": t_cold, "p": p_cold,
            "significant": p_cold < 0.05,
        }

    results["n_matched"] = len(sub)
    results["matched_df"] = sub
    return results


def write_findings(results: dict, df: pd.DataFrame) -> str:
    if "error" in results:
        text = f"# Agent 2 — Weather Findings\n\nERROR: {results['error']}\n"
        (OUT / "weather_findings.md").write_text(text)
        return text

    ts  = results["temp_vs_score"]
    ws  = results["wet_vs_score"]
    wnd = results["wind_vs_score"]
    thw = results["temp_vs_hw"]
    whw = results["wet_vs_hw"]

    lines = [
        "# Agent 2 — Weather Overlay Findings\n",
        f"Weather-matched matches: {results['n_matched']:,}\n",
        "---\n",
        "## Temperature vs Total Score",
        f"- Pearson r={ts['r']:.4f}, p={ts['p']:.4f} — {'**SIGNIFICANT**' if ts['significant'] else 'not significant'}",
        f"- Direction: {ts['direction']}\n",
        "## Wet Conditions (>5mm precipitation) vs Total Score",
        f"- Wet: {ws['n_wet']} matches, avg score {ws['avg_wet']:.1f}",
        f"- Dry: {ws['n_dry']} matches, avg score {ws['avg_dry']:.1f}",
        f"- Difference: {ws['avg_wet'] - ws['avg_dry']:+.1f} points",
        f"- t={ws['t']:.3f}, p={ws['p']:.4f} — {'**SIGNIFICANT**' if ws['significant'] else 'not significant'}\n",
        "## Wind vs Total Score",
        f"- Pearson r={wnd['r']:.4f}, p={wnd['p']:.4f} — {'**SIGNIFICANT**' if wnd['significant'] else 'not significant'}",
        f"- Direction: {wnd['direction']}\n",
        "## Temperature vs Home Win Rate",
        f"- Pearson r={thw['r']:.4f}, p={thw['p']:.4f} — {'**SIGNIFICANT**' if thw['significant'] else 'not significant'}\n",
        "## Wet Conditions vs Home Win Rate",
        f"- Wet home win rate: {whw['wet_hw']:.1%}  |  Dry: {whw['dry_hw']:.1%}",
        f"- t={whw['t']:.3f}, p={whw['p']:.4f} — {'**SIGNIFICANT**' if whw['significant'] else 'not significant'}\n",
    ]

    if "cold_vs_score" in results:
        cs = results["cold_vs_score"]
        lines += [
            "## Cold (<12°C) vs Total Score",
            f"- Cold: {cs['n_cold']} matches, avg {cs['avg_cold']:.1f}  |  Warm: {cs['n_warm']}, avg {cs['avg_warm']:.1f}",
            f"- t={cs['t']:.3f}, p={cs['p']:.4f} — {'**SIGNIFICANT**' if cs['significant'] else 'not significant'}\n",
        ]

    any_sig = any([ts["significant"], ws["significant"], wnd["significant"]])
    lines += [
        "---\n",
        "## Recommendation",
        "**INTEGRATE** — weather is a significant predictor; add as confidence modifier" if any_sig
        else "**DO NOT INTEGRATE** — weather effects not statistically significant in this dataset",
    ]

    text = "\n".join(lines)
    (OUT / "weather_findings.md").write_text(text)
    return text


def run() -> dict:
    print("\n[Agent 2] Weather Overlay — starting...")
    df = pd.read_csv(PROCESSED / "nrl_clean.csv", parse_dates=["date"])
    df["home_win"] = (df["result"] == "home_win").astype(int)

    enriched = build_weather_dataset(df)

    # Save enriched dataset
    enriched_path = OUT / "weather_enriched.csv"
    enriched.to_csv(enriched_path, index=False)
    print(f"  Weather-enriched dataset saved: {enriched_path}")

    results = analyse(enriched)
    text = write_findings(results, enriched)
    print(text)

    any_sig = "error" not in results and any([
        results.get("temp_vs_score", {}).get("significant", False),
        results.get("wet_vs_score",  {}).get("significant", False),
        results.get("wind_vs_score", {}).get("significant", False),
    ])

    filters = {}
    if "error" not in results:
        wv = results.get("wet_vs_score", {})
        if wv.get("significant") and wv.get("avg_wet", 99) < wv.get("avg_dry", 0):
            filters["wet_suppresses_scoring"] = True
            filters["wet_score_adjustment"] = round(wv["avg_wet"] - wv["avg_dry"], 1)

    return {
        "agent": "weather",
        "significant": any_sig,
        "results": results,
        "filters": filters,
        "findings_path": str(OUT / "weather_findings.md"),
        "enriched_csv": str(enriched_path),
    }


if __name__ == "__main__":
    run()
