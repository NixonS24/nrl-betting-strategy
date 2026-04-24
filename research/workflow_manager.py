
import subprocess
import os
import sys
import json
from pathlib import Path

def run_git(args):
    """Run a git command and return output."""
    result = subprocess.run(["git"] + args, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
    return result.stdout

def create_research_branch(h_id):
    branch_name = f"research/{h_id}"
    print(f"Creating branch {branch_name}...")
    run_git(["checkout", "-b", branch_name])

def commit_results(h_id, summary):
    print("Staging research files...")
    run_git(["add", f"research/hypotheses/{h_id}.md"])
    run_git(["add", f"research/scripts/{h_id}_analysis.py"])
    run_git(["add", f"research/results/R_{h_id[2:]}.json"])
    run_git(["add", f"research/visuals/{h_id}_plot.png"])
    
    commit_msg = f"research: validate {h_id} - {summary}"
    run_git(["commit", "-m", commit_msg])
    print(f"Committed: {commit_msg}")

def update_findings(h_id, summary):
    findings_path = Path("data/processed/findings.md")
    if not findings_path.exists():
        print("Findings file not found.")
        return
    
    content = findings_path.read_text()
    new_entry = f"\n- **{h_id}**: {summary} (Verified {Path('research/results/R_' + h_id[2:] + '.json')})"
    
    if h_id not in content:
        with open(findings_path, "a") as f:
            f.write(new_entry)
        print(f"Updated {findings_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python workflow_manager.py [h_id] [summary]")
        sys.exit(1)
    
    h_id = sys.argv[1]
    summary = sys.argv[2]
    
    create_research_branch(h_id)
    update_findings(h_id, summary)
    commit_results(h_id, summary)
