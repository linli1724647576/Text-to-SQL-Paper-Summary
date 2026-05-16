#!/usr/bin/env python3
"""Process rawdata files through extract -> label -> merge -> build."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from label_papers import RELEVANCE_POLICY_VERSION
from venues import canonical_venue_from_filename

REPO_ROOT = Path(__file__).resolve().parents[1]
RAWDATA_DIR = REPO_ROOT / "data" / "rawdata"
AUTODATA_DIR = REPO_ROOT / "data" / "autocrawl"
VENUES_PATH = REPO_ROOT / "data" / "venues.json"
SCRIPT_DIR = Path(__file__).resolve().parent
SENTINEL_VERSION = 2
PROCESSING_FINGERPRINT_FILES = (
    "extract_papers.py",
    "label_papers.py",
    "merge_labeldata.py",
    "paper_utils.py",
    "venues.py",
)


def canonical_venue(path):
    return canonical_venue_from_filename(path)


def repo_relative(path):
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def processing_fingerprint():
    files = []
    digest = hashlib.sha256()
    digest.update(f"relevance_policy:{RELEVANCE_POLICY_VERSION}".encode("utf-8"))
    for name in PROCESSING_FINGERPRINT_FILES:
        path = SCRIPT_DIR / name
        file_hash = sha256_file(path)
        files.append({"path": repo_relative(path), "sha256": file_hash})
        digest.update(name.encode("utf-8"))
        digest.update(file_hash.encode("ascii"))
    return {
        "relevance_policy_version": RELEVANCE_POLICY_VERSION,
        "files": files,
        "sha256": digest.hexdigest(),
    }


def fingerprint_group(paths, processing):
    return {
        "files": [
            {
                "path": repo_relative(path),
                "sha256": sha256_file(path),
            }
            for path in sorted(paths, key=repo_relative)
        ],
        "processing": processing,
    }


def load_processed():
    if not VENUES_PATH.exists():
        return {"version": SENTINEL_VERSION, "venues": {}}
    with open(VENUES_PATH, encoding="utf-8") as f:
        payload = json.load(f)
    if isinstance(payload, dict) and isinstance(payload.get("venues"), dict):
        return {"version": SENTINEL_VERSION, "venues": payload["venues"]}
    return {"version": SENTINEL_VERSION, "venues": {}}


def save_processed(processed):
    VENUES_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": SENTINEL_VERSION,
        "venues": {
            venue: {
                "files": sorted(record.get("files", []), key=lambda item: item["path"]),
                "processing": record.get("processing", {}),
            }
            for venue, record in sorted(processed.get("venues", {}).items())
        },
    }
    with open(VENUES_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def raw_files(directory):
    exts = {".bib", ".json", ".csv", ".html", ".htm"}
    ignored = {"fetch_failures.json"}
    return sorted(p for p in Path(directory).rglob("*") if p.suffix.lower() in exts and p.name not in ignored)


def supplemental_files(directory):
    path = Path(directory)
    if not path.exists():
        return []
    allowed = {"openalex.json"}
    return sorted(p for p in path.glob("*.json") if p.name in allowed or p.name.startswith("openalex-"))


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
    parser.add_argument("--no-autocrawl", action="store_true")
    args = parser.parse_args()

    files = raw_files(args.directory)
    if Path(args.directory).resolve() == RAWDATA_DIR.resolve() and not args.no_autocrawl:
        files.extend(supplemental_files(AUTODATA_DIR))
    processed = load_processed()
    grouped = {}
    for path in files:
        grouped.setdefault(canonical_venue(path), []).append(path)

    processing = processing_fingerprint()
    fingerprints = {venue: fingerprint_group(paths, processing) for venue, paths in grouped.items()}
    changed_groups = {
        venue: paths
        for venue, paths in grouped.items()
        if processed["venues"].get(venue) != fingerprints[venue]
    }
    stale_groups = sorted(set(processed["venues"]) - set(grouped))
    print(f"Found {len(grouped)} venues; {len(changed_groups)} changed; {len(stale_groups)} stale", file=sys.stderr)
    for venue, paths in sorted(changed_groups.items()):
        print(f"  {venue}: {[p.name for p in paths]}", file=sys.stderr)
    for venue in stale_groups:
        print(f"  stale {venue}", file=sys.stderr)

    if args.dry_run:
        return

    for venue in stale_groups:
        processed["venues"].pop(venue, None)
    if stale_groups and not changed_groups:
        save_processed(processed)

    for venue, paths in sorted(changed_groups.items()):
        with tempfile.TemporaryDirectory(prefix=f"text2sql_{venue}_") as tmp:
            extracted = {}
            extract_failed = False
            for path in paths:
                extracted_path = Path(tmp) / f"{path.stem}.json"
                if not run("extract_papers.py", [path], extracted_path):
                    extract_failed = True
                    continue
                extracted.update(json.load(open(extracted_path, encoding="utf-8")))
            if extract_failed:
                print(f"WARN: extraction failed for at least one file in {venue}; keeping old fingerprint", file=sys.stderr)
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
                processed["venues"][venue] = fingerprints[venue]
                save_processed(processed)

    if stale_groups:
        save_processed(processed)

    if not args.filter_only and not args.no_rebuild:
        run("build_site.py", [])


if __name__ == "__main__":
    main()
