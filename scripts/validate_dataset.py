#!/usr/bin/env python3
"""Validate generated Text-to-SQL dataset before publishing."""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from label_papers import relevance_level
from paper_utils import normalize_title_key
from taxonomy import DEPRECATED_TOPIC_LABELS
from venues import (
    ALL_CCF_A_VENUES,
    ARXIV_VENUE,
    README_CCF_A_JOURNALS,
    canonical_venue_from_filename,
    iter_ccf_a_venues,
    normalize_entry_venue,
    publication_category,
    venue_base_name,
    www_supported_by_source,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LABELDATA = REPO_ROOT / "data" / "labeldata" / "labeldata.json"
DEFAULT_VENUES = REPO_ROOT / "data" / "venues.json"
DEFAULT_RAWDATA = REPO_ROOT / "data" / "rawdata"
DEFAULT_REPORTS = REPO_ROOT / "data" / "reports"
DEFAULT_REPORT = DEFAULT_REPORTS / "update_summary.json"
BALANCED_OTHER_RATIO_WARNING = 0.30
BALANCED_DROP_LIMIT = 0.05
BALANCED_DBLP_FAILURE_LIMIT = 0.30

CCF_RECALL_CANARIES = [
    {
        "title": "ValueNet: A Natural Language-to-SQL System that Learns from Database Information",
        "venue": "ICDE",
        "year": "2021",
    },
    {
        "title": "DIN-SQL: Decomposed In-Context Learning of Text-to-SQL with Self-Correction",
        "venue": "NeurIPS",
        "year": "2023",
    },
    {
        "title": "The Dawn of Natural Language to SQL: Are We Fully Ready?",
        "venue": "VLDB",
        "year": "2024",
    },
    {
        "title": "Combining Small Language Models and Large Language Models for Zero-Shot NL2SQL",
        "venue": "VLDB",
        "year": "2024",
    },
]


def load_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_baseline(spec, warnings):
    if not spec:
        return None
    if ":" in spec and not Path(spec).exists():
        try:
            output = subprocess.check_output(
                ["git", "show", spec],
                cwd=REPO_ROOT,
                stderr=subprocess.STDOUT,
            )
            return json.loads(output.decode("utf-8"))
        except Exception as exc:
            warnings.append(f"baseline unavailable: {spec}: {exc}")
            return None
    path = Path(spec)
    if not path.is_absolute():
        path = REPO_ROOT / path
    try:
        return load_json(path, None)
    except Exception as exc:
        warnings.append(f"baseline unavailable: {spec}: {exc}")
        return None


def normalized_duplicate_groups(papers):
    groups = {}
    for title, entry in papers.items():
        key = normalize_title_key(entry.get("title") or title)
        if not key:
            continue
        groups.setdefault(key, []).append(entry.get("title") or title)
    return {key: titles for key, titles in groups.items() if len(titles) > 1}


def unique_title_count(papers):
    keys = {
        normalize_title_key(entry.get("title") or title)
        for title, entry in papers.items()
        if normalize_title_key(entry.get("title") or title)
    }
    return len(keys)


def run_process_dry_run():
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "process_folder.py"), "--dry-run"],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    match = re.search(r"Found\s+\d+\s+venues;\s+(\d+)\s+changed;\s+(\d+)\s+stale", output)
    if result.returncode != 0:
        return None, None, output.strip()
    if not match:
        return None, None, output.strip()
    return int(match.group(1)), int(match.group(2)), output.strip()


def journal_rawdata_coverage(rawdata_dir, from_year, to_year):
    expected = sorted({venue for venues in README_CCF_A_JOURNALS.values() for venue in venues})
    coverage = {}
    for venue in expected:
        files = []
        for year in range(from_year, to_year + 1):
            files.extend(sorted(Path(rawdata_dir).glob(f"{year}/{venue}{year}.json")))
        coverage[venue] = [path.relative_to(REPO_ROOT).as_posix() for path in files]
    return coverage


