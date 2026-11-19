#!/usr/bin/env python3
"""Preview the chapter milestones, or create missing milestones in an explicit repository."""

import argparse
from pathlib import Path
import re
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, metavar="OWNER/REPOSITORY")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create missing milestones using an authenticated GitHub CLI.",
    )
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9._-]+", args.repo) or args.repo.split(
        "/"
    )[1] in {".", ".."}:
        parser.error("Use an explicit GitHub owner and repository name.")

    milestone_file = Path(__file__).resolve().parents[1] / "MILESTONES.md"
    records = []
    for line in milestone_file.read_text().splitlines():
        if re.match(r"^\| `(?:checkpoint|chapters-\d+\.\d+\.\d+)/", line):
            tag, title, criteria = (cell.strip() for cell in line.strip("|").split("|"))
            records.append((title, f"{criteria}\n\nPlayable source tag: {tag}."))
    if len(records) != 11:
        parser.error("Expected eleven chapter entries in MILESTONES.md.")

    if not args.apply:
        print(f"Preview for {args.repo}")
        for title, details in records:
            print(f"\n{title}\n{details}")
        return

    endpoint = f"repos/{args.repo}/milestones"
    result = subprocess.run(
        [
            "gh",
            "api",
            "--paginate",
            f"{endpoint}?state=all&per_page=100",
            "--jq",
            ".[].title",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    existing = set(result.stdout.splitlines())
    for title, details in records:
        if title in existing:
            print(f"Already exists: {title}")
            continue
        subprocess.run(
            [
                "gh",
                "api",
                "--method",
                "POST",
                endpoint,
                "-f",
                f"title={title}",
                "-f",
                f"description={details}",
                "--silent",
            ],
            check=True,
        )
        print(f"Created: {title}")


if __name__ == "__main__":
    main()
