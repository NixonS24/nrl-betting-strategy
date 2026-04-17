# NRL Gambling Bias — Findings

**Dataset:** uselessnrlstats NRL matches 1998–2025 (n=5,435)
**Betfair exchange odds:** 2021–2026 subset (n=362 matches joined)

> **Note:** AusSportsBetting nrl.xlsx (bookmaker odds 2013–present) was not available — 
> the file downloaded from the website is an HTML placeholder. Download manually from
> https://www.aussportsbetting.com/data/historical-odds-results/nrl-rugby-league/
> and replace data/raw/nrl.xlsx to enable full odds-based bias testing.

---

## Draw Bias
- **Test:** Chi-square (top-8 matchup draw rate vs others)
- **Statistic:** chi2=0.2508
- **p-value:** 0.6165 — Not significant
- **Direction:** Top-8 draw rate 1.17% vs 0.96% other
- **Notes:** Overall draw rate only 1.01% — NRL rarely draws. Betfair doesn't price a draw market, so no direct odds mispricing test possible without bookmaker odds.

## Form/Momentum Bias
- **Test:** Point-biserial correlation + t-test by form bucket
- **Statistic:** r=0.1992
- **p-value:** 0.0000 — **SIGNIFICANT (p < 0.05)**
- **Direction:** Form diff positively predicts home win (r=0.199)
- **Notes:** Form predicts outcome, but need bookmaker odds to test if market ALREADY prices this in. Betfair sample (238 matches) too small for strong conclusions.

## Venue/Home Bias
- **Test:** One-way ANOVA + per-venue t-test vs overall home win rate
- **Statistic:** F=4.3271
- **p-value:** 0.0000 — **SIGNIFICANT (p < 0.05)**
- **Direction:** Significant variation in home win rates across venues
- **Notes:** See per-venue table for specific exploitable venues. Need bookmaker odds for exact edge calculation.

---

## Key Numbers

| Metric | Value |
|---|---|
| Overall NRL draw rate (1998–2025) | 1.01% |
| Draw rate — both top-8 clubs | 1.17% |
| Draw rate — other matchups | 0.96% |
| Overall home win rate | 57.4% |
| Form→outcome correlation (r) | 0.1992 |
| Venue ANOVA p-value | 0.0000 |

---

## Recommended Next Steps

1. **Obtain bookmaker odds** (nrl.xlsx from AusSportsBetting) to directly test whether
   market-implied probabilities diverge from actual outcomes at the identified venues.
2. **Venue Bias** is the strongest statistical signal — focus strategy development here first.
3. **Form Bias** shows a real correlation but needs odds data to confirm the market doesn't already price it in.
4. **Draw Bias** is limited by NRL's low draw rate (~1%) — likely not exploitable without a draw market.