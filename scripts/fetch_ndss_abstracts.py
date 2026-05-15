#!/usr/bin/env python3
"""Fetch abstracts for NDSS entries extracted from proceedings pages."""

import argparse
import json
import re
import sys
import time
import urllib.request
from html import unescape
from pathlib import Path


def clean(text):
    text = unescape(re.sub(r"<[^>]+>", " ", text or ""))
    return re.sub(r"\s+", " ", text).strip()


def fetch(url, timeout=20):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Text2SQL-Paper-Summary/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def extract_abstract(html):
    patterns = [
        r'<h2[^>]*>\s*Abstract\s*</h2>\s*<p[^>]*>(.*?)</p>',
        r'<h3[^>]*>\s*Abstract\s*</h3>\s*<p[^>]*>(.*?)</p>',
        r'<div[^>]*class="[^"]*abstract[^"]*"[^>]*>(.*?)</div>',
        r'<section[^>]*class="[^"]*abstract[^"]*"[^>]*>(.*?)</section>',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.I | re.S)
        if match:
            abstract = clean(match.group(1))
            if len(abstract) > 40:
                return abstract
    return ""


def main():
    parser = argparse.ArgumentParser(description="Fetch NDSS abstracts")
    parser.add_argument("input")
    parser.add_argument("--output", "-o", required=True)
    parser.add_argument("--delay", type=float, default=0.5)
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        papers = json.load(f)

    updated = 0
    for title, entry in papers.items():
        if entry.get("abstract"):
            continue
        url = entry.get("url", "")
        if not url:
            continue
        try:
            abstract = extract_abstract(fetch(url))
        except Exception as exc:
            print(f"WARN: failed {title[:70]}: {exc}", file=sys.stderr)
            continue
        if abstract:
            entry["abstract"] = abstract
            updated += 1
        if args.delay:
            time.sleep(args.delay)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)
    print(f"Fetched abstracts for {updated} papers", file=sys.stderr)


if __name__ == "__main__":
    main()
