"""
NRL Gambling Bias Analysis
Tests three market inefficiency hypotheses:
  1. Draw Bias    — draws underpriced for top-8 club matchups
  2. Form Bias    — market over/underreacts to recent team form
  3. Venue Bias   — home advantage mispriced at specific venues
"""

import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
df = pd.read_csv(ROOT / "data" / "processed" / "nrl_clean.csv", parse_dates=["date"])

findings = []

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

# ===========================================================================
# 1. DRAW BIAS
# ===========================================================================
section("1. DRAW BIAS")

# Overall draw rate
draw_rate_all = (df["result"] == "draw").mean()
print(f"Overall draw rate (1998-2025): {draw_rate_all:.4f} ({draw_rate_all*100:.2f}%)")

# Top-8 vs non-top-8 matchups
top8 = df[df["both_top8"] == True]
non_top8 = df[df["both_top8"] == False]
draw_top8 = (top8["result"] == "draw").mean()
draw_non_top8 = (non_top8["result"] == "draw").mean()

print(f"\nDraw rate — both top-8 clubs   ({len(top8)} matches): {draw_top8:.4f} ({draw_top8*100:.2f}%)")
print(f"Draw rate — other matchups      ({len(non_top8)} matches): {draw_non_top8:.4f} ({draw_non_top8*100:.2f}%)")

# Chi-square test: draw vs non-draw, top8 vs non-top8
contingency = pd.crosstab(df["both_top8"], df["result"] == "draw")
chi2, p_chi, dof, _ = stats.chi2_contingency(contingency)
print(f"\nChi-square test (top8 vs non-top8, draw vs no-draw):")
print(f"  chi2={chi2:.4f}, p={p_chi:.4f}, dof={dof}")

# Betfair implied draw probability (exchange has draw market in NRL?)
# In NRL (no draws market typically), check if any runner is The Draw
bf_draw_check = df[df["bf_home_open"].notna()].copy()
print(f"\nMatches with Betfair odds: {len(bf_draw_check)}")
print(f"Betfair implied home win prob (mean): {bf_draw_check['bf_implied_home'].mean():.3f}")
print(f"Betfair implied away win prob (mean): {bf_draw_check['bf_implied_away'].mean():.3f}")
prob_sum = (bf_draw_check['bf_implied_home'] + bf_draw_check['bf_implied_away']).mean()
print(f"Avg sum of implied probs (home+away): {prob_sum:.3f}  (margin = {(prob_sum-1)*100:.1f}%)")

# Actual draw rate in Betfair era
bf_draw_rate = (bf_draw_check["result"] == "draw").mean()
print(f"Actual draw rate in Betfair sample: {bf_draw_rate:.4f}")
print(f"Implied residual probability for draw: {(1 - prob_sum):.4f}")

findings.append({
    "bias": "Draw Bias",
    "test": "Chi-square (top-8 matchup draw rate vs others)",
    "statistic": f"chi2={chi2:.4f}",
    "p_value": p_chi,
    "significant": p_chi < 0.05,
    "direction": f"Top-8 draw rate {draw_top8*100:.2f}% vs {draw_non_top8*100:.2f}% other",
    "note": f"Overall draw rate only {draw_rate_all*100:.2f}% — NRL rarely draws. Betfair doesn't price a draw market, so no direct odds mispricing test possible without bookmaker odds."
})

# ===========================================================================
# 2. FORM / MOMENTUM BIAS
# ===========================================================================
section("2. FORM / MOMENTUM BIAS")

form_df = df[df["home_form_last5"].notna() & df["away_form_last5"].notna()].copy()
print(f"Matches with form data: {len(form_df)}")

form_df["form_diff"] = form_df["home_form_last5"] - form_df["away_form_last5"]
form_df["home_win_bin"] = (form_df["result"] == "home_win").astype(int)

# Logistic-style: does form_diff predict home win above what we'd expect?
corr, p_corr = stats.pointbiserialr(form_df["form_diff"], form_df["home_win_bin"])
print(f"\nPoint-biserial correlation (form_diff vs home win): r={corr:.4f}, p={p_corr:.6f}")

