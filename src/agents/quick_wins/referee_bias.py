"""
Agent 4: Referee Bias
=====================
Tests whether individual NRL referees produce significantly different
home win rates, and whether referee assignment is exploitable.

Evidence base: Peer-reviewed research (Frontiers in Sports, 2021) shows
NRL referees exhibit systematic home advantage bias. Experience reduces
but does not eliminate it.

Data source: NRL referee assignments scraped from NRL.com match centre.
Falls back to uselessnrlstats match_info.csv if referee column present.

Outputs:
  data/processed/quick_wins/referee_findings.md
  data/processed/quick_wins/referee_stats.csv
  Returns result dict consumed by coordinator.
"""

import time
import json
import urllib.request
import urllib.parse
import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path

ROOT      = Path(__file__).resolve().parents[3]
PROCESSED = ROOT / "data" / "processed"
RAW       = ROOT / "data" / "raw"
OUT       = PROCESSED / "quick_wins"
OUT.mkdir(parents=True, exist_ok=True)

MIN_GAMES = 20   # minimum games for a referee to be included in analysis


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_nrl_clean() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED / "nrl_clean.csv", parse_dates=["date"])
    df["home_win"] = (df["result"] == "home_win").astype(int)
    return df


def load_referee_data_from_uselessnrlstats() -> pd.DataFrame | None:
    """Check if match_info.csv has a referee column."""
    path = RAW / "uselessnrlstats" / "match_info.csv"
    if not path.exists():
        return None
    mi = pd.read_csv(path)
    ref_cols = [c for c in mi.columns if "ref" in c.lower()]
    if not ref_cols:
        return None
    print(f"  Found referee columns in match_info.csv: {ref_cols}")
    return mi[["match_id"] + ref_cols]


def fetch_nrl_com_referee(season: int, round_num: int, match_id: str,
                           retries: int = 3) -> str | None:
    """
    Attempt to fetch referee name from NRL.com match centre API.
    Returns referee name string or None.
    """
    url = f"https://www.nrl.com/draw/nrl-premiership/{season}/round-{round_num}/{match_id}/"
    headers = {"User-Agent": "Mozilla/5.0 (research project)"}
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
            # Look for referee name in page content
            for marker in ['"referee":', '"Referee":', 'referee":']:
                idx = html.find(marker)
                if idx > -1:
                    snippet = html[idx:idx+80]
                    # Extract value between quotes after colon
                    import re
                    m = re.search(r'["\']([A-Z][a-z]+ [A-Z][a-z]+)["\']', snippet)
                    if m:
                        return m.group(1)
            return None
        except Exception:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    return None


def scrape_referees_sample(df: pd.DataFrame, max_seasons: int = 5) -> pd.DataFrame:
    """
    Scrape referee assignments for recent seasons from NRL.com.
    Limited to recent seasons to keep runtime reasonable.
    Returns dataframe with match_id, referee columns.
    """
    recent = df[df["season"] >= df["season"].max() - max_seasons + 1].copy()
    print(f"  Attempting to scrape referees for {len(recent)} recent matches...")

    referees = []
    for i, (_, row) in enumerate(recent.iterrows()):
        if i % 50 == 0:
            print(f"    Progress: {i}/{len(recent)}")
        ref = fetch_nrl_com_referee(
            int(row["season"]),
            int(str(row.get("round", 1)).replace("Round ", "").replace("round-", "").strip() or 1),
            str(row.get("match_id", ""))
        )
        referees.append({"match_id": row.get("match_id"), "referee": ref})
        time.sleep(0.5)

    return pd.DataFrame(referees)


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyse_referees(df: pd.DataFrame) -> dict:
    """Core analysis: referee effect on home win rate."""
    results = {}
    overall_hw = df["home_win"].mean()
    results["overall_hw"] = overall_hw
    results["n_total"] = len(df)

    if "referee" not in df.columns or df["referee"].isna().all():
        results["error"] = "No referee data available"
        return results

    # Filter to referees with sufficient sample
    ref_groups = df.groupby("referee")["home_win"].agg(["mean", "count", "sum"])
    ref_groups.columns = ["hw_rate", "n_games", "n_hw"]
    ref_groups = ref_groups[ref_groups["n_games"] >= MIN_GAMES].sort_values("hw_rate", ascending=False)
    results["ref_table"] = ref_groups

    if len(ref_groups) < 3:
        results["error"] = f"Only {len(ref_groups)} referees with {MIN_GAMES}+ games — need more data"
        return results

    # ANOVA: does referee assignment significantly affect home win rate?
    groups = [
        df[df["referee"] == ref]["home_win"].values
        for ref in ref_groups.index
    ]
    f_stat, p_anova = stats.f_oneway(*groups)
    results["anova"] = {"f": f_stat, "p": p_anova, "significant": p_anova < 0.05}

    # Per-referee t-test vs overall
    sig_refs = []
    for ref, row in ref_groups.iterrows():
        grp = df[df["referee"] == ref]["home_win"]
        t, p = stats.ttest_1samp(grp, overall_hw)
        if p < 0.10:
            sig_refs.append({
                "referee": ref,
                "hw_rate": row["hw_rate"],
                "n": int(row["n_games"]),
                "direction": "↑ favours home" if row["hw_rate"] > overall_hw else "↓ favours away",
                "p": p,
            })
    results["significant_refs"] = sig_refs

    # Home penalty advantage correlation (proxy: use margin as signal)
    if "margin" in df.columns:
        # Higher margin when ref assigned → suggests home team benefiting more
        ref_margin = df.groupby("referee")["margin"].mean().reset_index()
        ref_margin.columns = ["referee", "avg_margin"]
        results["ref_margin"] = ref_margin

    return results


