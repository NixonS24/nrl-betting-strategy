"""
NRL Gambling Bias Research — Agent Team

Four-agent pipeline coordinated by an orchestrator:
  1. data-sourcer          — fetches supplementary datasets to extend coverage beyond nrl.xlsx
  2. requirements-manager  — defines the analysis spec for each run
  3. data-engineer         — ingests/cleans all raw data and writes processed outputs
  4. data-scientist        — runs statistical analysis and reports findings

Data sources used:
  - data/raw/nrl.xlsx              : AusSportsBetting (results + odds 2013–present)
  - data/raw/uselessnrlstats/      : uselessnrlstats CSVs (match history 1998–present, no odds)
  - data/raw/betfair/              : Betfair Automation Hub CSVs (exchange odds 2021–present)

Usage:
    python -m src.agents.team
    python -m src.agents.team --task "Investigate draw bias for top-8 teams since 2018"
    python -m src.agents.team --skip-sourcing   # skip data-sourcer, use existing raw data
"""

import argparse
import anyio
from pathlib import Path

from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition, ResultMessage

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"

DEFAULT_TASK = (
    "Run the full research pipeline: "
    "1) Use the data-sourcer to fetch supplementary datasets (uselessnrlstats CSVs and "
    "Betfair historical CSVs) into data/raw/, "
    "2) Use the requirements-manager to define the analysis spec, "
    "3) Use the data-engineer to ingest and merge all raw data sources into a unified "
    "processed dataset, "
    "4) Use the data-scientist to analyse the processed data for Draw Bias, "
    "Form/Momentum Bias, and Venue/Home Bias. "
    "Write a summary of findings to data/processed/findings.md."
)

SOURCING_ONLY_TASK = (
    "Use the data-sourcer to fetch all supplementary datasets into data/raw/ "
    "and write a sourcing report to data/raw/sourcing_report.md."
)

