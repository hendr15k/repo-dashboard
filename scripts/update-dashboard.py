#!/usr/bin/env python3
"""Auto-update repo-dashboard with live CI statuses from GitHub API."""

import json
import re
import subprocess
import sys

OWNER = "hendr15k"

def get_ci_status(repo_name):
    """Get latest workflow run conclusion for a repo."""
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{OWNER}/{repo_name}/actions/runs",
             "--jq", ".workflow_runs[0].conclusion // .workflow_runs[0].status // \"none\""],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            status = result.stdout.strip().strip('"')
            if status in ("success", "failure", "cancelled", "action_required", "timed_out"):
                return status
            return "none"
    except Exception:
        pass
    return "none"

def get_repo_info(repo_name):
    """Get description and pushedAt for a repo."""
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{OWNER}/{repo_name}",
             "--jq", "{description: .description, pushedAt: .pushedAt}"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            return json.loads(result.stdout.strip())
    except Exception:
        pass
    return {}

def main():
    with open("index.html", "r") as f:
        html = f.read()

    match = re.search(r'const EMBEDDED_DATA = \[(.*?)\];', html, re.DOTALL)
    if not match:
        print("ERROR: no EMBEDDED_DATA found in index.html")
        sys.exit(1)

    data = json.loads('[' + match.group(1) + ']')
    updated = 0

    for repo in data:
        name = repo["name"]

        # Update CI status
        ci = get_ci_status(name)
        if repo.get("ciStatus") != ci:
            repo["ciStatus"] = ci
            updated += 1

        # Update description and timestamp
        info = get_repo_info(name)
        if info.get("description") and info["description"] != repo.get("description"):
            repo["description"] = info["description"]
            updated += 1
        if info.get("pushedAt"):
            repo["updatedAt"] = info["pushedAt"]

    new_data_str = json.dumps(data, ensure_ascii=False, indent=2)
    new_html = html[:match.start()] + 'const EMBEDDED_DATA = ' + new_data_str + ';' + html[match.end():]

    with open("index.html", "w") as f:
        f.write(new_html)

    passing = sum(1 for r in data if r.get("ciStatus") == "success")
    failing = sum(1 for r in data if r.get("ciStatus") == "failure")
    print(f"Updated {updated} fields. {passing} passing, {failing} failing, {len(data)} total repos.")

if __name__ == "__main__":
    main()
