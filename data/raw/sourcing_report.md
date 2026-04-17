# NRL Data Sourcing Report
Generated: 2026-04-16

---

## Summary

| Dataset | Files Attempted | Files Downloaded | Status |
|---|---|---|---|
| uselessnrlstats (GitHub) | 4 | 4 | SUCCESS |
| Betfair Automation Hub NRL | 12 | 12 | SUCCESS |
| AusSportsBetting nrl.xlsx | 1 | 0 | FAILED (placeholder HTML) |

---

## Dataset 1: uselessnrlstats Match History

**Source:** https://raw.githubusercontent.com/uselessnrlstats/uselessnrlstats/main/cleaned_data/nrl/

**Note:** The originally specified filenames (match_info.csv, team_info.csv, etc.) do not exist at
the given path. The actual repository uses different names under `cleaned_data/nrl/`. Files were
downloaded from that subdirectory and saved with the canonical local names specified in the task.

### Files Downloaded

| Local Filename | Remote Source | Data Rows | Date Range |
|---|---|---|---|
| `data/raw/uselessnrlstats/match_info.csv` | `match_data.csv` | 14,658 | 1908-04-20 to 2025-03-30 |
| `data/raw/uselessnrlstats/team_info.csv` | `team_data.csv` | 48 | — (reference table) |
| `data/raw/uselessnrlstats/venue_info.csv` | `venue_data.csv` | 102 | — (reference table) |
| `data/raw/uselessnrlstats/ladder_data.csv` | `ladder_round_data.csv` | 29,063 | All competitions |

### Schema Notes

**match_info.csv** columns:
`competition, competition_year, round, date, time, time_24hr, match_id, venue_id, crowd,
home_team, home_team_ht_score, home_team_score, home_team_penalties,
away_team, away_team_ht_score, away_team_score, away_team_penalties`

**team_info.csv** columns:
`team_short, team_name, team_unique, team_mascots, team_abbr`

**venue_info.csv** columns:
`venue_id, venue_name, non-commercial_name, location, country, states, cities`

**ladder_data.csv** columns:
`competition_year, year, round, ladder_position, team, points, played, wins, losses, draws,
byes, score_for, score_against, score_diff`

### NRL Competition Coverage (subset)
- NRL competition rows only (competition == 'NRL'): 5,435 matches
- NRL date range: 1998-03-13 to 2025-03-30
- Also includes: NSWRL (1908-1994), ARL (1995-1996), Super League (1997)

### Join Key to nrl.xlsx
- Join on: `date` (match_info.date == nrl.xlsx date column) + `home_team` + `away_team`
- Team names will require fuzzy or manual mapping — uselessnrlstats uses full official names
  (e.g. "Sydney Roosters") while nrl.xlsx likely uses abbreviations or alternate forms
- The `team_info.csv` provides `team_short`, `team_abbr` and `team_unique` fields to assist mapping
- The `venue_id` in match_info links to `venue_info.csv` via `venue_id`

---

## Dataset 2: Betfair Automation Hub NRL Exchange Odds

**Source:** https://betfair-datascientists.github.io/data/assets/

**Note:** All 12 NRL files (Match_Odds and All_Markets for 2021-2026) are freely accessible
without authentication. Files use UTF-8-BOM encoding.

### Files Downloaded

| Filename | Data Rows | Date Range |
|---|---|---|
| `NRL_2021_Match_Odds.csv` | 390 | 2021-03-13 to 2021-10-03 |
| `NRL_2022_Match_Odds.csv` | 383 | 2022 season |
| `NRL_2023_Match_Odds.csv` | 425 | 2023 season |
| `NRL_2024_Match_Odds.csv` | 426 | 2024 season |
| `NRL_2025_Match_Odds.csv` | 438 | 2025 season |
| `NRL_2026_Match_Odds.csv` | 96 | 2026-03-01 to 2026-04-12 (partial) |
| `NRL_2021_All_Markets.csv` | 86,921 | 2021 season |
| `NRL_2022_All_Markets.csv` | 85,034 | 2022 season |
| `NRL_2023_All_Markets.csv` | 96,414 | 2023 season |
| `NRL_2024_All_Markets.csv` | 98,764 | 2024 season |
| `NRL_2025_All_Markets.csv` | 98,744 | 2025 season |
| `NRL_2026_All_Markets.csv` | 20,611 | 2026 season (partial) |