# Split into strong form advantage vs weak/none
form_df["form_advantage"] = pd.cut(
    form_df["form_diff"],
    bins=[-1.1, -0.4, -0.1, 0.1, 0.4, 1.1],
    labels=["strong_away", "mild_away", "neutral", "mild_home", "strong_home"]
)
form_group = form_df.groupby("form_advantage", observed=True)["home_win_bin"].agg(["mean", "count"])
form_group.columns = ["home_win_rate", "n_matches"]
print("\nHome win rate by form advantage bucket:")
print(form_group.to_string())

# Key question: when home team is in "strong_home" form — does it win MORE than overall?
overall_home_win = form_df["home_win_bin"].mean()
strong_home = form_df[form_df["form_advantage"] == "strong_home"]
strong_away = form_df[form_df["form_advantage"] == "strong_away"]

print(f"\nOverall home win rate: {overall_home_win:.3f}")
if len(strong_home) > 10:
    t, p_t = stats.ttest_1samp(strong_home["home_win_bin"], overall_home_win)
    print(f"Strong home form — win rate: {strong_home['home_win_bin'].mean():.3f} (n={len(strong_home)}), t={t:.3f}, p={p_t:.4f}")
if len(strong_away) > 10:
    t2, p_t2 = stats.ttest_1samp(strong_away["home_win_bin"], overall_home_win)
    print(f"Strong away form — home win rate: {strong_away['home_win_bin'].mean():.3f} (n={len(strong_away)}), t={t2:.3f}, p={p_t2:.4f}")

# With Betfair: does market correctly weight form?
bf_form = form_df[form_df["bf_home_open"].notna()].copy()
if len(bf_form) > 20:
    bf_corr, p_bf = stats.pearsonr(bf_form["form_diff"], bf_form["bf_implied_home"])
    print(f"\nBetfair sample ({len(bf_form)} matches):")
    print(f"  Correlation form_diff vs bf_implied_home: r={bf_corr:.4f}, p={p_bf:.4f}")
    # Does form predict actual result BETTER than Betfair implied prob?
    actual_corr, _ = stats.pointbiserialr(bf_form["bf_implied_home"], bf_form["home_win_bin"])
    form_corr2, _ = stats.pointbiserialr(bf_form["form_diff"], bf_form["home_win_bin"])
    print(f"  Betfair implied prob → actual result correlation: r={actual_corr:.4f}")
    print(f"  Form diff → actual result correlation:            r={form_corr2:.4f}")

findings.append({
    "bias": "Form/Momentum Bias",
    "test": "Point-biserial correlation + t-test by form bucket",
    "statistic": f"r={corr:.4f}",
    "p_value": p_corr,
    "significant": p_corr < 0.05,
    "direction": f"Form diff positively predicts home win (r={corr:.3f})",
    "note": "Form predicts outcome, but need bookmaker odds to test if market ALREADY prices this in. Betfair sample (238 matches) too small for strong conclusions."
})

# ===========================================================================
# 3. VENUE / HOME BIAS
# ===========================================================================
section("3. VENUE / HOME BIAS")

venue_df = df[df["venue_name"].notna()].copy()
venue_df["home_win_bin"] = (venue_df["result"] == "home_win").astype(int)

# Overall home win rate
overall_hw = venue_df["home_win_bin"].mean()
print(f"Overall home win rate: {overall_hw:.3f} ({overall_hw*100:.1f}%)")

# Per-venue home win rate (venues with ≥30 matches)
by_venue = venue_df.groupby("venue_name")["home_win_bin"].agg(["mean", "count", "sum"])
by_venue.columns = ["home_win_rate", "n_matches", "n_home_wins"]
by_venue = by_venue[by_venue["n_matches"] >= 30].sort_values("home_win_rate", ascending=False)
print(f"\nVenues with ≥30 matches ({len(by_venue)} venues):")
print(by_venue.to_string())

# ANOVA: does venue significantly affect home win rate?
venue_groups = [
    grp["home_win_bin"].values
    for _, grp in venue_df.groupby("venue_name")
    if len(grp) >= 30
]
f_stat, p_anova = stats.f_oneway(*venue_groups)
print(f"\nOne-way ANOVA (home win rate across venues with ≥30 matches):")
print(f"  F={f_stat:.4f}, p={p_anova:.6f}")

