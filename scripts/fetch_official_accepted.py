#!/usr/bin/env python3
"""Fetch accepted-paper lists from official conference pages.

The crawler intentionally stores only lightweight metadata. It is meant to
complement DBLP when official conference pages publish accepted papers earlier
or in a fuller form than DBLP.
"""

import argparse
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RAWDATA_DIR = REPO_ROOT / "data" / "rawdata"

OFFICIAL_ACCEPTED_URLS = {
    "ACL": {
        2025: "https://2025.aclweb.org/program/main_papers/",
    },
    "ICML": {
        2020: "https://proceedings.mlr.press/v119/",
        2021: "https://proceedings.mlr.press/v139/",
        2022: "https://proceedings.mlr.press/v162/",
        2023: "https://proceedings.mlr.press/v202/",
        2024: "https://proceedings.mlr.press/v235/",
        2025: "https://proceedings.mlr.press/v267/",
    },
    "ICDE": {
        2025: "https://ieee-icde.org/2025/research-papers/",
    },
    "ICSE": {
        2024: "https://conf.researchr.org/track/icse-2024/icse-2024-research-track",
        2025: "https://conf.researchr.org/track/icse-2025/icse-2025-research-track",
    },
    "FSE": {
        2024: "https://conf.researchr.org/track/fse-2024/fse-2024-research-papers",
        2025: "https://conf.researchr.org/track/fse-2025/fse-2025-research-papers",
    },
    "ASE": {
        2024: "https://conf.researchr.org/track/ase-2024/ase-2024-research",
        2025: "https://conf.researchr.org/track/ase-2025/ase-2025-papers",
    },
    "ISSTA": {
        2024: "https://conf.researchr.org/track/issta-2024/issta-2024-papers",
        2025: "https://conf.researchr.org/track/issta-2025/issta-2025-papers",
    },
    "IJCAI": {
        2020: "https://www.ijcai.org/proceedings/2020/",
        2021: "https://www.ijcai.org/proceedings/2021/",
        2022: "https://www.ijcai.org/proceedings/2022/",
        2023: "https://www.ijcai.org/proceedings/2023/",
        2024: "https://www.ijcai.org/proceedings/2024/",
        2025: "https://www.ijcai.org/proceedings/2025/",
    },
    "KDD": {
        2024: "https://kdd2024.kdd.org/research-track-papers/",
        2025: "https://kdd2025.kdd.org/research-track-papers/",
    },
    "NeurIPS": {
        2020: "https://proceedings.neurips.cc/paper/2020",
        2021: "https://proceedings.neurips.cc/paper/2021",
        2022: "https://proceedings.neurips.cc/paper/2022",
        2023: "https://proceedings.neurips.cc/paper_files/paper/2023",
        2024: "https://proceedings.neurips.cc/paper_files/paper/2024",
        2025: "https://proceedings.neurips.cc/paper/2025",
    },
    "SIGIR": {
        2025: "https://sigir2025.dei.unipd.it/accepted-papers.html",
    },
    "SIGMOD": {
        2020: "https://sigmod2020.sigmodconf.hosting.acm.org/sigmod_research_list.shtml",
        2021: "https://2021.sigmod.org/sigmod_research_list.shtml",
        2022: "https://2022.sigmod.org/sigmod_research_list.shtml",
        2023: "https://2023.sigmod.org/sigmod_research_list.shtml",
        2024: "https://2024.sigmod.org/sigmod-list.html",
        2025: "https://2025.sigmod.org/sigmod_papers.shtml",
        2026: "https://2026.sigmod.org/sigmod_papers.shtml",
    },
    "WWW": {
        2024: "https://www2024.thewebconf.org/accepted/research-tracks/",
        2026: "https://www2026.thewebconf.org/accepted/research-tracks.html",
    },
}

