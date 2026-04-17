# Agent 4 — Referee Bias Findings

Dataset: 5,435 matches

## Evidence Base
Frontiers in Sports (2021, peer-reviewed): NRL referees exhibit systematic
home advantage bias. Tier-1 refs (300+ games) show less bias but never zero.
Effect size: ~0.5 points per penalty advantage.

---

## Home Win Rate by Season
         hw_rate    n
season               
1998    0.584980  253
1999    0.591549  213
2000    0.670157  191
2001    0.539267  191
2002    0.592593  189
2003    0.539683  189
2004    0.582011  189
2005    0.582011  189
2006    0.571429  189
2007    0.567164  201
2008    0.587065  201
2009    0.611940  201
2010    0.557214  201
2011    0.616915  201
2012    0.567164  201
2013    0.577114  201
2014    0.577114  201
2015    0.537313  201
2016    0.587065  201
2017    0.537313  201
2018    0.577114  201
2019    0.557214  201
2020    0.532544  169
2021    0.547264  201
2022    0.582090  201
2023    0.563380  213
2024    0.582160  213
2025    0.468750   32

## Long-run Home Advantage Trend
- Slope: -0.0019 per season (decreasing)
- r=-0.454, p=0.0152 — **SIGNIFICANT**

## Home Win Rate by Era (referee rule changes)
            hw_rate     n
era                      
1998–2003  0.586460  1226
2004–2010  0.579869  1371
2011–2017  0.571429  1407
2018–2026  0.561845  1431

## Home Win Rate by Day of Week
              hw_rate     n
day_of_week                
Wednesday    1.000000     5
Tuesday      0.833333     6
Friday       0.582290  1118
Sunday       0.578134  1747
Monday       0.571895   306
Saturday     0.568550  2035
Thursday     0.545872   218

## Average Home Margin by Season
season
1998    5.003953
1999    4.211268
2000    7.319372
2001    4.507853
2002    5.116402
2003    2.185185
2004    5.375661
2005    5.412698
2006    2.111111
2007    5.825871
2008    5.169154
2009    4.084577
2010    4.412935
2011    3.577114
2012    2.363184
2013    4.079602
2014    4.179104
2015    3.716418
2016    2.000000
2017    0.507463
2018    2.447761
2019    3.875622
2020    2.538462
2021    1.457711
2022    2.746269
2023    2.600939
2024    2.901408
2025    5.083333

---

## How to Get Full Referee Data
1. **NRL.com API** — each match page contains referee name in JSON.
   Run `fetch_nrl_com_referee()` across all match IDs (rate limited, ~1 req/sec).
2. **NRL Premiership data** — NRL official stats hub sometimes includes referee.
3. **Manual collection** — for seasons 2009–2020, ref data may require scraping
   historical match reports.

Once referee data is collected, re-run this agent for full ANOVA analysis.

---

## Recommendation
**INTEGRATE** — significant referee or trend effect found; add as confidence modifier.