def analyse_without_referee_data(df: pd.DataFrame) -> dict:
    """
    Proxy analysis when no referee data available.
    Uses penalty proxy: home margin variance by round/season as indirect signal.
    Also analyses penalty statistics if available in data.
    """
    results = {"proxy_only": True}
    overall_hw = df["home_win"].mean()

    # Home advantage trend over seasons — is it stable or changing?
    season_hw = df.groupby("season")["home_win"].agg(["mean", "count"])
    season_hw.columns = ["hw_rate", "n"]
    results["season_trend"] = season_hw

    # Linear trend in home advantage over time
    seasons = season_hw.index.values
    hw_rates = season_hw["hw_rate"].values
    if len(seasons) > 5:
        slope, intercept, r, p, _ = stats.linregress(seasons, hw_rates)
        results["trend"] = {
            "slope": slope,
            "r": r,
            "p": p,
            "significant": p < 0.05,
            "direction": "increasing" if slope > 0 else "decreasing",
        }

    # Home advantage by day of week (referees may differ weekday vs weekend)
    df2 = df.copy()
    df2["day_of_week"] = df2["date"].dt.day_name()
    dow_hw = df2.groupby("day_of_week")["home_win"].agg(["mean", "count"])
    dow_hw.columns = ["hw_rate", "n"]
    results["dow_hw"] = dow_hw

    # Home advantage by era (could reflect referee rule changes)
    df2["era"] = pd.cut(df2["season"],
                        bins=[1997, 2003, 2010, 2017, 2026],
                        labels=["1998–2003", "2004–2010", "2011–2017", "2018–2026"])
    era_hw = df2.groupby("era", observed=True)["home_win"].agg(["mean", "count"])
    era_hw.columns = ["hw_rate", "n"]
    results["era_hw"] = era_hw

    # Margin analysis — home advantage size over time
    season_margin = df.groupby("season")["margin"].mean()
    results["season_margin"] = season_margin

    return results


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_findings(results: dict, has_ref_data: bool) -> str:
    lines = [
        "# Agent 4 — Referee Bias Findings\n",
        f"Dataset: {results.get('n_total', '?'):,} matches\n",
        "## Evidence Base",
        "Frontiers in Sports (2021, peer-reviewed): NRL referees exhibit systematic",
        "home advantage bias. Tier-1 refs (300+ games) show less bias but never zero.",
        "Effect size: ~0.5 points per penalty advantage.\n",
        "---\n",
    ]

    if "error" in results:
        lines += [
            f"## Data Status\n{results['error']}\n",
            "### Proxy Analysis\n",
        ]

    # Proxy analysis (always available)
    if "season_trend" in results:
        lines += [
            "## Home Win Rate by Season",
            results["season_trend"].to_string(),
            "",
        ]
    if "trend" in results:
        t = results["trend"]
        lines += [
            "## Long-run Home Advantage Trend",
            f"- Slope: {t['slope']:+.4f} per season ({t['direction']})",
            f"- r={t['r']:.3f}, p={t['p']:.4f} — {'**SIGNIFICANT**' if t['significant'] else 'not significant'}",
            "",
        ]
    if "era_hw" in results:
        lines += [
            "## Home Win Rate by Era (referee rule changes)",
            results["era_hw"].to_string(),
            "",
        ]
    if "dow_hw" in results:
        lines += [
            "## Home Win Rate by Day of Week",
            results["dow_hw"].sort_values("hw_rate", ascending=False).to_string(),
            "",
        ]
    if "season_margin" in results:
        lines += [
            "## Average Home Margin by Season",
            results["season_margin"].to_string(),
            "",
        ]

    # Referee-specific analysis (if data available)
    if "anova" in results:
        a = results["anova"]
        lines += [
            "## ANOVA: Referee Effect on Home Win Rate",
            f"F={a['f']:.4f}, p={a['p']:.6f} — {'**SIGNIFICANT**' if a['significant'] else 'not significant'}\n",
        ]
    if "ref_table" in results:
        lines += [
            "## Per-Referee Home Win Rates",
            results["ref_table"].to_string(),
            "",
        ]
    if results.get("significant_refs"):
        lines += ["## Referees Significantly Above/Below Average (p<0.10)"]
        for r in results["significant_refs"]:
            lines.append(f"  {r['referee']}: {r['hw_rate']:.1%} (n={r['n']}) {r['direction']} — p={r['p']:.4f}")
        lines.append("")

    # How to get real referee data
    lines += [
        "---\n",
        "## How to Get Full Referee Data",
        "1. **NRL.com API** — each match page contains referee name in JSON.",
        "   Run `fetch_nrl_com_referee()` across all match IDs (rate limited, ~1 req/sec).",
        "2. **NRL Premiership data** — NRL official stats hub sometimes includes referee.",
        "3. **Manual collection** — for seasons 2009–2020, ref data may require scraping",
        "   historical match reports.",
        "",
        "Once referee data is collected, re-run this agent for full ANOVA analysis.",
        "",
        "---\n",
        "## Recommendation",
    ]

    any_sig = (
        results.get("anova", {}).get("significant", False) or
        bool(results.get("significant_refs")) or
        results.get("trend", {}).get("significant", False)
    )

    if any_sig:
        lines.append("**INTEGRATE** — significant referee or trend effect found; add as confidence modifier.")
    else:
        lines.append("**PARTIAL** — proxy analysis complete; collect referee assignment data to confirm full signal.")

    text = "\n".join(lines)
    (OUT / "referee_findings.md").write_text(text)
    return text


