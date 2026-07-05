#!/usr/bin/env python3
"""Update README snapshot counts from the current repository data."""

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_README = REPO_ROOT / "README.md"
DEFAULT_LABELDATA = REPO_ROOT / "data" / "labeldata" / "labeldata.json"
DEFAULT_RAWDATA = REPO_ROOT / "data" / "rawdata"


@dataclass(frozen=True)
class SnapshotCounts:
    classified_papers: int
    rawdata_files: int
    official_source_files: int
    official_candidates: int


def format_count(value):
    return f"{value:,}"


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def item_count(path):
    payload = load_json(path)
    if isinstance(payload, dict):
        return len(payload)
    if isinstance(payload, list):
        return len(payload)
    raise ValueError(f"Unsupported JSON payload in {path}: {type(payload).__name__}")


def collect_counts(repo_root=REPO_ROOT):
    repo_root = Path(repo_root)
    rawdata_dir = repo_root / "data" / "rawdata"
    accepted_files = sorted(rawdata_dir.rglob("*-accepted.json"))
    return SnapshotCounts(
        classified_papers=item_count(repo_root / "data" / "labeldata" / "labeldata.json"),
        rawdata_files=sum(1 for path in rawdata_dir.rglob("*.json") if path.is_file()),
        official_source_files=sum(1 for path in accepted_files if path.is_file()),
        official_candidates=sum(item_count(path) for path in accepted_files if path.is_file()),
    )


SNAPSHOT_PATTERN = re.compile(
    r"(Current snapshot:\n\n)"
    r"- \*\*[\d,]+\*\* classified Text-to-SQL papers\n"
    r"- \*\*[\d,]+\*\* rawdata files under `data/rawdata/`\n"
    r"- \*\*[\d,]+\*\* official accepted/proceedings source files\n"
    r"- \*\*[\d,]+\*\* official accepted candidates before relevance filtering\n"
    r"(- Website: <[^>\n]+>\n)"
)


def make_snapshot_block(prefix, website_line, counts):
    return (
        f"{prefix}"
        f"- **{format_count(counts.classified_papers)}** classified Text-to-SQL papers\n"
        f"- **{format_count(counts.rawdata_files)}** rawdata files under `data/rawdata/`\n"
        f"- **{format_count(counts.official_source_files)}** official accepted/proceedings source files\n"
        f"- **{format_count(counts.official_candidates)}** official accepted candidates before relevance filtering\n"
        f"{website_line}"
    )


def update_readme_snapshot(
    readme_path=DEFAULT_README,
    counts=None,
    *,
    classified_papers=None,
    rawdata_files=None,
    official_source_files=None,
    official_candidates=None,
):
    if counts is None:
        counts = SnapshotCounts(
            classified_papers=classified_papers,
            rawdata_files=rawdata_files,
            official_source_files=official_source_files,
            official_candidates=official_candidates,
        )
    readme_path = Path(readme_path)
    original = readme_path.read_text(encoding="utf-8")

    def replace(match):
        return make_snapshot_block(match.group(1), match.group(2), counts)

    updated, replacements = SNAPSHOT_PATTERN.subn(replace, original, count=1)
    if replacements != 1:
        raise RuntimeError(f"Could not find the Current snapshot block in {readme_path}")
    if updated == original:
        return False
    readme_path.write_text(updated, encoding="utf-8")
    return True


def main():
    parser = argparse.ArgumentParser(description="Update README Current snapshot counts from local data.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--readme", default=str(DEFAULT_README))
    args = parser.parse_args()

    counts = collect_counts(args.repo_root)
    changed = update_readme_snapshot(args.readme, counts)
    status = "updated" if changed else "already current"
    print(
        "README snapshot "
        f"{status}: classified={format_count(counts.classified_papers)}, "
        f"rawdata_files={format_count(counts.rawdata_files)}, "
        f"official_source_files={format_count(counts.official_source_files)}, "
        f"official_candidates={format_count(counts.official_candidates)}"
    )


if __name__ == "__main__":
    main()