def ccf_conference_rawdata_coverage(rawdata_dir, from_year, to_year):
    coverage = {}
    for track, venue, _dblp_key, year in iter_ccf_a_venues(from_year, to_year, tracks=["AI", "DB", "SE"]):
        files = sorted((Path(rawdata_dir) / str(year)).glob(f"{venue}{year}*.json"))
        coverage[f"{venue}{year}"] = {
            "track": track,
            "venue": venue,
            "year": year,
            "files": [path.relative_to(REPO_ROOT).as_posix() for path in files],
            "present": bool(files),
        }
    return coverage


def report_failures(reports_dir):
    reports_dir = Path(reports_dir)
    failures = []
    warnings = []
    for name in ("fetch_failures.json", "official_accepted_failures.json"):
        payload = load_json(reports_dir / name, {})
        failures.extend(payload.get("failures") or [])
        warnings.extend(payload.get("warnings") or [])
    return failures, warnings


def quality_pruned_count(reports_dir, baseline_papers, current_papers):
    payload = load_json(Path(reports_dir) / "pruned_irrelevant.json", {})
    removed = payload.get("removed") or []
    baseline_keys = {
        normalize_title_key(entry.get("title") or title)
        for title, entry in (baseline_papers or {}).items()
        if normalize_title_key(entry.get("title") or title)
    }
    current_keys = {
        normalize_title_key(entry.get("title") or title)
        for title, entry in (current_papers or {}).items()
        if normalize_title_key(entry.get("title") or title)
    }
    verified = 0
    for item in removed:
        entry = item.get("entry") or item
        title = entry.get("title") or item.get("title") or ""
        key = normalize_title_key(title)
        if not key or key not in baseline_keys or key in current_keys:
            continue
        if relevance_level(title, entry.get("abstract", ""), entry.get("keywords", "")) == "irrelevant":
            verified += 1
    return verified


def source_policy_removed_count(baseline_papers, current_papers):
    current_keys = {
        normalize_title_key(entry.get("title") or title)
        for title, entry in (current_papers or {}).items()
        if normalize_title_key(entry.get("title") or title)
    }
    removed = 0
    for title, entry in (baseline_papers or {}).items():
        key = normalize_title_key(entry.get("title") or title)
        if not key or key in current_keys:
            continue
        if entry.get("openalex_id") or entry.get("semantic_scholar_id"):
            removed += 1
    return removed


def expected_dblp_conference_count(from_year, to_year):
    return sum(1 for _ in iter_ccf_a_venues(from_year, to_year, tracks=["AI", "DB", "SE"]))


def recall_canary_status(papers):
    index = {
        normalize_title_key(entry.get("title") or title): (title, entry)
        for title, entry in papers.items()
        if normalize_title_key(entry.get("title") or title)
    }
    results = []
    for canary in CCF_RECALL_CANARIES:
        key = normalize_title_key(canary["title"])
        title, entry = index.get(key, ("", {}))
        venue = normalize_entry_venue(entry) if entry else ""
        year = str(entry.get("year") or "") if entry else ""
        level = relevance_level(title, entry.get("abstract", ""), entry.get("keywords", "")) if entry else ""
        ok = bool(entry) and venue == canary["venue"] and year == canary["year"] and level != "irrelevant"
        results.append(
            {
                "title": canary["title"],
                "expected_venue": canary["venue"],
                "expected_year": canary["year"],
                "found": bool(entry),
                "actual_title": title,
                "actual_venue": venue,
                "actual_year": year,
                "relevance_level": level,
                "ok": ok,
            }
        )
    return results


def acl_findings_tagged_as_acl(papers):
    findings = []
    for title, entry in papers.items():
        if normalize_entry_venue(entry) != "ACL":
            continue
        source = " ".join(str(entry.get(field, "")) for field in ("booktitle", "journal", "container", "source"))
        if "findings" in source.lower():
            findings.append(entry.get("title") or title)
    return findings


def current_source_kind(entry):
    venue = normalize_entry_venue(entry)
    base = venue_base_name(venue)
    if venue == ARXIV_VENUE:
        return "arxiv"
    if base in ALL_CCF_A_VENUES:
        return "ccf_venue"
    if entry.get("openalex_id") or entry.get("semantic_scholar_id"):
        return "supplemental_or_other"
    return "other"