def run() -> dict:
    print("\n[Agent 4] Referee Bias — starting...")
    df = load_nrl_clean()

    # Try to get referee data from existing sources first
    ref_data = load_referee_data_from_uselessnrlstats()
    has_ref_data = False

    if ref_data is not None and not ref_data.empty:
        print(f"  Found referee data: {len(ref_data)} rows")
        df = df.merge(ref_data, on="match_id", how="left")
        # Normalise column name
        ref_col = [c for c in df.columns if "ref" in c.lower() and c != "result"][0]
        df = df.rename(columns={ref_col: "referee"})
        has_ref_data = True
    else:
        print("  No referee data in local files — running proxy analysis on home advantage trends.")
        df["referee"] = np.nan

    if has_ref_data:
        results = analyse_referees(df)
        # Save ref stats
        if "ref_table" in results:
            results["ref_table"].to_csv(OUT / "referee_stats.csv")
    else:
        results = analyse_without_referee_data(df)

    results["n_total"] = len(df)
    results["overall_hw"] = df["home_win"].mean()

    text = write_findings(results, has_ref_data)
    print(text)

    any_sig = (
        results.get("anova", {}).get("significant", False) or
        bool(results.get("significant_refs")) or
        results.get("trend", {}).get("significant", False)
    )

    return {
        "agent": "referee_bias",
        "significant": any_sig,
        "has_ref_data": has_ref_data,
        "results": results,
        "findings_path": str(OUT / "referee_findings.md"),
        "next_step": "Scrape NRL.com match pages to collect referee assignments for full analysis",
    }


if __name__ == "__main__":
    run()
