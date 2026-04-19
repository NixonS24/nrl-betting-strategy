# Agent 6 — Injury Mispricing Findings

## Hypothesis
Bookmakers incorrectly price player absences. Market overreacts to
offensive star injuries (halfback/five-eighth) and underreacts to
defensive losses (hooker, props). Injury impact ∝ salary cap value.

---

## Data Collection Status
- Lineup scraping test: 0/20 NRL.com pages returned data
- NRL.com scraping limited — use proxy analysis + alternative sources

---

## Proxy Analysis (Line Movement as Injury Signal)

### Big Line Moves (>10% odds change open→close)
- Matches with big move: 432  |  Small move: 1996
- HW rate — big move: **36.3%**  |  small: 60.5%
- t=-9.323, p=0.0000 — **SIGNIFICANT**

### Direction of Line Movement vs Outcome
- When home odds shortened (>5%): HW rate 60.8% (n=660)
- When home odds drifted (>5%): HW rate 40.3% (n=647)
- t=7.535, p=0.0000 — **SIGNIFICANT**
- Market direction CORRECT: odds move in right direction when team news hits

### Betfair Odds Calibration
How well do implied probabilities predict actual outcomes?
               n  actual_hw  avg_implied  calibration_error
prob_bucket                                                
<30%          66   0.212121     0.196313           0.015808
30-45%        55   0.363636     0.384056          -0.020420
45-55%        32   0.625000     0.505666           0.119334
55-70%        75   0.640000     0.631458           0.008542
>70%         134   0.791045     0.814724          -0.023679

Overall calibration: r=0.4380, p=0.0000
Positive calibration error = market UNDERESTIMATES home win probability
Negative error = market OVERESTIMATES home win probability

---


## Data Collection Plan for Full Injury Analysis

### Option 1: NRL.com Team Lists (Recommended)
- URL pattern: nrl.com/draw/nrl-premiership/{season}/round-{round}/{match-slug}/
- Available: ~2019–present with structured team list JSON
- Contains: player name, position, jersey number, interchange status
- Script: `fetch_nrl_team_list()` in this module — test first
- Collect: Thursday announcement + game-day 17 (compare for late withdrawals)

### Option 2: NRL Stats Hub
- URL: stats.nrl.com/v3/nrl/players
- Contains: career stats, representative history, seasons played
- Use as salary cap proxy: games played × position weight → player value score

### Option 3: SuperCoach / Fantasy Rankings
- Public SuperCoach prices are direct salary cap proxies
- Available each season; scrape pre-season prices as value weights
- Higher SC price = more important player = larger injury impact

### Proposed Injury Impact Score
```
injury_score(team) = sum(position_weight[pos] for player in missing_players)

where missing_players = Thursday_squad - game_day_17
```

### Hypothesis Tests (once data collected)
1. Does injury_score_delta predict outcome beyond Betfair implied probability?
2. Which positions show largest calibration error when missing?
3. Is the market's odds adjustment proportional to injury_score?
   - Too large adjustment = fade the move (back injured team)
   - Too small adjustment = follow the move (back healthy team)

---

## Position Importance Weights (Salary Cap Proxy)

| Position | Weight | Rationale |
|---|---|---|
| Halfback / Five-eighth | 10 | Controls attack, typically highest paid |
| Hooker | 9 | Most involved player (dummy half runs) |
| Fullback | 8 | Sweeper/playmaker, high profile |
| Prop (x2) | 7 | Engine room, fatigue management |
| Lock | 6 | Key defensive organiser |
| Centre (x2) | 5 | Try scorers, line defence |
| Winger (x2) | 4 | Peripheral impact |
| Second row (x2) | 4 | Workhorses |
| Bench/interchange | 2 | Rotation cover |

---

## Recommendation
**PARTIAL** — proxy analysis shows line movement is directionally correct
(market adjusts odds when team news breaks) but calibration error may exist.
**Next step:** Collect NRL.com team lists to build injury_score per match
and test if salary-weighted injury impact predicts outcomes beyond Betfair odds.