"""
Fetches NRL match history CSV files from the uselessnrlstats GitHub repository
(cleaned data sourced from Rugby League Project, covering 1908-present).

Files downloaded:
  - match_data.csv      -> data/raw/uselessnrlstats/match_info.csv
  - team_data.csv       -> data/raw/uselessnrlstats/team_info.csv
  - venue_data.csv      -> data/raw/uselessnrlstats/venue_info.csv
  - ladder_round_data.csv -> data/raw/uselessnrlstats/ladder_data.csv

Run:
    python src/ingestion/fetch_uselessnrlstats.py
"""

import os
import sys
import requests

BASE_URL = "https://raw.githubusercontent.com/uselessnrlstats/uselessnrlstats/main/cleaned_data/nrl"

# (remote_filename, local_save_name)
FILES = [
    ("match_data.csv", "match_info.csv"),
    ("team_data.csv", "team_info.csv"),
    ("venue_data.csv", "venue_info.csv"),
    ("ladder_round_data.csv", "ladder_data.csv"),
]

OUTPUT_DIR = "/Users/taylahart/AI_Projects/gamblingProject/data/raw/uselessnrlstats"


def download_file(remote_name: str, local_name: str) -> dict:
    url = f"{BASE_URL}/{remote_name}"
    local_path = os.path.join(OUTPUT_DIR, local_name)
    result = {"url": url, "local_path": local_path, "success": False, "rows": 0, "error": None}

    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        content = response.text

        with open(local_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Count rows (subtract 1 for header)
        lines = [l for l in content.splitlines() if l.strip()]
        result["rows"] = max(0, len(lines) - 1)
        result["success"] = True
        print(f"  OK  {local_name} ({result['rows']} data rows)")
    except requests.HTTPError as e:
        result["error"] = f"HTTP {e.response.status_code}"
        print(f"  FAIL {local_name}: {result['error']}", file=sys.stderr)
    except Exception as e:
        result["error"] = str(e)
        print(f"  FAIL {local_name}: {result['error']}", file=sys.stderr)

    return result


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Downloading uselessnrlstats CSVs to {OUTPUT_DIR}")
    results = []
    for remote_name, local_name in FILES:
        results.append(download_file(remote_name, local_name))

    successes = sum(1 for r in results if r["success"])
    print(f"\nDone: {successes}/{len(FILES)} files downloaded successfully.")
    return results


if __name__ == "__main__":
    main()
