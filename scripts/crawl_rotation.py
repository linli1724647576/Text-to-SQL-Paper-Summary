#!/usr/bin/env python3
"""Select and finalize daily venue batches for incremental crawls."""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from crawl_state import INCOMPLETE_STATUSES, isoformat, load_state, parse_time, save_state
from source_coverage import venue_manifest as source_venue_manifest


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = REPO_ROOT / "data" / "reports"
DEFAULT_STATE = REPORT_DIR / "crawl_state.json"
DEFAULT_PLAN = REPORT_DIR / "crawl_rotation_plan.json"
DEFAULT_TRACKS = "AI,DB,SE"
HISTORY_LIMIT = 90


def load_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, sort_keys=True)


def venue_manifest(from_year, to_year, tracks):
    return source_venue_manifest(from_year, to_year, tracks=tracks)


def normalized_retry_queue(rotation, manifest):
    manifest_by_upper = {venue.upper(): venue for venue in manifest}
    retry = []
    seen = set()
    for venue in rotation.get("retry_queue") or []:
        key = str(venue).upper()
        if key in manifest_by_upper and key not in seen:
            retry.append(manifest_by_upper[key])
            seen.add(key)
    rotation["retry_queue"] = retry
    return retry


def select_batch(state, manifest, batch_size):
    rotation = state.setdefault("rotation", {})
    retry_queue = normalized_retry_queue(rotation, manifest)
    cursor_before = int(rotation.get("cursor") or 0) % max(1, len(manifest))
    cursor = cursor_before
    selected = []
    retry_selected = []
    new_selected = []

    if retry_queue and batch_size > 0:
        selected.append(retry_queue[0])
        retry_selected.append(retry_queue[0])

    retry_set = set(retry_queue)
    attempts = 0
    while len(selected) < batch_size and attempts < len(manifest):
        venue = manifest[cursor]
        cursor = (cursor + 1) % len(manifest)
        attempts += 1
        if venue in selected or venue in retry_set:
            continue
        selected.append(venue)
        new_selected.append(venue)

    fill_idx = 1
    while len(selected) < batch_size and fill_idx < len(retry_queue):
        venue = retry_queue[fill_idx]
        fill_idx += 1
        if venue in selected:
            continue
        selected.append(venue)
        retry_selected.append(venue)

    return {
        "selected": selected,
        "retry_selected": retry_selected,
        "new_selected": new_selected,
        "cursor_before": cursor_before,
        "cursor_after": cursor,
    }


def write_github_output(path, outputs):
    target = path or os.environ.get("GITHUB_OUTPUT")
    if not target:
        return
    with open(target, "a", encoding="utf-8") as f:
        for key, value in outputs.items():
            f.write(f"{key}={value}\n")


def command_select(args):
    manifest = venue_manifest(args.from_year, args.to_year, args.tracks)
    if not manifest:
        raise SystemExit("empty venue manifest")
    state = load_state(args.crawl_state)
    now = datetime.now(timezone.utc)
    selection = select_batch(state, manifest, args.batch_size)
    selected = selection["selected"]
    plan = {
        "version": 1,
        "selected_at": isoformat(now),
        "from_year": args.from_year,
        "to_year": args.to_year,
        "tracks": args.tracks,
        "batch_size": args.batch_size,
        "manifest": manifest,
        "venues": selected,
        "venues_csv": ",".join(selected),
        "retry_venues": selection["retry_selected"],
        "new_venues": selection["new_selected"],
        "cursor_before": selection["cursor_before"],
        "cursor_after": selection["cursor_after"],
    }
    write_json(args.plan, plan)
    write_github_output(args.github_output, {"venues": plan["venues_csv"]})
    print(f"Selected crawl venues: {plan['venues_csv']}")


def report_failed_venues(reports_dir, selected):
    failed = set()
    selected_by_upper = {venue.upper(): venue for venue in selected}
    for name in ("fetch_failures.json", "official_accepted_failures.json"):
        payload = load_json(Path(reports_dir) / name, {})
        for item in payload.get("failures") or []:
            key = str(item.get("venue") or "").upper()
            if key in selected_by_upper:
                failed.add(selected_by_upper[key])
    return failed


def state_failed_venues(state, selected, selected_at):
    failed = set()
    selected_by_upper = {venue.upper(): venue for venue in selected}
    for record in (state.get("records") or {}).values():
        key = str(record.get("venue") or "").upper()
        if key not in selected_by_upper or record.get("status") not in INCOMPLETE_STATUSES:
            continue
        attempted = parse_time(record.get("last_attempt_at"))
        if not attempted or attempted < selected_at:
            continue
        failed.add(selected_by_upper[key])
    return failed


def command_finalize(args):
    state = load_state(args.crawl_state)
    plan = load_json(args.plan, {})
    selected = [str(item) for item in plan.get("venues") or []]
    if not selected:
        print("No selected venues in rotation plan; nothing to finalize")
        return
    selected_at = parse_time(plan.get("selected_at")) or datetime.now(timezone.utc)
    failed = report_failed_venues(args.reports_dir, selected)
    failed |= state_failed_venues(state, selected, selected_at)
    succeeded = [venue for venue in selected if venue not in failed]

    rotation = state.setdefault("rotation", {})
    retry_queue = normalized_retry_queue(rotation, plan.get("manifest") or selected)
    retry_queue = [venue for venue in retry_queue if venue not in succeeded]
    for venue in selected:
        if venue in failed and venue not in retry_queue:
            retry_queue.append(venue)
    rotation["retry_queue"] = retry_queue
    rotation["cursor"] = int(plan.get("cursor_after", rotation.get("cursor") or 0))
    history = rotation.setdefault("history", [])
    history.append(
        {
            "finalized_at": isoformat(datetime.now(timezone.utc)),
            "venues": selected,
            "succeeded": succeeded,
            "failed": sorted(failed),
            "cursor": rotation["cursor"],
        }
    )
    rotation["history"] = history[-HISTORY_LIMIT:]
    rotation["last_selected"] = selected
    rotation["last_completed_at"] = history[-1]["finalized_at"]
    save_state(args.crawl_state, state)
    print(f"Finalized crawl venues: succeeded={succeeded}; failed={sorted(failed)}")


def main():
    parser = argparse.ArgumentParser(description="Manage daily incremental crawl rotation")
    subparsers = parser.add_subparsers(dest="command", required=True)

    select = subparsers.add_parser("select")
    select.add_argument("--from-year", type=int, default=2020)
    select.add_argument("--to-year", type=int, default=2026)
    select.add_argument("--tracks", default=DEFAULT_TRACKS)
    select.add_argument("--batch-size", type=int, default=2)
    select.add_argument("--crawl-state", default=str(DEFAULT_STATE))
    select.add_argument("--plan", default=str(DEFAULT_PLAN))
    select.add_argument("--github-output")
    select.set_defaults(func=command_select)

    finalize = subparsers.add_parser("finalize")
    finalize.add_argument("--crawl-state", default=str(DEFAULT_STATE))
    finalize.add_argument("--plan", default=str(DEFAULT_PLAN))
    finalize.add_argument("--reports-dir", default=str(REPORT_DIR))
    finalize.set_defaults(func=command_finalize)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