VENUE_CATEGORIES = {
    "ACL": "AI 领域",
    "ICML": "AI 领域",
    "IJCAI": "AI 领域",
    "NeurIPS": "AI 领域",
    "ICSE": "软件工程",
    "FSE": "软件工程",
    "ASE": "软件工程",
    "ISSTA": "软件工程",
    "ICDE": "数据库领域",
    "KDD": "数据库领域",
    "SIGIR": "数据库领域",
    "SIGMOD": "数据库领域",
    "WWW": "数据库领域",
}

STOP_HEADINGS = (
    "accepted demo",
    "accepted demos",
    "accepted industry",
    "accepted tutorial",
    "accepted tutorials",
    "accepted workshop",
    "accepted workshops",
    "doctoral consortium",
    "industry track",
    "pods",
    "sirip",
)


def clean(text):
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def text_lines(content):
    content = re.sub(r"<\s*br\s*/?\s*>", "\n", content, flags=re.I)
    content = re.sub(r"</(h[1-6]|p|li|td|tr|div)>", "\n", content, flags=re.I)
    content = re.sub(r"<[^>]+>", " ", content)
    content = html.unescape(content)
    lines = [re.sub(r"\s+", " ", line).strip() for line in content.splitlines()]
    return [line for line in lines if line]


def get_text(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "Text2SQL-Paper-Summary/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def normalize_title(title):
    title = clean(title)
    title = re.sub(r"^\d+\s*[|.)-]\s*", "", title)
    title = re.sub(r"^[A-Z]\s*$", "", title)
    title = re.sub(r"\s*\[[^\]]*(Experiments|Analysis|Vision|Systems)[^\]]*\]\s*$", "", title)
    title = title.strip(" :-")
    if len(title) < 8:
        return ""
    return title


def normalize_authors(text):
    text = clean(text)
    text = re.sub(r"\bDOI:\s*\S+", "", text, flags=re.I)
    text = re.sub(r"\([^)]*\)", "", text)
    text = text.replace("*", "")
    parts = re.split(r";|\band\b|,", text)
    authors = [part.strip(" ,\"") for part in parts if part.strip(" ,\"")]
    return " and ".join(authors)


def main_region(content):
    patterns = [
        r'<div[^>]+id=["\']maincontent["\'][^>]*>(.*?)(?:<!--endMainContent|<div id=["\']footer)',
        r'<main[^>]*>(.*?)</main>',
        r'<article[^>]*>(.*?)</article>',
    ]
    for pattern in patterns:
        match = re.search(pattern, content, flags=re.I | re.S)
        if match:
            return match.group(1)
    return content


def row_entries(content):
    entries = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", content, flags=re.I | re.S):
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.I | re.S)
        if len(cells) < 2:
            continue
        title_cell, author_cell = cells[-2], cells[-1]
        title = normalize_title(title_cell)
        if not title or title.lower() in {"paper title", "total papers accepted"}:
            continue
        entries.append((title, normalize_authors(author_cell)))
    return entries


def pmlr_entries(content):
    entries = []
    blocks = re.findall(r'<div[^>]+class=["\'][^"\']*paper[^"\']*["\'][^>]*>(.*?)</div>', content, flags=re.I | re.S)
    if not blocks:
        blocks = re.findall(r'<p[^>]+class=["\']title["\'][^>]*>(.*?)</p>(.*?)(?=<p[^>]+class=["\']title["\']|$)', content, flags=re.I | re.S)
    for block in blocks:
        if isinstance(block, tuple):
            title_html, body = block
        else:
            title_match = re.search(r'<p[^>]+class=["\']title["\'][^>]*>(.*?)</p>', block, flags=re.I | re.S)
            if not title_match:
                continue
            title_html, body = title_match.group(1), block[title_match.end():]
        title = normalize_title(title_html)
        if not title:
            continue
        authors = ""
        author_match = re.search(r'<p[^>]+class=["\']details["\'][^>]*>(.*?)</p>', body, flags=re.I | re.S)
        if author_match:
            authors = normalize_authors(author_match.group(1))
        entries.append((title, authors))
    return entries


