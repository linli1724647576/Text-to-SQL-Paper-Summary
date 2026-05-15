#!/usr/bin/env python3
"""Merge classified papers into data/labeldata/labeldata.json."""

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LABELDATA = REPO_ROOT / "data" / "labeldata" / "labeldata.json"


def main():
    parser = argparse.ArgumentParser(description="Merge labeled papers")
    parser.add_argument("input")
    parser.add_argument("--labeldata", default=str(DEFAULT_LABELDATA))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-overwrite", action="store_true")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        new_papers = json.load(f)
    if os.path.exists(args.labeldata):
        with open(args.labeldata, encoding="utf-8") as f:
            existing = json.load(f)
    else:
        existing = {}

    added = updated = skipped = invalid = 0
    for title, entry in new_papers.items():
        if not entry.get("labels") or not entry.get("pipeline_stages"):
            invalid += 1
            continue
        key = entry.get("title") or title
        if key in existing:
            if args.no_overwrite:
                skipped += 1
            else:
                existing[key] = entry
                updated += 1
        else:
            existing[key] = entry
            added += 1

    print(f"Added: {added}", file=sys.stderr)
    print(f"Updated: {updated}", file=sys.stderr)
    print(f"Skipped: {skipped}", file=sys.stderr)
    print(f"Invalid: {invalid}", file=sys.stderr)
    print(f"Total: {len(existing)}", file=sys.stderr)

    if args.dry_run:
        return

    Path(args.labeldata).parent.mkdir(parents=True, exist_ok=True)
    with open(args.labeldata, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(existing.items())), f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
