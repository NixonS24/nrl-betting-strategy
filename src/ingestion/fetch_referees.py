"""
Fetch Referee Assignments from NRL.com
=====================================
Scrapes referee names from NRL match centre pages.
Outputs to data/raw/referee_assignments.csv

Usage:
    python3 src/ingestion/fetch_referees.py --seasons 2024,2025
"""

import time
import json
import re
import urllib.request
import pandas as pd
from pathlib import Path
from html import unescape
import argparse

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUT_PATH = RAW / "referee_assignments.csv"
RAW.mkdir(parents=True, exist_ok=True)

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

def get_fixtures(season: int, round_num: int) -> list:
    url = f"https://www.nrl.com/draw//data?competition=111&season={season}&round={round_num}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        fixtures = []
        for f in data.get("fixtures", []):
            mc_url = f.get("matchCentreUrl", "")
            if not mc_url: continue
            
            # Extract slug: /draw/nrl-premiership/2024/round-1/slug/
            parts = mc_url.strip("/").split("/")
            if len(parts) < 1: continue
            slug = parts[-1]
            
            fixtures.append({
                "season": season,
                "round": round_num,
                "match_slug": slug,
                "home_nickname": f.get("homeTeam", {}).get("nickName"),
                "away_nickname": f.get("awayTeam", {}).get("nickName"),
                "match_id": f.get("matchId")
            })
        return fixtures
    except Exception as e:
        print(f"  [!] Draw API failed for {season} R{round_num}: {e}")
        return []

def fetch_referee(season: int, round_num: int, slug: str) -> str:
    url = f"https://www.nrl.com/draw/nrl-premiership/{season}/round-{round_num}/{slug}/"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="ignore")
        
        # Pattern for referee: position: "Referee"
        # The JSON is often escaped in HTML
        pattern = r'&quot;firstName&quot;:&quot;([^&]+)&quot;,&quot;lastName&quot;:&quot;([^&]+)&quot;,&quot;profileId&quot;:\d+,&quot;position&quot;:&quot;Referee&quot;'
        m = re.search(pattern, html)
        if m:
            return f"{m.group(1)} {m.group(2)}"
        
        # Fallback for unescaped HTML
        pattern_raw = r'"firstName":"([^"]+)","lastName":"([^"]+)","profileId":\d+,"position":"Referee"'
        m = re.search(pattern_raw, html)
        if m:
            return f"{m.group(1)} {m.group(2)}"
            
        return None
    except Exception as e:
        print(f"    [!] Fetch failed for {slug}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seasons", type=str, default="2024,2025")
    parser.add_argument("--rounds", type=int, default=30)
    args = parser.parse_args()
    
    target_seasons = [int(s) for s in args.seasons.split(",")]
    
    # Load existing data to resume
    if OUT_PATH.exists():
        existing_df = pd.read_csv(OUT_PATH)
        processed_slugs = set(existing_df["match_slug"].tolist())
        results = existing_df.to_dict("records")
    else:
        processed_slugs = set()
        results = []
    
    print(f"Starting referee fetch for seasons: {target_seasons}")
    
    try:
        for season in target_seasons:
            for round_num in range(1, args.rounds + 1):
                fixtures = get_fixtures(season, round_num)
                if not fixtures:
                    if round_num > 25: break # End of season
                    continue
                
                print(f"Season {season} Round {round_num}: {len(fixtures)} matches")
                for fix in fixtures:
                    if fix["match_slug"] in processed_slugs:
                        continue
                    
                    print(f"  Fetching {fix['match_slug']}...")
                    ref = fetch_referee(season, round_num, fix["match_slug"])
                    if ref:
                        fix["referee"] = ref
                        results.append(fix)
                        processed_slugs.add(fix["match_slug"])
                        print(f"    -> {ref}")
                    else:
                        print(f"    -> NOT FOUND")
                    
                    time.sleep(0.5)
                
                # Save progress after each round
                pd.DataFrame(results).to_csv(OUT_PATH, index=False)
                
    except KeyboardInterrupt:
        print("\nInterrupted. Saving progress...")
        pd.DataFrame(results).to_csv(OUT_PATH, index=False)

if __name__ == "__main__":
    main()