def load_raw_records(path):
    try:
        payload = load_json(path, {})
    except Exception:
        return []
    if isinstance(payload, dict):
        return list(payload.items())
    if isinstance(payload, list):
        return [(item.get("title", ""), item) for item in payload if isinstance(item, dict)]
    return []


def raw_source_kind(path):
    name = path.name.lower()
    if "arxiv" in name or "arxiv" in path.as_posix().lower():
        return "arxiv"
    if "-accepted" in name:
        return "official_accepted"
    return "dblp"


def rawdata_diagnostics(rawdata_dir, papers):
    raw_by_venue_year = {}
    arxiv_keys = set()
    ccf_raw_keys = set()
    for path in sorted(Path(rawdata_dir).glob("*/*.json")):
        if path.name in {"fetch_failures.json"}:
            continue
        records = load_raw_records(path)
        source = raw_source_kind(path)
        venue_key = canonical_venue_from_filename(path)
        raw_by_venue_year.setdefault(
            venue_key,
            {"raw_candidates": 0, "official_accepted": 0, "dblp": 0, "arxiv": 0, "relevant_papers": 0},
        )
        raw_by_venue_year[venue_key]["raw_candidates"] += len(records)
        raw_by_venue_year[venue_key][source] += len(records)
        for title, entry in records:
            if not isinstance(entry, dict):
                continue
            key = normalize_title_key(entry.get("title") or title)
            if not key:
                continue
            if source == "arxiv":
                arxiv_keys.add(key)
            elif venue_base_name(venue_key) in ALL_CCF_A_VENUES:
                ccf_raw_keys.add(key)

    for title, entry in papers.items():
        venue = normalize_entry_venue(entry)
        year = str(entry.get("year") or "")
        if not year:
            continue
        key = f"{venue_base_name(venue)}{year}" if venue != ARXIV_VENUE else "ArXiv"
        raw_by_venue_year.setdefault(
            key,
            {"raw_candidates": 0, "official_accepted": 0, "dblp": 0, "arxiv": 0, "relevant_papers": 0},
        )
        raw_by_venue_year[key]["relevant_papers"] += 1

    ccf_label_keys = {
        normalize_title_key(entry.get("title") or title)
        for title, entry in papers.items()
        if venue_base_name(normalize_entry_venue(entry)) in ALL_CCF_A_VENUES
    }
    return {
        "venue_year": dict(sorted(raw_by_venue_year.items())),
        "arxiv_raw_titles_overridden_by_ccf": len(arxiv_keys & ccf_raw_keys & ccf_label_keys),
    }


