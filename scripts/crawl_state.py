#!/usr/bin/env python3
"""Persistent crawl state for incremental metadata fetchers."""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


STATE_VERSION = 1
INCOMPLETE_STATUSES = {"failed", "empty", "stale"}


@dataclass
class SkipDecision:
    skip: bool
    reason: str
    record_key: str
    bootstrapped: bool = False


def utc_now():
    return datetime.now(timezone.utc)


def isoformat(dt):
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_time(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def file_time(path):
    return datetime.fromtimestamp(Path(path).stat().st_mtime, timezone.utc)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def count_json_records(path):
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    if isinstance(payload, dict):
        return len(payload)
    if isinstance(payload, list):
        return len(payload)
    return 0


def stored_path(path):
    path = Path(path)
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def empty_state():
    return {
        "version": STATE_VERSION,
        "records": {},
        "rotation": {
            "cursor": 0,
            "retry_queue": [],
            "history": [],
        },
    }


def load_state(path):
    path = Path(path)
    if not path.exists():
        return empty_state()
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        return empty_state()
    payload.setdefault("version", STATE_VERSION)
    if not isinstance(payload.get("records"), dict):
        payload["records"] = {}
    if not isinstance(payload.get("rotation"), dict):
        payload["rotation"] = {}
    payload["rotation"].setdefault("cursor", 0)
    payload["rotation"].setdefault("retry_queue", [])
    payload["rotation"].setdefault("history", [])
    return payload


def save_state(path, state):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    state["version"] = STATE_VERSION
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False, sort_keys=True)


def record_key(source_type, venue, year):
    return f"{source_type}:{str(venue).upper()}:{year}"


def is_active_year(year, now=None):
    try:
        return int(year) >= (now or utc_now()).year
    except (TypeError, ValueError):
        return False


def valid_complete_record(record, out_path):
    path = Path(out_path)
    if not record or record.get("status") != "complete" or not path.exists():
        return False
    try:
        return record.get("sha256") == sha256_file(path)
    except OSError:
        return False


def mark_complete(state, source_type, venue, year, path, *, source=None, track=None, now=None, bootstrapped=False):
    now = now or utc_now()
    key = record_key(source_type, venue, year)
    path = Path(path)
    count = count_json_records(path)
    status = "complete" if count > 0 else "empty"
    success_time = file_time(path) if bootstrapped else now
    record = {
        "venue": str(venue).upper(),
        "year": str(year),
        "source_type": source_type,
        "source": source or source_type,
        "track": track or "",
        "status": status,
        "last_attempt_at": isoformat(success_time),
        "last_success_at": isoformat(success_time) if status == "complete" else "",
        "rawdata_path": stored_path(path),
        "sha256": sha256_file(path),
        "record_count": count,
        "error": "",
    }
    state.setdefault("records", {})[key] = record
    return record


def mark_failed(state, source_type, venue, year, path, error, *, source=None, track=None, status="failed", now=None):
    now = now or utc_now()
    key = record_key(source_type, venue, year)
    path = Path(path)
    record = {
        "venue": str(venue).upper(),
        "year": str(year),
        "source_type": source_type,
        "source": source or source_type,
        "track": track or "",
        "status": status,
        "last_attempt_at": isoformat(now),
        "last_success_at": "",
        "rawdata_path": stored_path(path),
        "sha256": "",
        "record_count": 0,
        "error": str(error),
    }
    if path.exists():
        try:
            record["sha256"] = sha256_file(path)
            record["record_count"] = count_json_records(path)
        except Exception:
            pass
    state.setdefault("records", {})[key] = record
    return record


def mark_stale(state, source_type, venue, year, path, *, source=None, track=None, now=None):
    return mark_failed(
        state,
        source_type,
        venue,
        year,
        path,
        "active-year refresh due",
        source=source,
        track=track,
        status="stale",
        now=now,
    )


def should_skip_fetch(
    state,
    source_type,
    venue,
    year,
    out_path,
    *,
    active_year_refresh_days=7,
    now=None,
    allow_bootstrap=True,
):
    now = now or utc_now()
    key = record_key(source_type, venue, year)
    out_path = Path(out_path)
    record = state.setdefault("records", {}).get(key)
    bootstrapped = False
    if not record and out_path.exists() and allow_bootstrap:
        try:
            record = mark_complete(
                state,
                source_type,
                venue,
                year,
                out_path,
                source=source_type,
                now=now,
                bootstrapped=True,
            )
            bootstrapped = True
        except Exception:
            record = None

    if not record:
        return SkipDecision(False, "missing_state", key, bootstrapped)
    if record.get("status") in INCOMPLETE_STATUSES:
        return SkipDecision(False, record.get("status") or "incomplete", key, bootstrapped)
    if not valid_complete_record(record, out_path):
        return SkipDecision(False, "missing_or_changed_file", key, bootstrapped)

    if is_active_year(year, now):
        last_success = parse_time(record.get("last_success_at"))
        if not last_success:
            return SkipDecision(False, "active_year_missing_success_time", key, bootstrapped)
        age_days = (now - last_success).total_seconds() / 86400
        if active_year_refresh_days >= 0 and age_days >= active_year_refresh_days:
            return SkipDecision(False, "active_year_refresh_due", key, bootstrapped)

    return SkipDecision(True, "complete", key, bootstrapped)
