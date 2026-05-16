#!/usr/bin/env python3
"""Combine, label, and merge official accepted-paper rawdata."""

import argparse
import json
from pathlib import Path

from label_papers import filter_papers, label_papers
from paper_utils import dedupe_papers, normalize_title_key, upsert_paper

REPO_ROOT = Path(__file__).resolve().parents[1]
RAWDATA_DIR = REPO_ROOT / "data" / "rawdata"
AUTODATA_DIR = REPO_ROOT / "data" / "autocrawl"
LABELDATA_PATH = REPO_ROOT / "data" / "labeldata" / "labeldata.json"


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def combine_accepted(rawdata_dir):
    combined = {}
    files = sorted(Path(rawdata_dir).glob("*/*-accepted.json"))
    for path in files:
        combined.update(load_json(path))
    return files, combined


def merge_labeled(labeled, labeldata_path, no_overwrite=True):
    existing = load_json(labeldata_path) if labeldata_path.exists() else {}
    existing, existing_duplicates = dedupe_papers(existing)
    index = {
        normalize_title_key(entry.get("title") or title): title
        for title, entry in existing.items()
        if normalize_title_key(entry.get("title") or title)
    }
    added = updated = skipped = invalid = 0
    for title, entry in labeled.items():
        if not entry.get("labels") or not entry.get("pipeline_stages"):
            invalid += 1
            continue
        status = upsert_paper(existing, index, title, entry, no_overwrite=no_overwrite)
        if status == "added":
            added += 1
        elif status == "updated":
            updated += 1
        elif status == "skipped":
            skipped += 1
        else:
            invalid += 1
    write_json(labeldata_path, dict(sorted(existing.items())))
    return added, updated, skipped, invalid, len(existing), existing_duplicates


def main():
    parser = argparse.ArgumentParser(description="Process official accepted-paper rawdata")
    parser.add_argument("--rawdata-dir", default=str(RAWDATA_DIR))
    parser.add_argument("--output-dir", default=str(AUTODATA_DIR))
    parser.add_argument("--labeldata", default=str(LABELDATA_PATH))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    combined_path = output_dir / "official_accepted_all.json"
    labeled_path = output_dir / "official_accepted_all_labeled.json"

    files, combined = combine_accepted(args.rawdata_dir)
    write_json(combined_path, combined)
    print(f"Combined {len(files)} files and {len(combined)} official accepted candidates")

    relevant = filter_papers(combined)
    labeled = label_papers(relevant)
    write_json(labeled_path, labeled)
    print(f"Filtered and labeled {len(labeled)} relevant papers")

    stats = merge_labeled(labeled, Path(args.labeldata), no_overwrite=not args.overwrite)
    added, updated, skipped, invalid, total, existing_duplicates = stats
    print(f"Deduped existing duplicates: {existing_duplicates}")
    print(f"Added: {added}")
    print(f"Updated: {updated}")
    print(f"Skipped: {skipped}")
    print(f"Invalid: {invalid}")
    print(f"Total: {total}")


if __name__ == "__main__":
    main()