def validate(args):
    fatal_errors = []
    warnings = []
    metrics = {}

    papers = load_json(args.labeldata, {})
    if not isinstance(papers, dict):
        fatal_errors.append("labeldata is not a JSON object")
        papers = {}

    venues_payload = load_json(args.venues, {})
    venues_records = venues_payload.get("venues") if isinstance(venues_payload, dict) else None
    metrics["venues_sentinel_version"] = venues_payload.get("version") if isinstance(venues_payload, dict) else None
    metrics["venues_sentinel_count"] = len(venues_records) if isinstance(venues_records, dict) else 0
    if venues_payload and (venues_payload.get("version") != 2 or not isinstance(venues_records, dict)):
        fatal_errors.append("venues sentinel must be version 2 with a venues object")

    duplicate_groups = normalized_duplicate_groups(papers)
    metrics["paper_count"] = len(papers)
    metrics["unique_title_count"] = unique_title_count(papers)
    metrics["normalized_duplicate_groups"] = len(duplicate_groups)
    if duplicate_groups:
        sample = list(duplicate_groups.values())[:5]
        fatal_errors.append(f"normalized title duplicate groups found: {len(duplicate_groups)}; sample={sample}")

    changed, stale, dry_run_output = run_process_dry_run()
    metrics["process_folder_changed"] = changed
    metrics["process_folder_stale"] = stale
    if changed is None or stale is None:
        fatal_errors.append(f"process_folder.py --dry-run could not be parsed: {dry_run_output[:500]}")
    elif changed or stale:
        fatal_errors.append(f"process_folder.py --dry-run reports changed={changed}, stale={stale}")

    baseline = load_baseline(args.baseline, warnings)
    if baseline is not None:
        baseline_count = unique_title_count(baseline)
        metrics["baseline_unique_title_count"] = baseline_count
        if baseline_count:
            drop_ratio = (baseline_count - metrics["unique_title_count"]) / baseline_count
            pruned_count = quality_pruned_count(args.reports_dir, baseline, papers)
            source_removed_count = source_policy_removed_count(baseline, papers)
            adjusted_drop_ratio = (
                max(0, baseline_count - metrics["unique_title_count"] - pruned_count - source_removed_count)
                / baseline_count
            )
            metrics["unique_title_drop_ratio"] = round(drop_ratio, 6)
            metrics["quality_pruned_irrelevant_count"] = pruned_count
            metrics["source_policy_removed_count"] = source_removed_count
            metrics["adjusted_unique_title_drop_ratio"] = round(adjusted_drop_ratio, 6)
            if adjusted_drop_ratio > BALANCED_DROP_LIMIT:
                fatal_errors.append(
                    f"unexplained unique paper count dropped by {adjusted_drop_ratio:.2%}; limit is {BALANCED_DROP_LIMIT:.0%}"
                )

    www_mismatches = []
    unsupported_www = []
    irrelevant_records = []
    category_counts = {}
    source_counts = {}
    deprecated_topic_records = []
    for title, entry in papers.items():
        normalized = normalize_entry_venue(entry)
        category = publication_category(entry)
        category_counts[category] = category_counts.get(category, 0) + 1
        source_kind = current_source_kind(entry)
        source_counts[source_kind] = source_counts.get(source_kind, 0) + 1
        deprecated = sorted(set(entry.get("labels") or []) & DEPRECATED_TOPIC_LABELS)
        if deprecated:
            deprecated_topic_records.append({"title": entry.get("title") or title, "labels": deprecated})
        if venue_base_name(normalized) == "WWW" and category != "交叉/综合/新兴":
            www_mismatches.append(entry.get("title") or title)
        if venue_base_name(normalized) == "WWW" and not www_supported_by_source(entry):
            unsupported_www.append(entry.get("title") or title)
        level = relevance_level(title, entry.get("abstract", ""), entry.get("keywords", ""))
        if level == "irrelevant":
            irrelevant_records.append(entry.get("title") or title)
    metrics["category_counts"] = dict(sorted(category_counts.items()))
    metrics["source_counts"] = dict(sorted(source_counts.items()))
    metrics["irrelevant_records"] = len(irrelevant_records)
    metrics["unsupported_www_records"] = len(unsupported_www)
    metrics["deprecated_topic_label_records"] = len(deprecated_topic_records)
    if www_mismatches:
        fatal_errors.append(f"WWW papers outside cross category: {www_mismatches[:10]}")
    if unsupported_www:
        fatal_errors.append(f"WWW papers lack high-confidence WWW source: {unsupported_www[:10]}")
    if irrelevant_records:
        fatal_errors.append(f"irrelevant records under current relevance rules: {len(irrelevant_records)}; sample={irrelevant_records[:10]}")
    if deprecated_topic_records:
        fatal_errors.append(f"deprecated topic labels remain: {deprecated_topic_records[:10]}")

    canaries = recall_canary_status(papers)
    missing_canaries = [item for item in canaries if not item["ok"]]
    metrics["ccf_recall_canaries"] = canaries
    if missing_canaries:
        fatal_errors.append(f"CCF-A recall canaries failed: {missing_canaries[:5]}")

    acl_findings = acl_findings_tagged_as_acl(papers)
    metrics["acl_findings_tagged_as_acl"] = len(acl_findings)
    if acl_findings:
        fatal_errors.append(f"ACL Findings records tagged as ACL CCF-A: {acl_findings[:10]}")

    metrics["rawdata_diagnostics"] = rawdata_diagnostics(args.rawdata_dir, papers)

    coverage = journal_rawdata_coverage(args.rawdata_dir, args.from_year, args.to_year)
    metrics["readme_journal_rawdata_files"] = coverage
    missing_journals = [venue for venue, files in coverage.items() if not files]
    if missing_journals:
        fatal_errors.append(
            f"README journal rawdata missing for {args.from_year}-{args.to_year}: {', '.join(missing_journals)}"
        )

    conference_coverage = ccf_conference_rawdata_coverage(args.rawdata_dir, args.from_year, args.to_year)
    missing_conference_rawdata = [
        key for key, record in sorted(conference_coverage.items()) if not record["present"]
    ]
    metrics["ccf_conference_rawdata_missing"] = missing_conference_rawdata
    if missing_conference_rawdata:
        fatal_errors.append(
            f"CCF-A conference rawdata missing for {args.from_year}-{args.to_year}: "
            + ", ".join(missing_conference_rawdata)
        )

    failures, report_warnings = report_failures(args.reports_dir)
    metrics["fetch_failure_count"] = len(failures)
    metrics["fetch_warning_count"] = len(report_warnings)
    expected_conferences = expected_dblp_conference_count(args.from_year, args.to_year)
    dblp_conference_failures = [
        item for item in failures if item.get("source_type") == "dblp-conference" and item.get("status") == "failed"
    ]
    metrics["dblp_conference_failures"] = len(dblp_conference_failures)
    metrics["expected_dblp_conferences"] = expected_conferences
    if expected_conferences:
        failure_ratio = len(dblp_conference_failures) / expected_conferences
        metrics["dblp_conference_failure_ratio"] = round(failure_ratio, 6)
        if failure_ratio > BALANCED_DBLP_FAILURE_LIMIT:
            fatal_errors.append(
                f"DBLP conference failures are {failure_ratio:.2%}; limit is {BALANCED_DBLP_FAILURE_LIMIT:.0%}"
            )

    other_count = category_counts.get("其他", 0)
    if papers:
        other_ratio = other_count / len(papers)
        metrics["other_ratio"] = round(other_ratio, 6)
        if other_ratio > BALANCED_OTHER_RATIO_WARNING:
            warnings.append(f"high Other category ratio: {other_ratio:.2%}")

    if not os.environ.get("SEMANTIC_SCHOLAR_API_KEY"):
        warnings.append("SEMANTIC_SCHOLAR_API_KEY is not set; Semantic Scholar rate limits may be lower")

    rate_limited = [
        item for item in failures + report_warnings if "429" in str(item.get("error", "")) or item.get("status") == "partial_failed"
    ]
    if rate_limited:
        warnings.append(f"partial source failures or rate-limit events: {len(rate_limited)}")

    status = "failed" if fatal_errors else "ok"
    payload = {
        "mode": args.mode,
        "status": status,
        "fatal_errors": fatal_errors,
        "warnings": warnings,
        "metrics": metrics,
    }
    report_path = Path(args.write_report)
    if not report_path.is_absolute():
        report_path = REPO_ROOT / report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(json.dumps(payload, indent=2, ensure_ascii=False), file=sys.stderr)
    return 1 if fatal_errors else 0


def main():
    parser = argparse.ArgumentParser(description="Validate Text-to-SQL dataset")
    parser.add_argument("--mode", choices=["balanced"], default="balanced")
    parser.add_argument("--baseline")
    parser.add_argument("--labeldata", default=str(DEFAULT_LABELDATA))
    parser.add_argument("--venues", default=str(DEFAULT_VENUES))
    parser.add_argument("--rawdata-dir", default=str(DEFAULT_RAWDATA))
    parser.add_argument("--reports-dir", default=str(DEFAULT_REPORTS))
    parser.add_argument("--write-report", default=str(DEFAULT_REPORT))
    parser.add_argument("--from-year", type=int, default=2020)
    parser.add_argument("--to-year", type=int, default=2026)
    args = parser.parse_args()
    raise SystemExit(validate(args))


if __name__ == "__main__":
    main()
