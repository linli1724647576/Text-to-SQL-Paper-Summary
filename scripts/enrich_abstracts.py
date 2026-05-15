#!/usr/bin/env python3
"""Enrich rawdata JSON files with abstracts via Semantic Scholar title search."""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path


def clean(text):
    return re.sub(r"\s+", " ", (text or "")).strip()


def get_json(url, timeout=20):
    headers = {"User-Agent": "Text2SQL-Paper-Summary/1.0"}
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def post_json(url, payload, timeout=30):
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "User-Agent": "Text2SQL-Paper-Summary/1.0",
        "Content-Type": "application/json",
    }
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key
    req = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def search_title(title):
    params = {
        "query": title,
        "limit": "3",
        "fields": "title,abstract,year,venue,externalIds,url",
    }
    url = "https://api.semanticscholar.org/graph/v1/paper/search?" + urllib.parse.urlencode(params)
    payload = get_json(url)
    title_norm = clean(title).lower()
    for paper in payload.get("data") or []:
        candidate = clean(paper.get("title", "")).lower()
        if candidate == title_norm or title_norm in candidate or candidate in title_norm:
            abstract = clean(paper.get("abstract", ""))
            if abstract:
                return abstract
    return ""


def doi_id(doi):
    doi = clean(doi)
    if not doi:
        return ""
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.I)
    return "DOI:" + doi


def batch_by_doi(entries):
    indexed = []
    ids = []
    for title, entry in entries:
        if entry.get("abstract"):
            continue
        paper_id = doi_id(entry.get("doi", ""))
        if not paper_id:
            continue
        indexed.append((title, entry, paper_id))
        ids.append(paper_id)
    if not ids:
        return 0

    updated = 0
    fields = "title,abstract,year,venue,externalIds,url"
    for start in range(0, len(ids), 500):
        chunk = ids[start:start + 500]
        payload = post_json(
            "https://api.semanticscholar.org/graph/v1/paper/batch?"
            + urllib.parse.urlencode({"fields": fields}),
            {"ids": chunk},
        )
        for result, (_, entry, _) in zip(payload, indexed[start:start + 500]):
            if not result:
                continue
            abstract = clean(result.get("abstract", ""))
            if abstract:
                entry["abstract"] = abstract
                updated += 1
            if not entry.get("url") and result.get("url"):
                entry["url"] = result["url"]
    return updated


def enrich_file(path, limit=None, delay=1.0):
    with open(path, encoding="utf-8") as f:
        papers = json.load(f)
    items = list(papers.items())
    try:
        updated = batch_by_doi(items)
    except Exception as exc:
        print(f"WARN: DOI batch failed for {path}: {exc}", file=sys.stderr)
        updated = 0
    checked = 0
    for title, entry in items:
        if entry.get("abstract"):
            continue
        if limit is not None and checked >= limit:
            break
        checked += 1
        try:
            abstract = search_title(entry.get("title") or title)
        except Exception as exc:
            print(f"WARN: {title[:80]}: {exc}", file=sys.stderr)
            if "429" in str(exc):
                time.sleep(max(delay, 10.0))
            continue
        if abstract:
            entry["abstract"] = abstract
            updated += 1
        if delay:
            time.sleep(delay)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)
    return updated, checked


def main():
    parser = argparse.ArgumentParser(description="Enrich rawdata JSON abstracts")
    parser.add_argument("paths", nargs="+", help="JSON files or directories")
    parser.add_argument("--limit-per-file", type=int)
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()

    files = []
    for item in args.paths:
        path = Path(item)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.json")))
        else:
            files.append(path)

    total_updated = 0
    for path in files:
        if path.name == "fetch_failures.json":
            continue
        print(f"Enriching {path}", file=sys.stderr)
        updated, checked = enrich_file(path, limit=args.limit_per_file, delay=args.delay)
        total_updated += updated
        print(f"  updated {updated}/{checked}", file=sys.stderr)
    print(f"Total updated abstracts: {total_updated}", file=sys.stderr)


if __name__ == "__main__":
    main()