**Match_Odds total data rows:** ~2,158 (across 2021-2026)
**All_Markets total data rows:** ~566,488 (across 2021-2026)
**Overall Betfair date coverage:** March 2021 to April 2026 (ongoing)

### Schema Notes (Match_Odds files)

Key columns:
`EVENT_DATE, PATH, EVENT_ID, MARKET_TYPE, MARKET_ID, MARKET_NAME, SELECTION_ID,
RUNNER_NAME, RUNNER_STATUS, IS_WINNER, TOTAL_POINTS, HOME_TEAM, AWAY_TEAM,
HOME_MARGIN, HOME_SCORE, AWAY_SCORE,
BEST_BACK_FIRST_BOUNCE, BEST_LAY_FIRST_BOUNCE, MATCHED_VOLUME_FIRST_BOUNCE,
BEST_BACK_PRICE_HALF_TIME, BEST_LAY_PRICE_HALF_TIME, MATCHED_VOLUME_HALF_TIME,
TOTAL_MATCHED_VOLUME`

Each match appears as multiple rows — one row per selection (home team, away team, draw if listed).
`RUNNER_NAME` holds the short team name. `HOME_TEAM` and `AWAY_TEAM` are the full fixture teams.

### Join Key to nrl.xlsx
- Join on: `EVENT_DATE` (date portion, strip time) + `HOME_TEAM` + `AWAY_TEAM`
- `HOME_TEAM` and `AWAY_TEAM` use full official team names (e.g. "Manly Sea Eagles",
  "South Sydney Rabbitohs") — same convention as uselessnrlstats match_info
- Team name normalisation will be needed to align with nrl.xlsx abbreviations

---

## Dataset 3: AusSportsBetting (data/raw/nrl.xlsx) — PRIMARY SOURCE

**Status: FAILED — placeholder HTML file, not a real spreadsheet**

`data/raw/nrl.xlsx` (and `nrl_new.xlsx`, `nrl_ua.xlsx`) are HTML redirect/placeholder pages
served by the AusSportsBetting website, not actual Excel files. Attempting to open them with
openpyxl or xlrd raises BadZipFile / format errors.

**Action required:** Download the real NRL data file manually from
https://www.aussportsbetting.com/data/historical-odds-results/nrl-rugby-league/
The site requires browser-based download (no direct API). Once downloaded, overwrite
`data/raw/nrl.xlsx` with the genuine file.

Expected schema (from project documentation): date + home/away team names + match result +
bookmaker odds (head-to-head), covering 2013-present.

---

## Downloader Script

`src/ingestion/fetch_uselessnrlstats.py` — downloads all 4 uselessnrlstats CSVs. Run with:

```
python src/ingestion/fetch_uselessnrlstats.py
```

Betfair files were downloaded directly via curl during this sourcing run. A dedicated Betfair
downloader script can be added to `src/ingestion/fetch_betfair.py` if re-fetching is needed.

---

## Recommended Join Strategy

When merging all three datasets:

1. **Normalise dates** to `YYYY-MM-DD` format across all sources.
2. **Normalise team names** to a canonical set using `team_info.csv` (team_unique or team_abbr).
   - Betfair uses full names: "Manly Sea Eagles", "South Sydney Rabbitohs"
   - uselessnrlstats uses: `home_team` / `away_team` (also full names, consistent with Betfair)
   - nrl.xlsx (once obtained) — likely uses short names; map via team_abbr
3. **Primary join key:** `match_date + home_team_canonical + away_team_canonical`
4. **For ladder/form features:** join `ladder_data.csv` on `competition_year + round + team`
   (round must be aligned with match_info round column)
5. **For Betfair odds:** filter `Match_Odds` files to one row per team per match, pivot on
   `RUNNER_NAME` to get home/away best-back prices side by side before joining.
