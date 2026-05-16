#!/usr/bin/env python3
"""Fetch SIGMOD accepted research papers from official conference pages."""

import argparse
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RAWDATA_DIR = REPO_ROOT / "data" / "rawdata"

SIGMOD_ACCEPTED_URLS = {
    2020: "https://sigmod2020.sigmodconf.hosting.acm.org/sigmod_research_list.shtml",
    2021: "https://2021.sigmod.org/sigmod_research_list.shtml",
    2022: "https://2022.sigmod.org/sigmod_research_list.shtml",
    2023: "https://2023.sigmod.org/sigmod_research_list.shtml",
    2024: "https://2024.sigmod.org/sigmod-list.html",
    2025: "https://2025.sigmod.org/sigmod_papers.shtml",
    2026: "https://2026.sigmod.org/sigmod_papers.shtml",
}

STOP_HEADINGS = (
    "Accepted Industrial",
    "Accepted Demo",
    "Accepted Demos",
    "Accepted Tutorials",
    "Accepted Workshops",
    "PODS",
)


def clean(text):
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_text(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "Text2SQL-Paper-Summary/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def normalize_title(title):
    title = clean(title)
    title = re.sub(r"^\d+\s*[|.)-]\s*", "", title)
    title = re.sub(r"\s*\[[^\]]*(Experiments|Analysis|Vision|Systems)[^\]]*\]\s*$", "", title)
    return title.strip()


def authors_from_text(text):
    names = []
    for part in re.split(r";|\band\b", clean(text)):
        name = re.sub(r"\([^)]*\)", "", part)
        name = name.replace("*", "").strip(" ,\"")
        if name:
            names.append(name)
    return " and ".join(names)


def row_entries(content):
    entries = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", content, flags=re.I | re.S):
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.I | re.S)
        if len(cells) < 3:
            continue
        title = normalize_title(cells[-2])
        if not title or title.lower() in {"a", "paper title", "total papers accepted:"}:
            continue
        entries.append((title, authors_from_text(cells[-1])))
    return entries


def list_entries(content):
    entries = []
    matches = list(re.finditer(r"<li[^>]*>(.*?)(?=<li[\s>]|</ul>)", content, flags=re.I | re.S))
    for match in matches:
        item = match.group(1)
        bold = re.search(r"<(?:b|strong)[^>]*>(.*?)</(?:b|strong)>", item, flags=re.I | re.S)
        if bold:
            title = normalize_title(bold.group(1))
            tail = item[bold.end():]
        else:
            parts = re.split(r"<br\s*/?>", item, maxsplit=1, flags=re.I)
            title = normalize_title(parts[0])
            tail = parts[1] if len(parts) > 1 else ""
        if not title or title.lower() in {"homepage", "accepted papers"}:
            continue
        if any(heading.lower() in clean(tail).lower()[:80] for heading in STOP_HEADINGS):
            tail = ""
        entries.append((title, authors_from_text(tail)))
    return entries


def parse_accepted(content):
    main = re.search(r'<div[^>]+id=["\']maincontent["\'][^>]*>(.*?)(?:<!--endMainContent|<div id=["\']footer)', content, flags=re.I | re.S)
    if main:
        content = main.group(1)
    h1 = re.search(r"<h1[^>]*>\s*Accepted Papers for SIGMOD\s*</h1>", content, flags=re.I)
    if h1:
        content = content[h1.end():]
    entries = row_entries(content)
    if len(entries) >= 10:
        return entries
    return list_entries(content)


def make_paper(title, authors, year, url):
    return {
        "type": "INPROCEEDINGS",
        "key": f"sigmod-official-{year}-{re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:80]}",
        "author": authors,
        "booktitle": "SIGMOD Conference",
        "title": title,
        "year": str(year),
        "abstract": "",
        "keywords": "",
        "url": url,
        "doi": "",
        "venue": "SIGMOD",
        "venue_track": "数据库领域",
    }


def main():
    parser = argparse.ArgumentParser(description="Fetch official SIGMOD accepted research papers")
    parser.add_argument("--from-year", type=int, default=2020)
    parser.add_argument("--to-year", type=int, default=2026)
    parser.add_argument("--output-dir", default=str(RAWDATA_DIR))
    args = parser.parse_args()

    total = 0
    for year, url in SIGMOD_ACCEPTED_URLS.items():
        if year < args.from_year or year > args.to_year:
            continue
        print(f"Fetching SIGMOD {year}: {url}", file=sys.stderr)
        content = get_text(url)
        entries = parse_accepted(content)
        papers = {title: make_paper(title, authors, year, url) for title, authors in entries}
        out_path = Path(args.output_dir) / str(year) / f"SIGMOD{year}-accepted.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(papers, f, indent=2, ensure_ascii=False)
        total += len(papers)
        print(f"  wrote {len(papers)} papers -> {out_path}", file=sys.stderr)

    print(f"Fetched official SIGMOD accepted entries: {total}", file=sys.stderr)


if __name__ == "__main__":
    main()
