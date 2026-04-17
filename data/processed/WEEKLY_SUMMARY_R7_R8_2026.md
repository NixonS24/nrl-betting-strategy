# Weekly Summary — NRL Rounds 7 & 8, 2026

**Date generated:** 17 April 2026  
**Bankroll:** $100 | **Strategy:** Venue Bias (Quarter Kelly)  
**Repo:** https://github.com/NixonS24/nrl-betting-strategy

---

## ACTIVE BET — Round 7

| | |
|---|---|
| **Match** | Wests Tigers vs Brisbane Broncos |
| **Kickoff** | Saturday 18 April, 7:35pm AEST |
| **Venue** | Campbelltown Sports Stadium |
| **Bet** | Back **Brisbane Broncos** (fade home) |
| **Odds** | $2.45 |
| **Stake** | $8.99 (¼ Kelly on $100 bankroll) |
| **Edge** | 21.3% |
| **Expected profit** | +$4.69 |

**Why:** Campbelltown has a 37.9% historical home win rate. Market prices Broncos  
at $2.45 (40.8% implied) but history says away team wins here 62.1% of the time.  
Note: Wests Tigers are in strong form (3 wins in a row, sitting 2nd on ladder) and  
Adam Reynolds returns for Brisbane. Stick to the model — form filter tested and  
**does not improve ROI** over pure venue signal.

> **Action after game:** Log result in `data/processed/quick_wins/bet_ledger.csv`

---

## ROUND 8 PREVIEW — No qualifying bets

**ANZAC Round — 24–26 April 2026**

| Match | Venue | Strategy check |
|---|---|---|
| Wests Tigers vs Canberra Raiders | Leichhardt Oval | Not a strategy venue |
| North Queensland Cowboys vs Cronulla Sharks | Queensland Country Bank Stadium | Not a strategy venue |
| Brisbane Broncos vs Canterbury Bulldogs | Suncorp Stadium | Not a strategy venue |
| St George Illawarra vs Sydney Roosters | Allianz Stadium | Not a strategy venue |
| New Zealand Warriors vs Dolphins | Go Media Stadium | Not a strategy venue |
| **Melbourne Storm vs South Sydney Rabbitohs** | **AAMI Park** | Strategy venue ✓ — odds too short |
| Newcastle Knights vs Penrith Panthers | McDonald Jones Stadium | Not a strategy venue |
| Manly Sea Eagles vs Parramatta Eels | 4 Pines Park | Not a strategy venue |

**AAMI Park analysis:**  
Storm priced at ~$1.20 (implied 83.3%) — our venue base rate is 76.0%.  
Edge = 76.0% − 83.3% = **−7.3%** (negative — market overprices Storm).  
Minimum edge threshold is +5%. **No bet this round.**

---

## Bankroll Tracker

| Round | Bet | Stake | Odds | Result | P&L | Running Bankroll |
|---|---|---|---|---|---|---|
| R7 2026 | Broncos (away) @ Campbelltown | $8.99 | $2.45 | Pending | — | $100.00 |
| R8 2026 | — | — | — | No qualifying bets | — | — |

---

## Project Findings Summary

### Core Strategy: Venue Bias
- **79 bets backtested** (2009–2025), **+9.32% ROI**, $736 profit (flat $100 stakes)
- **Betfair validation:** 9 bets, 77.8% win rate, **+69.78% ROI**
- **Best venue:** AAMI Park — 43 bets, 30 wins, +$866, ROI **+20.1%**

### 5 Analysis Agents Run This Session

| # | Agent | Key Finding | Status |
|---|---|---|---|
| 1 | Rest & Travel Fatigue | Away short rest only +1.6% HW rate (p=0.27) | Not significant — skip |
| 2 | **Weather Overlay** | **Wet games −4.8 pts** (t=−6.79, p<0.0001); cold games +2.4 pts | **Confirmed — use for overs/unders** |
| 3 | **CLV Tracker** | Home odds shortening → **63% win rate** vs 48% drifting (p<0.0001) | **Live — bet early in week** |
| 4 | Referee Bias | Home advantage declining **−0.19%/yr** (p=0.015) over 27 seasons | Partial — need ref assignment data |
| 5 | Form Filter | 3/5 threshold: ROI −0.12%. 4/5: ROI −2.45%. No improvement. | Not integrated |

### Key Insights
1. **Bet early in the week** — CLV data shows home odds shortening predicts 63% win rate; capturing opening line value before market adjusts is measurable edge
2. **Weather = overs/unders signal** — wet games reliably score 4.8 fewer points (significant); check forecast before any qualifying game
3. **Home advantage is shrinking** — declining ~0.19%/yr; venue baselines should be recalculated annually to stay accurate
4. **Venue bias standalone is best** — form filter, rest filter add noise not signal; keep the strategy simple

---

## Next Steps

### This week
- [ ] Log R7 result (Saturday 18 Apr after 7:35pm AEST) in `bet_ledger.csv`
- [ ] No bet required for Round 8 (AAMI Park odds too short)

### Next session
- [ ] **Add weather to weekend picks** — fetch rain forecast for qualifying venue, auto-flag overs/unders opportunity when wet predicted
- [ ] **Scrape referee assignments** — NRL.com match pages contain referee name in JSON; build scraper to collect 2009–2026 assignments and re-run Agent 4 with real data
- [ ] **Regenerate Word report** — update with all 5 agent findings: `python src/strategy/generate_report.py`

### Medium term
- [ ] CLV dashboard after 20+ live bets logged
- [ ] Bookmaker account management plan (at +9% ROI, limits incoming)
- [ ] Mid-season dataset refresh for 2026 results

---

## Running the Project

```bash
# This week's bets (run each Thursday)
python src/strategy/weekend_picks.py --bankroll 100

# Run all 5 analysis agents
python -m src.agents.quick_wins.coordinator

# Full strategy backtest
python src/strategy/venue_bias.py

# Regenerate Word report
python src/strategy/generate_report.py
```

---

*National Gambling Helpline: 1800 858 858 | Bet responsibly*
