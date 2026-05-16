#!/usr/bin/env python3
"""Extract paper metadata from local rawdata files.

Supported inputs:
* BibTeX files with title/abstract fields
* ACL Anthology-style HTML pages with embedded abstracts
* NDSS-style HTML pages with paper titles/links
* JSON files already shaped as {title: entry} or a list of paper objects
* CSV files with title/abstract/year/venue columns
"""

import argparse
import csv
import json
import os
import re
import sys
from html import unescape

from venues import canonical_venue_from_filename

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def clean(text):
    return re.sub(r"\s+", " ", (text or "")).strip()


def infer_year(path):
    for part in path.replace("\\", "/").split("/"):
        if re.fullmatch(r"20\d{2}", part):
            return part
    match = re.search(r"(20\d{2})", os.path.basename(path))
    return match.group(1) if match else ""


def infer_venue(path):
    return canonical_venue_from_filename(path)


def normalize_entry(entry, title, venue, year):
    title = clean(entry.get("title") or title)
    abstract = clean(entry.get("abstract") or "")
    if not title:
        return None
    out = {
        "type": entry.get("type", "INPROCEEDINGS"),
        "key": entry.get("key", ""),
        "author": entry.get("author", ""),
        "booktitle": entry.get("booktitle", venue),
        "title": title,
        "year": str(entry.get("year", year) or ""),
        "abstract": abstract,
        "keywords": entry.get("keywords", ""),
        "url": entry.get("url", entry.get("doi", "")),
        "doi": entry.get("doi", ""),
        "venue": entry.get("venue", venue),
        "venue_track": entry.get("venue_track", ""),
    }
    for optional in ("journal", "container", "source", "publisher", "openalex_id", "semantic_scholar_id"):
        if entry.get(optional):
            out[optional] = entry.get(optional)
    if out["doi"] and out["url"] == out["doi"] and not out["url"].startswith("http"):
        out["url"] = "https://doi.org/" + out["doi"]
    return out


def parse_bib(path, venue=None, year=None):
    venue = venue or infer_venue(path)
    year = year or infer_year(path)
    text = open(path, encoding="utf-8", errors="ignore").read()
    entries = {}
    for chunk in re.split(r"\n@", text):
        chunk = chunk.strip()
        if not chunk:
            continue
        if not chunk.startswith("@"):
            chunk = "@" + chunk
        match = re.match(r"@(\w+)\s*\{([^,]*),", chunk)
        if not match:
            continue
        raw = {"type": match.group(1).upper(), "key": match.group(2).strip()}
        for field_match in re.finditer(r"(\w+)\s*=\s*\{((?:[^{}]|\{[^{}]*\})*)\}", chunk, re.S):
            raw[field_match.group(1).lower()] = clean(field_match.group(2).replace("{", "").replace("}", ""))
        for field_match in re.finditer(r'(\w+)\s*=\s*"([^"]*)"', chunk, re.S):
            raw[field_match.group(1).lower()] = clean(field_match.group(2))
        entry = normalize_entry(raw, raw.get("title", ""), venue, year)
        if entry:
            entries[entry["title"]] = entry
    return entries


def parse_json(path, venue=None, year=None):
    venue = venue or infer_venue(path)
    year = year or infer_year(path)
    data = json.load(open(path, encoding="utf-8"))
    if isinstance(data, list):
        iterable = [(item.get("title", ""), item) for item in data]
    else:
        iterable = data.items()
    entries = {}
    for title, raw in iterable:
        entry = normalize_entry(raw, title, venue, year)
        if entry:
            entries[entry["title"]] = entry
    return entries


def strip_tags(text):
    return clean(unescape(re.sub(r"<[^>]+>", " ", text or "")))