def link_entries(content):
    entries = []
    for match in re.finditer(r'<a[^>]+href=["\'][^"\']*(?:paper|papers|proceedings)[^"\']*["\'][^>]*>(.*?)</a>', content, flags=re.I | re.S):
        title = normalize_title(match.group(1))
        if not title:
            continue
        if any(skip in title.lower() for skip in ("accepted", "proceedings", "schedule", "program")):
            continue
        tail = content[match.end(): match.end() + 500]
        entries.append((title, normalize_authors(tail)))
    return entries


def acl_anthology_entries(content):
    entries = []
    for block in re.findall(r'<p class="d-sm-flex[^"]*">(.*?)</p>', content, flags=re.I | re.S):
        title_match = re.search(r'<strong>(.*?)</strong>', block, flags=re.I | re.S)
        if not title_match:
            continue
        title = normalize_title(title_match.group(1))
        if not title:
            continue
        author_match = re.search(r'<em>(.*?)</em>', block, flags=re.I | re.S)
        authors = normalize_authors(author_match.group(1)) if author_match else ""
        entries.append((title, authors))
    return entries


def ijcai_entries(content):
    entries = []
    pattern = re.compile(
        r'<div[^>]+class=["\']paper_wrapper["\'][^>]*>\s*'
        r'<div[^>]+class=["\']title["\'][^>]*>(.*?)</div>\s*'
        r'<div[^>]+class=["\']authors["\'][^>]*>(.*?)</div>',
        re.I | re.S,
    )
    for title_html, authors_html in pattern.findall(content):
        title = normalize_title(title_html)
        if title:
            entries.append((title, normalize_authors(authors_html)))
    return entries


def sigir_accepted_entries(content):
    start = re.search(r'<h2[^>]+id=["\']full-papers["\'][^>]*>', content, flags=re.I)
    if start:
        next_heading = re.search(r'<h2[^>]+id=["\'][^"\']*papers["\'][^>]*>', content[start.end():], flags=re.I)
        content = content[start.end(): start.end() + next_heading.start()] if next_heading else content[start.end():]
    entries = []
    for item in re.findall(
        r'<li[^>]+class=["\'][^"\']*accepted-paper-item[^"\']*["\'][^>]*>(.*?)</li>',
        content,
        flags=re.I | re.S,
    ):
        title_match = re.search(
            r'<span[^>]+class=["\'][^"\']*accepted-paper-title[^"\']*["\'][^>]*>(.*?)</span>',
            item,
            flags=re.I | re.S,
        )
        if not title_match:
            continue
        author_match = re.search(
            r'<span[^>]+class=["\'][^"\']*accepted-paper-author[^"\']*["\'][^>]*>(.*?)</span>',
            item,
            flags=re.I | re.S,
        )
        title = normalize_title(title_match.group(1))
        if title:
            authors = normalize_authors(author_match.group(1)) if author_match else ""
            entries.append((title, authors))
    return entries


def www_research_entries(content):
    entries = []
    for item in re.findall(r"<li[^>]*>(.*?)</li>", content, flags=re.I | re.S):
        text = clean(item)
        match = re.match(r"^\([^)]+\)\s*(.+?)\s+[—-]\s+(.+)$", text)
        if not match:
            continue
        title = normalize_title(match.group(1))
        if title:
            entries.append((title, normalize_authors(match.group(2))))
    return entries


def kdd_table_entries(content):
    entries = []
    for table in re.findall(r"<table[^>]*>(.*?)</table>", content, flags=re.I | re.S):
        rows = re.findall(r"<tr[^>]*>\s*<td[^>]*>(.*?)</td>\s*</tr>", table, flags=re.I | re.S)
        idx = 0
        while idx < len(rows):
            title_match = re.search(r"<strong[^>]*>(.*?)</strong>", rows[idx], flags=re.I | re.S)
            if not title_match:
                idx += 1
                continue
            title = normalize_title(title_match.group(1))
            authors = normalize_authors(rows[idx + 1]) if idx + 1 < len(rows) else ""
            if title:
                entries.append((title, authors))
            idx += 2
    return entries


