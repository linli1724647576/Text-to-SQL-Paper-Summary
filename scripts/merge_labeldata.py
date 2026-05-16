#!/usr/bin/env python3
"""Merge classified papers into data/labeldata/labeldata.json."""

import argparse
import json
import os
import sys
from pathlib import Path

from label_papers import relevance_level, with_relevance_metadata
from paper_utils import dedupe_papers, normalize_paper_metadata, normalize_title_key, upsert_paper

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LABELDATA = REPO_ROOT / "data" / "labeldata" / "labeldata.json"
DEFAULT_PRUNE_REPORT = REPO_ROOT / "data" / "reports" / "pruned_irrelevant.json"


def prune_irrelevant_papers(papers):
    kept = {}
    removed = []
    for title, entry in papers.items():
        level = relevance_level(title, entry.get("abstract", ""), entry.get("keywords", ""))
        normalized = normalize_paper_metadata(with_relevance_metadata(title, entry))
        if level == "irrelevant":
            removed.append(
                {
                    "title": normalized.get("title") or title,
                    "venue": normalized.get("venue", ""),
                    "year": normalized.get("year", ""),
                    "doi": normalized.get("doi", ""),
                    "url": normalized.get("url", ""),
                    "reason": "relevance_level=irrelevant",
                    "entry": normalized,
                }
            )
            continue
        kept[normalized.get("title") or title] = normalized
    return kept, removed


def write_prune_report(path, removed):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    combined = []
    seen = set()
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                existing_payload = json.load(f)
            combined.extend(existing_payload.get("removed") or [])
        except Exception:
            combined = []
    combined.extend(removed)
    deduped = []
    for item in combined:
        entry = item.get("entry") or item
        title = entry.get("title") or item.get("title") or ""
        key = normalize_title_key(title)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    payload = {
        "summary": {
            "removed_count": len(deduped),
            "newly_removed_count": len(removed),
        },
        "removed": deduped,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Merge labeled papers")
    parser.add_argument("input", nargs="?")
    parser.add_argument("--labeldata", default=str(DEFAULT_LABELDATA))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-overwrite", action="store_true")
    parser.add_argument("--dedupe-only", action="store_true")
    parser.add_argument("--prune-irrelevant", action="store_true")
    parser.add_argument("--prune-report", default=str(DEFAULT_PRUNE_REPORT))
    args = parser.parse_args()

    if not args.input and not args.dedupe_only:
        parser.error("input is required unless --dedupe-only is set")

    if os.path.exists(args.labeldata):
        with open(args.labeldata, encoding="utf-8") as f:
            existing = json.load(f)
    else:
        existing = {}
    existing, existing_duplicates = dedupe_papers(existing)
    removed = []
    if args.prune_irrelevant:
        existing, removed = prune_irrelevant_papers(existing)
        existing, prune_duplicates = dedupe_papers(existing)
        existing_duplicates += prune_duplicates

    if args.dedupe_only:
        print(f"Deduped existing duplicates: {existing_duplicates}", file=sys.stderr)
        if args.prune_irrelevant:
            print(f"Pruned irrelevant: {len(removed)}", file=sys.stderr)
        print(f"Total: {len(existing)}", file=sys.stderr)
        if not args.dry_run:
            Path(args.labeldata).parent.mkdir(parents=True, exist_ok=True)
            with open(args.labeldata, "w", encoding="utf-8") as f:
                json.dump(dict(sorted(existing.items())), f, indent=2, ensure_ascii=False)
            if args.prune_irrelevant:
                write_prune_report(args.prune_report, removed)
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
        if relevance_level(title, entry.get("abstract", ""), entry.get("keywords", "")) == "irrelevant":
            invalid += 1
            continue
        entry = with_relevance_metadata(title, entry)
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
    if args.prune_irrelevant:
        print(f"Pruned irrelevant: {len(removed)}", file=sys.stderr)
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
    if args.prune_irrelevant:
        write_prune_report(args.prune_report, removed)


if __name__ == "__main__":
    main()