def parse_acl_html(path, venue=None, year=None):
    venue = venue or infer_venue(path)
    year = year or infer_year(path)
    content = open(path, encoding="utf-8", errors="ignore").read()
    entries = {}

    title_positions = [
        (m.start(), strip_tags(m.group(2)), m.group(1).strip().strip("\"'"))
        for m in re.finditer(
            r'<strong><a class=align-middle href=([^\s>]+)[^>]*>(.*?)</a></strong>',
            content,
            re.S,
        )
    ]
    abstract_positions = [
        (m.start(), strip_tags(m.group(1)))
        for m in re.finditer(r'<div class="card-body p-3 small">(.*?)</div>', content, re.S)
    ]

    ai = 0
    for idx, (tpos, title, url) in enumerate(title_positions):
        next_tpos = title_positions[idx + 1][0] if idx + 1 < len(title_positions) else len(content)
        while ai < len(abstract_positions) and abstract_positions[ai][0] < tpos:
            ai += 1
        if ai >= len(abstract_positions) or abstract_positions[ai][0] >= next_tpos:
            continue
        abstract = abstract_positions[ai][1]
        ai += 1
        if url and not url.startswith("http"):
            url = "https://aclanthology.org" + url
        entry = normalize_entry(
            {
                "type": "INPROCEEDINGS",
                "title": title,
                "abstract": abstract,
                "url": url,
                "venue": venue,
                "booktitle": venue,
                "year": year,
            },
            title,
            venue,
            year,
        )
        if entry:
            entries[entry["title"]] = entry
    return entries


def parse_ndss_html(path, venue=None, year=None):
    venue = venue or infer_venue(path)
    year = year or infer_year(path)
    content = open(path, encoding="utf-8", errors="ignore").read()
    entries = {}

    patterns = [
        re.compile(r'<h2 class="pt-cv-title"><a href="([^"]*)"[^>]*>(.*?)</a></h2>', re.S),
        re.compile(r'<h3 class="blog-post-title">(.*?)</h3>.*?<a class="paper-link-abs" href="([^"]+)"', re.S),
    ]
    for pattern in patterns:
        for match in pattern.finditer(content):
            if len(match.groups()) != 2:
                continue
            first, second = match.group(1), match.group(2)
            if first.startswith("http"):
                url, title = first, strip_tags(second)
            else:
                title, url = strip_tags(first), second.strip()
            entry = normalize_entry(
                {
                    "type": "INPROCEEDINGS",
                    "title": title,
                    "abstract": "",
                    "url": url,
                    "venue": venue,
                    "booktitle": venue,
                    "year": year,
                },
                title,
                venue,
                year,
            )
            if entry:
                entries[entry["title"]] = entry
        if entries:
            break
    return entries


def parse_html(path, venue=None, year=None):
    content = open(path, encoding="utf-8", errors="ignore").read(80000).lower()
    if "acl anthology" in content or "aclanthology" in content or "align-middle" in content:
        return parse_acl_html(path, venue, year)
    if "ndss" in path.lower() or "ndss symposium" in content or "pt-cv-title" in content:
        return parse_ndss_html(path, venue, year)
    raise ValueError(f"cannot detect supported HTML format for {path}")


def parse_csv(path, venue=None, year=None):
    venue = venue or infer_venue(path)
    year = year or infer_year(path)
    entries = {}
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            lowered = {k.lower(): v for k, v in row.items()}
            entry = normalize_entry(lowered, lowered.get("title", ""), venue, year)
            if entry:
                entries[entry["title"]] = entry
    return entries


def main():
    parser = argparse.ArgumentParser(description="Extract papers from rawdata")
    parser.add_argument("input")
    parser.add_argument("--venue")
    parser.add_argument("--year")
    args = parser.parse_args()

    ext = os.path.splitext(args.input)[1].lower()
    if ext == ".bib":
        entries = parse_bib(args.input, args.venue, args.year)
    elif ext == ".json":
        entries = parse_json(args.input, args.venue, args.year)
    elif ext == ".csv":
        entries = parse_csv(args.input, args.venue, args.year)
    elif ext in (".html", ".htm"):
        entries = parse_html(args.input, args.venue, args.year)
    else:
        print(f"Unsupported input type: {ext}", file=sys.stderr)
        sys.exit(1)

    print(f"Extracted {len(entries)} papers from {args.input}", file=sys.stderr)
    json.dump(entries, sys.stdout, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