def kdd_schedule_entries(content):
    lines = text_lines(content)
    try:
        start = next(idx for idx, line in enumerate(lines) if line.lower() == "research track papers schedule")
    except StopIteration:
        return []
    entries = []
    skip_prefixes = (
        "theme:",
        "session chair:",
        "program",
        "author information",
        "attending",
        "sponsors",
        "calls",
        "menu",
    )
    date_re = re.compile(r"^(monday|tuesday|wednesday|thursday|friday|saturday|sunday),\s+\w+", re.I)
    for idx in range(start + 1, len(lines) - 1):
        line = lines[idx]
        next_line = lines[idx + 1]
        lower = line.lower()
        if date_re.match(line) or lower.startswith(skip_prefixes):
            continue
        if "(" not in next_line or ")" not in next_line:
            continue
        title = normalize_title(line)
        if not title:
            continue
        entries.append((title, normalize_authors(next_line)))
    return entries


def researchr_entries(content):
    allowed_tracks = {
        "research track",
        "research papers",
        "fse research papers",
        "icse research track",
        "ase research papers",
        "issta research papers",
    }
    entries = []
    for row in re.findall(r"<tr[^>]+data-slot-id=[\"'][^\"']+[\"'][^>]*>(.*?)</tr>", content, flags=re.I | re.S):
        track_match = re.search(r'<div[^>]+class=["\']prog-track["\'][^>]*>(.*?)</div>', row, flags=re.I | re.S)
        if not track_match or clean(track_match.group(1)).lower() not in allowed_tracks:
            continue
        title_match = re.search(r"<strong>\s*<a[^>]*>(.*?)</a>\s*</strong>", row, flags=re.I | re.S)
        if not title_match:
            continue
        title_html = re.sub(r"<span[^>]*>.*?</span>", "", title_match.group(1), flags=re.I | re.S)
        title = normalize_title(title_html)
        if not title:
            continue
        authors = ""
        performers_match = re.search(r'<div[^>]+class=["\']performers["\'][^>]*>(.*?)</div>', row, flags=re.I | re.S)
        if performers_match:
            names = [
                clean(name)
                for name in re.findall(r"<a[^>]*>(.*?)</a>", performers_match.group(1), flags=re.I | re.S)
                if clean(name)
            ]
            authors = " and ".join(names)
        entries.append((title, authors))
    return entries


def list_entries(content):
    entries = []
    matches = list(re.finditer(r"<li[^>]*>(.*?)(?=<li[\s>]|</ul>)", content, flags=re.I | re.S))
    for match in matches:
        item = match.group(1)
        if any(stop in clean(item).lower()[:80] for stop in STOP_HEADINGS):
            continue
        bold = re.search(r"<(?:b|strong)[^>]*>(.*?)</(?:b|strong)>", item, flags=re.I | re.S)
        if bold:
            title = normalize_title(bold.group(1))
            tail = item[bold.end():]
        else:
            parts = re.split(r"<br\s*/?>|\n", item, maxsplit=1, flags=re.I)
            title = normalize_title(parts[0])
            tail = parts[1] if len(parts) > 1 else ""
        if title:
            entries.append((title, normalize_authors(tail)))
    return entries


def heading_entries(content):
    entries = []
    pattern = re.compile(r"<h[2-6][^>]*>(.*?)</h[2-6]>(.*?)(?=<h[2-6][^>]*>|$)", re.I | re.S)
    for match in pattern.finditer(content):
        title = normalize_title(match.group(1))
        if not title:
            continue
        body = match.group(2)
        if any(stop in title.lower() for stop in STOP_HEADINGS):
            continue
        entries.append((title, normalize_authors(body)))
    return entries


