#!/usr/bin/env python3
"""Expected source coverage for the production Text-to-SQL dataset."""

import json
from datetime import datetime, timezone
from pathlib import Path

from label_papers import relevance_level
from venues import CCF_A_VENUES, README_CCF_A_JOURNALS, iter_ccf_a_venues, iter_readme_journals

try:
    from fetch_official_accepted import OFFICIAL_ACCEPTED_URLS
except Exception:
    OFFICIAL_ACCEPTED_URLS = {}


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAWDATA = REPO_ROOT / "data" / "rawdata"

CURRENT_YEAR = 2026
TRACK_ORDER = ("AI", "DB", "SE")

CURRENT_YEAR_CONFERENCE_STATUS = {
    2026: {
        "AAAI": {
            "status": "available",
            "source_type": "dblp-conference",
            "source_url": "https://dblp.org/db/conf/aaai/aaai2026.xml",
        },
        "NeurIPS": {"status": "not_published_yet", "notes": "official main accepted source not configured"},
        "ACL": {"status": "not_published_yet", "notes": "official main accepted source not configured"},
        "CVPR": {
            "status": "available",
            "source_type": "official-accepted",
            "source_url": "https://cvpr.thecvf.com/virtual/2026/papers.html",
        },
        "ICCV": {"status": "not_applicable", "notes": "ICCV is odd-year only in the current project scope"},
        "ICML": {
            "status": "available",
            "source_type": "official-accepted",
            "source_url": "https://icml.cc/virtual/2026/papers.html",
        },
        "IJCAI": {"status": "not_published_yet", "notes": "official main accepted source not configured"},
        "SIGMOD": {"status": "available", "source_type": "official-accepted"},
        "VLDB": {
            "status": "available",
            "source_type": "dblp-conference",
            "source_url": "https://dblp.org/db/journals/pvldb/pvldb19.xml",
        },
        "ICDE": {"status": "available", "source_type": "official-accepted"},
        "KDD": {"status": "not_published_yet", "notes": "official main accepted source not configured"},
        "WWW": {"status": "available", "source_type": "official-accepted"},
        "SIGIR": {"status": "not_published_yet", "notes": "official main accepted source not configured"},
        "ICSE": {
            "status": "available",
            "source_type": "official-accepted",
            "source_url": "https://conf.researchr.org/track/icse-2026/icse-2026-research-track",
        },
        "FSE": {
            "status": "available",
            "source_type": "official-accepted",
            "source_url": "https://conf.researchr.org/track/fse-2026/fse-2026-research-papers",
        },
        "ASE": {"status": "not_published_yet", "notes": "official main accepted source not configured"},
        "ISSTA": {"status": "not_published_yet", "notes": "official main accepted source not configured"},
    }
}


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def selected_tracks(tracks):
    if not tracks:
        return set(TRACK_ORDER)
    if isinstance(tracks, str):
        tracks = [item.strip() for item in tracks.split(",") if item.strip()]
    return {str(track).strip() for track in tracks if str(track).strip()}


def relative(path):
    try:
        return Path(path).resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return Path(path).as_posix()


