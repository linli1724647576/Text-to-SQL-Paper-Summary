#!/usr/bin/env python3
"""Validate generated Text-to-SQL dataset before publishing."""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from paper_utils import normalize_title_key
from venues import (
    README_CCF_A_JOURNALS,
    iter_ccf_a_venues,
    normalize_entry_venue,
    publication_category,
    venue_base_name,
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


def report_failures(reports_dir):
    reports_dir = Path(reports_dir)
    failures = []
    warnings = []
    for name in ("fetch_failures.json", "official_accepted_failures.json"):
        payload = load_json(reports_dir / name, {})
        failures.extend(payload.get("failures") or [])
        warnings.extend(payload.get("warnings") or [])
    return failures, warnings


def expected_dblp_conference_count(from_year, to_year):
    return sum(1 for _ in iter_ccf_a_venues(from_year, to_year, tracks=["AI", "DB", "SE"]))


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
            metrics["unique_title_drop_ratio"] = round(drop_ratio, 6)
            if drop_ratio > BALANCED_DROP_LIMIT:
                fatal_errors.append(
                    f"unique paper count dropped by {drop_ratio:.2%}; limit is {BALANCED_DROP_LIMIT:.0%}"
                )

    www_mismatches = []
    category_counts = {}
    for title, entry in papers.items():
        normalized = normalize_entry_venue(entry)
        category = publication_category(entry)
        category_counts[category] = category_counts.get(category, 0) + 1
        if venue_base_name(normalized) == "WWW" and category != "交叉/综合/新兴":
            www_mismatches.append(entry.get("title") or title)
    metrics["category_counts"] = dict(sorted(category_counts.items()))
    if www_mismatches:
        fatal_errors.append(f"WWW papers outside cross category: {www_mismatches[:10]}")

    coverage = journal_rawdata_coverage(args.rawdata_dir, args.from_year, args.to_year)
    metrics["readme_journal_rawdata_files"] = coverage
    missing_journals = [venue for venue, files in coverage.items() if not files]
    if missing_journals:
        fatal_errors.append(
            f"README journal rawdata missing for {args.from_year}-{args.to_year}: {', '.join(missing_journals)}"
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