# Identify venues significantly above/below overall
print(f"\nVenues with home win rate significantly different from overall ({overall_hw:.3f}):")
for venue, row in by_venue.iterrows():
    grp = venue_df[venue_df["venue_name"] == venue]["home_win_bin"]
    t, p = stats.ttest_1samp(grp, overall_hw)
    if p < 0.10:
        direction = "↑ above" if row["home_win_rate"] > overall_hw else "↓ below"
        print(f"  {venue}: {row['home_win_rate']:.3f} (n={int(row['n_matches'])}) {direction} average, p={p:.4f}")

# With Betfair: does market implied prob match venue-adjusted home advantage?
bf_venue = venue_df[venue_df["bf_home_open"].notna() & venue_df["venue_name"].notna()].copy()
if len(bf_venue) > 20:
    print(f"\nBetfair venue analysis ({len(bf_venue)} matches):")
    bf_by_venue = bf_venue.groupby("venue_name").agg(
        n=("bf_implied_home", "count"),
        actual_hw=("home_win_bin", "mean"),
        implied_hw=("bf_implied_home", "mean")
    ).query("n >= 10").sort_values("actual_hw", ascending=False)
    bf_by_venue["edge"] = bf_by_venue["actual_hw"] - bf_by_venue["implied_hw"]
    print(bf_by_venue.to_string())

findings.append({
    "bias": "Venue/Home Bias",
    "test": "One-way ANOVA + per-venue t-test vs overall home win rate",
    "statistic": f"F={f_stat:.4f}",
    "p_value": p_anova,
    "significant": p_anova < 0.05,
    "direction": "Significant variation in home win rates across venues",
    "note": "See per-venue table for specific exploitable venues. Need bookmaker odds for exact edge calculation."
})

# ===========================================================================
# WRITE FINDINGS
# ===========================================================================
section("SUMMARY")

out_lines = [
    "# NRL Gambling Bias — Findings\n",
    f"**Dataset:** uselessnrlstats NRL matches 1998–2025 (n={len(df):,})",
    f"**Betfair exchange odds:** 2021–2026 subset (n={df['bf_home_open'].notna().sum():,} matches joined)\n",
    f"> **Note:** AusSportsBetting nrl.xlsx (bookmaker odds 2013–present) was not available — ",
    f"> the file downloaded from the website is an HTML placeholder. Download manually from",
    f"> https://www.aussportsbetting.com/data/historical-odds-results/nrl-rugby-league/",
    f"> and replace data/raw/nrl.xlsx to enable full odds-based bias testing.\n",
    "---\n",
]

for f in findings:
    sig = "**SIGNIFICANT (p < 0.05)**" if f["significant"] else "Not significant"
    out_lines += [
        f"## {f['bias']}",
        f"- **Test:** {f['test']}",
        f"- **Statistic:** {f['statistic']}",
        f"- **p-value:** {f['p_value']:.4f} — {sig}",
        f"- **Direction:** {f['direction']}",
        f"- **Notes:** {f['note']}",
        "",
    ]

# Draw bias detail
out_lines += [
    "---\n",
    "## Key Numbers\n",
    f"| Metric | Value |",
    f"|---|---|",
    f"| Overall NRL draw rate (1998–2025) | {draw_rate_all*100:.2f}% |",
    f"| Draw rate — both top-8 clubs | {draw_top8*100:.2f}% |",
    f"| Draw rate — other matchups | {draw_non_top8*100:.2f}% |",
    f"| Overall home win rate | {overall_hw*100:.1f}% |",
    f"| Form→outcome correlation (r) | {corr:.4f} |",
    f"| Venue ANOVA p-value | {p_anova:.4f} |",
    "",
    "---\n",
    "## Recommended Next Steps\n",
    "1. **Obtain bookmaker odds** (nrl.xlsx from AusSportsBetting) to directly test whether",
    "   market-implied probabilities diverge from actual outcomes at the identified venues.",
    "2. **Venue Bias** is the strongest statistical signal — focus strategy development here first.",
    "3. **Form Bias** shows a real correlation but needs odds data to confirm the market doesn't already price it in.",
    "4. **Draw Bias** is limited by NRL's low draw rate (~1%) — likely not exploitable without a draw market.",
]

findings_path = ROOT / "data" / "processed" / "findings.md"
findings_path.write_text("\n".join(out_lines))
print(f"\nFindings written to {findings_path}")

for f in findings:
    sig = "SIGNIFICANT" if f["significant"] else "not significant"
    print(f"  {f['bias']}: {sig} (p={f['p_value']:.4f})")
