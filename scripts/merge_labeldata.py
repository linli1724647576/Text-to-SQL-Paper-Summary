#!/usr/bin/env python3
"""Merge classified papers into data/labeldata/labeldata.json."""

import argparse
import json
import os
import sys
from pathlib import Path

from paper_utils import dedupe_papers, normalize_title_key, upsert_paper

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LABELDATA = REPO_ROOT / "data" / "labeldata" / "labeldata.json"


def main():
    parser = argparse.ArgumentParser(description="Merge labeled papers")
    parser.add_argument("input", nargs="?")
    parser.add_argument("--labeldata", default=str(DEFAULT_LABELDATA))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-overwrite", action="store_true")
    parser.add_argument("--dedupe-only", action="store_true")
    args = parser.parse_args()

    if not args.input and not args.dedupe_only:
        parser.error("input is required unless --dedupe-only is set")

    if os.path.exists(args.labeldata):
        with open(args.labeldata, encoding="utf-8") as f:
            existing = json.load(f)
    else:
        existing = {}
    existing, existing_duplicates = dedupe_papers(existing)

    if args.dedupe_only:
        print(f"Deduped existing duplicates: {existing_duplicates}", file=sys.stderr)
        print(f"Total: {len(existing)}", file=sys.stderr)
        if not args.dry_run:
            Path(args.labeldata).parent.mkdir(parents=True, exist_ok=True)
            with open(args.labeldata, "w", encoding="utf-8") as f:
                json.dump(dict(sorted(existing.items())), f, indent=2, ensure_ascii=False)
        return

    with open(args.input, encoding="utf-8") as f:
        new_papers = json.load(f)

    added = updated = skipped = invalid = 0
    index = {
        normalize_title_key(entry.get("title") or title): title
        for title, entry in existing.items()
        if normalize_title_key(entry.get("title") or title)
    }
    for title, entry in new_papers.items():
        if not entry.get("labels") or not entry.get("pipeline_stages"):
            invalid += 1
            continue
        status = upsert_paper(existing, index, title, entry, no_overwrite=args.no_overwrite)
        if status == "added":
            added += 1
        elif status == "updated":
            updated += 1
        elif status == "skipped":
            skipped += 1
        else:
            invalid += 1

    print(f"Deduped existing duplicates: {existing_duplicates}", file=sys.stderr)
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