def pipe_entries(content):
    entries = []
    lines = text_lines(content)
    for idx, line in enumerate(lines):
        match = re.match(r"^\d+\s*\|\s*(.+)$", line)
        if not match:
            continue
        title = normalize_title(match.group(1))
        if not title:
            continue
        author = lines[idx + 1] if idx + 1 < len(lines) else ""
        entries.append((title, normalize_authors(author)))
    return entries


def unique_entries(entries):
    seen = set()
    unique = []
    for title, authors in entries:
        key = title.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append((title, authors))
    return unique


def parse_accepted(content):
    is_researchr = 'conf.researchr.org' in content or '<body id="track"' in content
    if not is_researchr:
        content = main_region(content)
    h1 = re.search(r"<h1[^>]*>.*?Accepted.*?</h1>", content, flags=re.I | re.S)
    if h1 and not is_researchr:
        content = content[h1.end():]

    exact_parsers = (
        acl_anthology_entries,
        ijcai_entries,
        sigir_accepted_entries,
        www_research_entries,
        kdd_table_entries,
        kdd_schedule_entries,
        researchr_entries,
        pmlr_entries,
    )
    for parser in exact_parsers:
        entries = unique_entries(parser(content))
        if len(entries) >= 20:
            return entries

    if is_researchr:
        return []

    best = []
    for parser in (row_entries, list_entries, pipe_entries, link_entries, heading_entries):
        entries = parser(content)
        if len(entries) > len(best):
            best = entries
    return unique_entries(best)


def make_paper(venue, year, url, title, authors):
    return {
        "type": "INPROCEEDINGS",
        "key": f"{venue.lower()}-official-{year}-{re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:80]}",
        "author": authors,
        "booktitle": f"{venue} Conference",
        "title": title,
        "year": str(year),
        "abstract": "",
        "keywords": "",
        "url": url,
        "doi": "",
        "venue": venue,
        "venue_track": VENUE_CATEGORIES.get(venue, ""),
    }


def selected_configs(venues, from_year, to_year):
    allowed = {venue.strip().upper() for venue in venues.split(",") if venue.strip()} if venues else None
    for venue, years in OFFICIAL_ACCEPTED_URLS.items():
        if allowed and venue.upper() not in allowed:
            continue
        for year, url in years.items():
            if year < from_year or year > to_year:
                continue
            yield venue, year, url


def main():
    parser = argparse.ArgumentParser(description="Fetch official accepted-paper pages")
    parser.add_argument("--from-year", type=int, default=2020)
    parser.add_argument("--to-year", type=int, default=2026)
    parser.add_argument("--venues", help="Comma-separated venues, e.g. SIGMOD,ICDE,SIGIR")
    parser.add_argument("--output-dir", default=str(RAWDATA_DIR))
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument(
        "--min-entries",
        type=int,
        default=20,
        help="Skip pages that parse fewer entries; this avoids saving navigation pages as rawdata.",
    )
    args = parser.parse_args()

    total = 0
    for venue, year, url in selected_configs(args.venues, args.from_year, args.to_year):
        print(f"Fetching {venue} {year}: {url}", file=sys.stderr)
        try:
            content = get_text(url)
        except Exception as exc:
            print(f"  WARN: fetch failed: {exc}", file=sys.stderr)
            continue
        entries = parse_accepted(content)
        if len(entries) < args.min_entries:
            print(f"  WARN: parsed only {len(entries)} entries; skipped", file=sys.stderr)
            continue
        papers = {title: make_paper(venue, year, url, title, authors) for title, authors in entries}
        out_path = Path(args.output_dir) / str(year) / f"{venue}{year}-accepted.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(papers, f, indent=2, ensure_ascii=False)
        total += len(papers)
        print(f"  wrote {len(papers)} papers -> {out_path}", file=sys.stderr)
        if args.sleep:
            time.sleep(args.sleep)

    print(f"Fetched official accepted entries: {total}", file=sys.stderr)


if __name__ == "__main__":
    main()