AGENTS = {
    "data-sourcer": AgentDefinition(
        description=(
            "NRL data sourcer. Fetches supplementary datasets from the web to extend "
            "coverage beyond the existing nrl.xlsx. Downloads uselessnrlstats match history "
            "CSVs (1998–present) and Betfair Automation Hub NRL exchange odds CSVs (2021–present) "
            "into data/raw/. Writes a sourcing report summarising what was fetched."
        ),
        prompt=(
            "You are the data sourcer for an NRL gambling bias research project. "
            "Your job is to fetch two supplementary datasets and save them to data/raw/.\n\n"
            "## Dataset 1: uselessnrlstats match history CSVs\n"
            "These are pre-cleaned CSVs scraped from Rugby League Project covering NRL "
            "history back to 1998 (no odds, match results only).\n"
            "Fetch the following files from the GitHub raw URL base "
            "https://raw.githubusercontent.com/uselessnrlstats/uselessnrlstats/main/cleaned_data/ "
            "and save each to data/raw/uselessnrlstats/<filename>:\n"
            "  - match_info.csv\n"
            "  - team_info.csv\n"
            "  - venue_info.csv\n"
            "  - ladder_data.csv\n"
            "Use Python (requests library) to download each file. "
            "Write the downloader script to src/ingestion/fetch_uselessnrlstats.py and run it.\n\n"
            "## Dataset 2: Betfair Automation Hub NRL CSV files\n"
            "Betfair publishes historical exchange odds CSVs for NRL on their Automation Hub. "
            "The listing page is: https://betfair-datascientists.github.io/data/dataListing/\n"
            "Check that page for the NRL CSV download links. Download any freely available "
            "NRL match odds CSV files and save them to data/raw/betfair/. "
            "If direct download requires login/authentication, note this in the report and "
            "skip gracefully — do not fail the whole task.\n\n"
            "## Output\n"
            "Write a sourcing report to data/raw/sourcing_report.md that records:\n"
            "  - Which files were successfully downloaded and their row counts\n"
            "  - Date range covered by each dataset\n"
            "  - Any files that could not be fetched and why\n"
            "  - How each dataset should be joined to nrl.xlsx (matching keys: date + teams)\n"
        ),
        tools=["Read", "Write", "Bash", "Glob", "WebFetch"],
    ),

    "requirements-manager": AgentDefinition(
        description=(
            "NRL research project manager. Reads raw data and existing code, "
            "then writes a clear analysis requirements spec (requirements_spec.md) "
            "covering which columns to use, bias hypotheses to test, and success criteria."
        ),
        prompt=(
            "You are the project manager for an NRL gambling bias research project. "
            "Your job is to read the raw data schema and any existing analysis code, "
            "then produce a concise requirements spec at data/processed/requirements_spec.md. "
            "The spec must define:\n"
            "  - Which columns in nrl.xlsx map to what (teams, scores, venue, odds, date)\n"
            "  - Exact statistical tests to run for each of the three biases:\n"
            "      * Draw Bias: probability of draws for top-tier clubs vs. market-implied\n"
            "      * Form/Momentum Bias: recent performance vs. market odds movement\n"
            "      * Venue/Home Bias: home advantage by specific venue vs. market adjustment\n"
            "  - What 'big teams' / top-tier clubs means (define the set)\n"
            "  - Minimum sample size and significance threshold (p < 0.05)\n"
            "Be precise and actionable — the data-engineer and data-scientist will follow this spec."
        ),
        tools=["Read", "Write", "Glob", "Grep"],
    ),

    "data-engineer": AgentDefinition(
        description=(
            "NRL data pipeline engineer. Reads the requirements spec and all raw data sources "
            "(nrl.xlsx, uselessnrlstats CSVs, Betfair CSVs), merges and cleans them, "
            "then writes a unified processed dataset to data/processed/."
        ),
        prompt=(
            "You are the data engineer for an NRL gambling bias research project. "
            "Read data/processed/requirements_spec.md and data/raw/sourcing_report.md "
            "(if it exists) to understand what data is available, "
            "then build a Python script at src/ingestion/pipeline.py that:\n"
            "  1. Loads data/raw/nrl.xlsx (primary: results + odds 2013–present)\n"
            "  2. If data/raw/uselessnrlstats/match_info.csv exists, loads it and left-joins "
            "     on date + team names to extend history back to 1998 for rows missing from "
            "     nrl.xlsx (match results only — no odds for pre-2013 rows)\n"
            "  3. If data/raw/betfair/ CSVs exist, loads them and joins on date + teams "
            "     to add Betfair exchange closing prices as additional columns\n"
            "  4. Standardises column names (snake_case) across all sources\n"
            "  5. Parses dates and sorts chronologically\n"
            "  6. Derives features: result ('draw'/'home_win'/'away_win'), "
            "     rolling_form_5 for both teams, is_top_8_club flag, "
            "     implied_prob_home/away/draw from closing odds\n"
            "  7. Writes the unified frame to data/processed/nrl_clean.csv\n"
            "  8. Prints a data quality report (shape, nulls, date range, rows per source)\n"
            "Run the script with Bash after writing it. Fix any errors before finishing. "
            "If supplementary files are missing, continue with nrl.xlsx alone and note it."
        ),
        tools=["Read", "Write", "Bash", "Glob", "Grep"],
    ),

    "data-scientist": AgentDefinition(
        description=(
            "NRL data scientist / statistician. Reads processed data and runs "
            "statistical tests for Draw Bias, Form Bias, and Venue Bias, "
            "then writes findings to data/processed/findings.md."
        ),
        prompt=(
            "You are the data scientist for an NRL gambling bias research project. "
            "Read data/processed/requirements_spec.md for the analysis spec and "
            "data/processed/nrl_clean.csv for the processed data. "
            "Write a Python analysis script at src/analysis/bias_analysis.py that:\n"
            "  1. Draw Bias — chi-square or binomial test: are draws more frequent "
            "     among top-8 clubs than market-implied odds suggest?\n"
            "  2. Form/Momentum Bias — regression or t-test: does recent win/loss streak "
            "     predict market odds movement in a direction inconsistent with actual outcomes?\n"
            "  3. Venue/Home Bias — ANOVA or paired t-test by venue: does home advantage "
            "     vary significantly across venues in a way the market misprices?\n"
            "Run the script. Write all findings (including test statistics, p-values, "
            "effect sizes, and a plain-English interpretation) to data/processed/findings.md. "
            "Flag any bias with p < 0.05 as potentially exploitable. "
            "Note limitations (sample size, available columns, etc.)."
        ),
        tools=["Read", "Write", "Bash", "Glob", "Grep"],
    ),
}


async def run_team(task: str, skip_sourcing: bool = False) -> None:
    print(f"\n{'='*60}")
    print("NRL Gambling Bias Research — Agent Team")
    print(f"{'='*60}")
    print(f"Task: {task}\n")

    # When skipping sourcing, remove data-sourcer from available agents
    agents = dict(AGENTS)
    if skip_sourcing:
        agents.pop("data-sourcer", None)
        print("[--skip-sourcing] data-sourcer agent disabled\n")

    async for message in query(
        prompt=task,
        options=ClaudeAgentOptions(
            cwd=str(PROJECT_ROOT),
            allowed_tools=["Read", "Write", "Bash", "Glob", "Grep", "Agent", "WebFetch"],
            agents=agents,
            permission_mode="acceptEdits",
            max_turns=60,
        ),
    ):
        if isinstance(message, ResultMessage):
            print("\n" + "="*60)
            print("TEAM RESULT")
            print("="*60)
            print(message.result)
            if message.stop_reason != "end_turn":
                print(f"\n[Stop reason: {message.stop_reason}]")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the NRL research agent team")
    parser.add_argument(
        "--task",
        default=DEFAULT_TASK,
        help="High-level task for the orchestrator to execute",
    )
    parser.add_argument(
        "--skip-sourcing",
        action="store_true",
        help="Skip the data-sourcer agent and use existing raw data only",
    )
    parser.add_argument(
        "--source-only",
        action="store_true",
        help="Run the data-sourcer agent only (fetch supplementary datasets)",
    )
    args = parser.parse_args()

    task = SOURCING_ONLY_TASK if args.source_only else args.task
    anyio.run(run_team, task, args.skip_sourcing)


if __name__ == "__main__":
    main()