def load_raw_payload(path):
    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
    except Exception:
        return []
    if isinstance(payload, dict):
        return [item for item in payload.values() if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def raw_files(rawdata_dir, venue, year):
    return sorted((Path(rawdata_dir) / str(year)).glob(f"{venue}{year}*.json"))


def raw_stats(paths):
    candidates = 0
    relevant = 0
    for path in paths:
        for entry in load_raw_payload(path):
            candidates += 1
            title = entry.get("title") or ""
            if relevance_level(title, entry.get("abstract", ""), entry.get("keywords", "")) != "irrelevant":
                relevant += 1
    return candidates, relevant


def official_url(venue, year):
    return (OFFICIAL_ACCEPTED_URLS.get(venue) or {}).get(year, "")


def make_record(kind, track, venue, year, status, rawdata_dir, **extra):
    paths = raw_files(rawdata_dir, venue, year)
    candidates, relevant = raw_stats(paths)
    url = extra.get("source_url") or official_url(venue, year)
    source_type = extra.get("source_type") or ("journal" if kind == "journal" else "dblp-conference")
    return {
        "kind": kind,
        "track": track,
        "venue": venue,
        "year": int(year),
        "status": status,
        "source_type": source_type,
        "source_url": url,
        "rawdata_files": [relative(path) for path in paths],
        "rawdata_present": bool(paths),
        "raw_candidate_count": candidates,
        "relevant_candidate_count": relevant,
        "notes": extra.get("notes", ""),
    }


def expected_current_year_conferences(to_year, tracks, rawdata_dir):
    if to_year < CURRENT_YEAR:
        return []
    allowed = selected_tracks(tracks)
    status_map = CURRENT_YEAR_CONFERENCE_STATUS.get(CURRENT_YEAR, {})
    records = []
    for track in TRACK_ORDER:
        if track not in allowed:
            continue
        for venue in CCF_A_VENUES.get(track, {}):
            explicit = status_map.get(venue)
            if explicit is None:
                status = "missing_config"
                explicit = {"notes": "current-year source status is not configured"}
            else:
                status = explicit.get("status") or "missing_config"
            if official_url(venue, CURRENT_YEAR) and status != "not_applicable":
                status = "available"
            records.append(
                make_record(
                    "conference",
                    track,
                    venue,
                    CURRENT_YEAR,
                    status,
                    rawdata_dir,
                    source_type=explicit.get("source_type") or "official-accepted",
                    source_url=explicit.get("source_url", ""),
                    notes=explicit.get("notes", ""),
                )
            )
    return records


def expected_source_records(from_year=2020, to_year=2026, tracks=None, rawdata_dir=DEFAULT_RAWDATA):
    allowed = selected_tracks(tracks)
    records = []
    seen = set()
    conference_to_year = min(to_year, CURRENT_YEAR - 1)
    if from_year <= conference_to_year:
        for track, venue, _dblp_key, year in iter_ccf_a_venues(from_year, conference_to_year, tracks=allowed):
            status = "covered"
            paths = raw_files(rawdata_dir, venue, year)
            if not paths:
                status = "rawdata_missing"
            records.append(make_record("conference", track, venue, year, status, rawdata_dir))
            seen.add(("conference", venue, year))
    for record in expected_current_year_conferences(to_year, allowed, rawdata_dir):
        if record["year"] < from_year:
            continue
        key = ("conference", record["venue"], record["year"])
        if key not in seen:
            records.append(record)
            seen.add(key)
    for track, venue, _dblp_key, year in iter_readme_journals(from_year, to_year, tracks=allowed):
        status = "covered" if raw_files(rawdata_dir, venue, year) else "rawdata_missing"
        records.append(make_record("journal", track, venue, year, status, rawdata_dir))
    return records


def source_coverage_summary(records):
    summary = {
        "total": len(records),
        "covered": 0,
        "available": 0,
        "not_published_yet": 0,
        "not_applicable": 0,
        "missing_config": 0,
        "rawdata_missing": 0,
        "available_without_rawdata": 0,
    }
    for record in records:
        status = record.get("status")
        if status in summary:
            summary[status] += 1
        if status == "available" and not record.get("rawdata_present"):
            summary["available_without_rawdata"] += 1
        if status == "rawdata_missing":
            summary["rawdata_missing"] += 1
    return summary


def write_source_coverage_report(path, records, *, from_year=2020, to_year=2026, tracks=None):
    payload = {
        "version": 1,
        "generated_at": utc_now(),
        "from_year": from_year,
        "to_year": to_year,
        "tracks": sorted(selected_tracks(tracks)),
        "summary": source_coverage_summary(records),
        "records": records,
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, sort_keys=True)
    return payload


def venue_manifest(from_year=2020, to_year=2026, tracks=None, rawdata_dir=DEFAULT_RAWDATA):
    del rawdata_dir
    allowed = selected_tracks(tracks)
    seen = set()
    venues = []
    for track in TRACK_ORDER:
        if track not in allowed:
            continue
        for venue, spec in CCF_A_VENUES.get(track, {}).items():
            has_historical_year = any(
                (from_year is None or year >= from_year) and (to_year is None or year <= to_year)
                for year in spec.get("years", [])
            )
            current_status = CURRENT_YEAR_CONFERENCE_STATUS.get(CURRENT_YEAR, {}).get(venue, {})
            has_current_year = bool(
                to_year is not None
                and to_year >= CURRENT_YEAR
                and current_status.get("status") != "not_applicable"
            )
            if (has_historical_year or has_current_year) and venue not in seen:
                venues.append(venue)
                seen.add(venue)
    for track, venue, _dblp_key, year in iter_readme_journals(from_year, to_year, tracks=allowed):
        if venue not in seen:
            venues.append(venue)
            seen.add(venue)
    return venues
