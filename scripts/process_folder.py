#!/usr/bin/env python3
"""Process rawdata files through extract -> label -> merge -> build."""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from venues import canonical_venue_from_filename

REPO_ROOT = Path(__file__).resolve().parents[1]
RAWDATA_DIR = REPO_ROOT / "data" / "rawdata"
VENUES_PATH = REPO_ROOT / "data" / "venues.json"
SCRIPT_DIR = Path(__file__).resolve().parent


def canonical_venue(path):
    return canonical_venue_from_filename(path)


def load_processed():
    if VENUES_PATH.exists():
        return set(json.load(open(VENUES_PATH, encoding="utf-8")))
    return set()


def save_processed(venues):
    VENUES_PATH.parent.mkdir(parents=True, exist_ok=True)
    json.dump(sorted(venues), open(VENUES_PATH, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


def raw_files(directory):
    exts = {".bib", ".json", ".csv", ".html", ".htm"}
    return sorted(p for p in Path(directory).rglob("*") if p.suffix.lower() in exts)


def run(script, args, stdout_path=None):
    cmd = [sys.executable, str(SCRIPT_DIR / script)] + [str(a) for a in args]
    print("$ " + " ".join(cmd), file=sys.stderr)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    if stdout_path:
        with open(stdout_path, "w", encoding="utf-8") as out:
            result = subprocess.run(cmd, stdout=out, stderr=sys.stderr, env=env)
    else:
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=sys.stderr, env=env)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Process rawdata folder")
    parser.add_argument("directory", nargs="?", default=str(RAWDATA_DIR))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--filter-only", action="store_true")
    parser.add_argument("--no-rebuild", action="store_true")
    args = parser.parse_args()

    files = raw_files(args.directory)
    processed = load_processed()
    grouped = {}
    for path in files:
        grouped.setdefault(canonical_venue(path), []).append(path)

    new_groups = {venue: paths for venue, paths in grouped.items() if venue not in processed}
    print(f"Found {len(grouped)} venues; {len(new_groups)} new", file=sys.stderr)
    for venue, paths in sorted(new_groups.items()):
        print(f"  {venue}: {[p.name for p in paths]}", file=sys.stderr)

    if args.dry_run:
        return

    for venue, paths in sorted(new_groups.items()):
        with tempfile.TemporaryDirectory(prefix=f"text2sql_{venue}_") as tmp:
            extracted = {}
            for path in paths:
                extracted_path = Path(tmp) / f"{path.stem}.json"
                if not run("extract_papers.py", [path], extracted_path):
                    continue
                extracted.update(json.load(open(extracted_path, encoding="utf-8")))
            if not extracted:
                continue

            all_path = Path(tmp) / "extracted.json"
            ndss_path = Path(tmp) / "ndss.json"
            labeled_path = Path(tmp) / "labeled.json"
            json.dump(extracted, open(all_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
            if "ndss" in venue.lower() and any(not item.get("abstract") for item in extracted.values()):
                if run("fetch_ndss_abstracts.py", [all_path, "-o", ndss_path]):
                    all_path = ndss_path
            phase = "filter" if args.filter_only else "all"
            if not run("label_papers.py", [all_path, "--phase", phase, "-o", labeled_path]):
                continue
            if not args.filter_only and run("merge_labeldata.py", [labeled_path]):
                with open(labeled_path, encoding="utf-8") as f:
                    labeled = json.load(f)
                if labeled:
                    processed.add(venue)
                    save_processed(processed)
                else:
                    print(f"  No relevant papers for {venue}; venue not marked processed", file=sys.stderr)

    if not args.filter_only and not args.no_rebuild:
        run("build_site.py", [])


if __name__ == "__main__":
    main()
