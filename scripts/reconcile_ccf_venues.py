#!/usr/bin/env python3
"""Promote existing papers to CCF-A venues when rawdata proves acceptance."""

import argparse
import json
from pathlib import Path

from label_papers import relevance_level
from paper_utils import normalize_title_key
from venues import (
    AI_CCF_A_VENUES,
    CROSS_CCF_A_VENUES,
    DATABASE_CCF_A_VENUES,
    README_CCF_A_JOURNALS,
    SE_CCF_A_VENUES,
    canonical_venue_from_filename,
    normalize_venue_name,
    publication_category,
    venue_base_name,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LABELDATA = REPO_ROOT / "data" / "labeldata" / "labeldata.json"
DEFAULT_RAWDATA = REPO_ROOT / "data" / "rawdata"
DEFAULT_REPORT = REPO_ROOT / "data" / "reports" / "ccf_venue_reconciliation.json"

ALL_CCF = AI_CCF_A_VENUES | DATABASE_CCF_A_VENUES | SE_CCF_A_VENUES | CROSS_CCF_A_VENUES
README_JOURNALS = {venue for venues in README_CCF_A_JOURNALS.values() for venue in venues}
CCF_CONFERENCES = ALL_CCF - README_JOURNALS


def load_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def raw_entry_title(title, entry):
    return (entry.get("title") if isinstance(entry, dict) else "") or title


def venue_rank(venue):
    base = venue_base_name(venue)
    if base in CCF_CONFERENCES:
        return 3
    if base in README_JOURNALS:
        return 2
    if base == "ArXiv":
        return 1
    return 0


def source_matches_venue(value, target):
    return venue_base_name(normalize_venue_name(value)) == target or venue_base_name(value) == target


def iter_ccf_raw_evidence(rawdata_dir):
    for path in sorted(Path(rawdata_dir).glob("*/*.json")):
        raw_venue = venue_base_name(canonical_venue_from_filename(path))
        if raw_venue not in ALL_CCF:
            continue
        data = load_json(path, {})
        if not isinstance(data, dict):
            continue
        for title, entry in data.items():
            if not isinstance(entry, dict):
                continue
            raw_title = raw_entry_title(title, entry)
            key = normalize_title_key(raw_title)
            if not key:
                continue
            yield key, raw_venue, raw_title, entry, path


def best_evidence(existing, candidate):
    if existing is None:
        return candidate
    existing_rank = venue_rank(existing["venue"])
    candidate_rank = venue_rank(candidate["venue"])
    if candidate_rank != existing_rank:
        return candidate if candidate_rank > existing_rank else existing
    existing_year = str(existing["entry"].get("year") or "")
    candidate_year = str(candidate["entry"].get("year") or "")
    if candidate_year > existing_year:
        return candidate
    return existing


def reconcile(labeldata, rawdata_dir):
    index = {
        normalize_title_key(entry.get("title") or title): title
        for title, entry in labeldata.items()
        if normalize_title_key(entry.get("title") or title)
    }
    evidence = {}
    for key, venue, raw_title, entry, path in iter_ccf_raw_evidence(rawdata_dir):
        if key not in index:
            continue
        label_title = index[key]
        label_entry = labeldata[label_title]
        if relevance_level(label_title, label_entry.get("abstract", ""), label_entry.get("keywords", "")) == "irrelevant":
            continue
        candidate = {
            "label_title": label_title,
            "venue": venue,
            "raw_title": raw_title,
            "entry": entry,
            "path": path.relative_to(REPO_ROOT).as_posix(),
        }
        evidence[label_title] = best_evidence(evidence.get(label_title), candidate)

    changes = []
    for title, item in sorted(evidence.items()):
        entry = labeldata[title]
        current = venue_base_name(entry.get("venue", ""))
        target = item["venue"]
        expected_category = publication_category({"venue": target, "booktitle": target})
        needs_category_fix = entry.get("venue_track", "") != expected_category
        needs_source_fix = not (
            source_matches_venue(entry.get("booktitle", ""), target)
            or source_matches_venue(entry.get("journal", ""), target)
        )
        if venue_rank(target) < venue_rank(current):
            continue
        if venue_rank(target) == venue_rank(current) and target == current and not (needs_category_fix or needs_source_fix):
            continue
        before = {
            "venue": entry.get("venue", ""),
            "venue_track": entry.get("venue_track", ""),
            "booktitle": entry.get("booktitle", ""),
            "journal": entry.get("journal", ""),
        }
        raw_entry = item["entry"]
        entry["venue"] = target
        entry["booktitle"] = raw_entry.get("booktitle") or raw_entry.get("journal") or target
        if raw_entry.get("journal"):
            entry["journal"] = raw_entry["journal"]
        entry["venue_track"] = publication_category(entry)
        for field in ("author", "year", "url", "doi", "key"):
            if not entry.get(field) and raw_entry.get(field):
                entry[field] = raw_entry[field]
        after = {
            "venue": entry.get("venue", ""),
            "venue_track": entry.get("venue_track", ""),
            "booktitle": entry.get("booktitle", ""),
            "journal": entry.get("journal", ""),
        }
        changes.append(
            {
                "title": title,
                "from": before,
                "to": after,
                "rawdata_path": item["path"],
                "rawdata_title": item["raw_title"],
            }
        )
    return changes, len(evidence)


def main():
    parser = argparse.ArgumentParser(description="Reconcile labeldata venue fields from CCF-A rawdata evidence")
    parser.add_argument("--labeldata", default=str(DEFAULT_LABELDATA))
    parser.add_argument("--rawdata-dir", default=str(DEFAULT_RAWDATA))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    labeldata = load_json(args.labeldata, {})
    changes, evidence_count = reconcile(labeldata, args.rawdata_dir)
    promoted_count = sum(
        1 for item in changes if venue_rank(item["to"].get("venue", "")) > venue_rank(item["from"].get("venue", ""))
    )
    payload = {
        "summary": {
            "ccf_raw_evidence_matches": evidence_count,
            "updated_count": len(changes),
            "promoted_count": promoted_count,
            "metadata_fix_count": len(changes) - promoted_count,
            "already_aligned_count": evidence_count - len(changes),
        },
        "updates": changes,
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    if not args.dry_run:
        with open(args.labeldata, "w", encoding="utf-8") as f:
            json.dump(dict(sorted(labeldata.items())), f, indent=2, ensure_ascii=False)
    print(f"Updated CCF-A venue affiliations: {len(changes)}")
    print(f"Promoted from lower-priority venues: {promoted_count}")
    print(f"Wrote reconciliation report: {report_path}")


if __name__ == "__main__":
    main()
