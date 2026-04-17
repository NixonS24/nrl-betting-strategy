# Venue Bias Strategy — Backtest Results

**Period:** Betfair exchange odds 2021–2025
**Strategy:** Back home at AAMI Park / Olympic Park / QSAC when market implied prob
is ≥5% below historical home win rate. Fade home at Campbelltown / Cbus Super.

## Performance
| Metric | Value |
|---|---|
| Total bets | 10 |
| Win rate | 80.0% |
| Total staked | $1,000 |
| Total profit | $1,008.00 |
| ROI | 100.80% |
| Max drawdown | $100.00 |
| Avg odds | 2.404 |

## By Venue
| venue                       |   n |   wins |   profit |      roi |
|:----------------------------|----:|-------:|---------:|---------:|
| AAMI Park                   |   6 |      5 |      453 | 0.755    |
| Campbelltown Sports Stadium |   3 |      2 |      175 | 0.583333 |
| Cbus Super Stadium          |   1 |      1 |      380 | 3.8      |

## All Bets
| date                | home_team       | away_team                  | venue                       | bet_type   |   odds |   edge | result   | won   |   profit |   cumulative_profit |
|:--------------------|:----------------|:---------------------------|:----------------------------|:-----------|-------:|-------:|:---------|:------|---------:|--------------------:|
| 2021-07-22 00:00:00 | Parramatta Eels | Canberra Raiders           | Cbus Super Stadium          | fade_home  |   4.8  | 0.3483 | away_win | True  |      380 |                 380 |
| 2022-08-07 00:00:00 | Wests Tigers    | Newcastle Knights          | Campbelltown Sports Stadium | fade_home  |   2.86 | 0.2713 | away_win | True  |      186 |                 566 |
| 2022-08-26 00:00:00 | Melbourne Storm | Sydney Roosters            | AAMI Park                   | back_home  |   1.62 | 0.1429 | away_win | False |     -100 |                 466 |
| 2023-04-06 00:00:00 | Melbourne Storm | Sydney Roosters            | AAMI Park                   | back_home  |   1.71 | 0.1754 | home_win | True  |       71 |                 537 |
| 2023-05-11 00:00:00 | Melbourne Storm | Brisbane Broncos           | AAMI Park                   | back_home  |   1.76 | 0.1921 | home_win | True  |       76 |                 613 |
| 2023-06-02 00:00:00 | Wests Tigers    | Canberra Raiders           | Campbelltown Sports Stadium | fade_home  |   1.89 | 0.0919 | away_win | True  |       89 |                 702 |
| 2023-06-11 00:00:00 | Melbourne Storm | Cronulla Sutherland Sharks | AAMI Park                   | back_home  |   1.7  | 0.172  | home_win | True  |       70 |                 772 |
| 2024-03-08 00:00:00 | Melbourne Storm | Penrith Panthers           | AAMI Park                   | back_home  |   3.1  | 0.4377 | home_win | True  |      210 |                 982 |
| 2024-07-20 00:00:00 | Melbourne Storm | Sydney Roosters            | AAMI Park                   | back_home  |   2.26 | 0.3178 | home_win | True  |      126 |                1108 |
| 2025-03-30 00:00:00 | Wests Tigers    | New Zealand Warriors       | Campbelltown Sports Stadium | fade_home  |   2.34 | 0.1936 | draw     | False |     -100 |                1008 |

## Limitations
- Betfair sample only 238 matches (2021–2025) — limited statistical power
- No bookmaker odds yet (nrl.xlsx placeholder) — can't test pre-2021
- Historical base rates computed on full 1998–2025 dataset (look-ahead on early years)
- Once nrl.xlsx is downloaded, re-run with bookmaker closing odds for 2013–2025