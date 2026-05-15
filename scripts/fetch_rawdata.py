#!/usr/bin/env python3
"""Build rawdata files from DBLP and arXiv.

This script creates ASE-style rawdata under data/rawdata/. DBLP is used for
CCF-A venue proceedings metadata; arXiv is used as a broad Text-to-SQL preprint
source. The downstream process_folder.py pipeline remains the source of truth.
"""

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from venues import iter_ccf_a_venues

REPO_ROOT = Path(__file__).resolve().parents[1]
RAWDATA_DIR = REPO_ROOT / "data" / "rawdata"

ARXIV_QUERIES = [
    '"text-to-sql"',
    '"text to sql"',
    "text2sql",
    "nl2sql",
    '"natural language to sql"',
    '"semantic parsing" sql database',
]


def get_text(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Text2SQL-Paper-Summary/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def clean(text):
    return re.sub(r"\s+", " ", (text or "")).strip()


def dblp_url(dblp_key, year):
    return f"https://dblp.org/db/conf/{dblp_key}/{dblp_key}{year}.xml"


def discover_dblp_urls(dblp_key, year):
    candidates = [dblp_url(dblp_key, year)]
    index_url = f"https://dblp.org/db/conf/{dblp_key}/index.html"
    try:
        html = get_text(index_url)
    except Exception:
        return candidates
    hrefs = re.findall(r'href="([^"]+)"', html)
    for href in hrefs:
        if str(year) not in href:
            continue
        if not href.endswith(".html"):
            continue
        if href.startswith("http"):
            full = href
        elif href.startswith("/"):
            full = "https://dblp.org" + href
        else:
            full = urllib.parse.urljoin(index_url, href)
        candidates.append(full[:-5] + ".xml")
    seen = set()
    unique = []
    for item in candidates:
        if item not in seen:
            unique.append(item)
            seen.add(item)
    return unique


def parse_dblp_publications(xml_text, venue, year, track):
    xml_text = re.sub(r"<(/?)(bht|h1|ref|dblpcites)([^>]*)>", r"", xml_text)
    root = ET.fromstring(f"<root>{xml_text}</root>")
    papers = {}
    for node in root.iter():
        if node.tag not in {"inproceedings", "article"}:
            continue
        title = clean(" ".join("".join(title_node.itertext()) for title_node in node.findall("title")))
        if not title:
            continue
        authors = [clean(author.text or "") for author in node.findall("author") if clean(author.text or "")]
        url_node = node.find("ee")
        doi_node = node.find("doi")
        booktitle_node = node.find("booktitle")
        entry = {
            "type": node.tag.upper(),
            "key": node.attrib.get("key", ""),
            "author": " and ".join(authors),
            "booktitle": clean(booktitle_node.text if booktitle_node is not None else venue),
            "title": title,
            "year": str(year),
            "abstract": "",
            "keywords": "",
            "url": clean(url_node.text if url_node is not None else ""),
            "doi": clean(doi_node.text if doi_node is not None else ""),
            "venue": f"{venue}{year}",
            "venue_track": track,
        }
        if entry["doi"] and not entry["url"]:
            entry["url"] = "https://doi.org/" + entry["doi"]
        papers[title] = entry
    return papers


def fetch_dblp_venue(dblp_key, venue, year, track):
    errors = []
    for url in discover_dblp_urls(dblp_key, year):
        try:
            xml_text = get_text(url)
            papers = parse_dblp_publications(xml_text, venue, year, track)
            if papers:
                return papers
            errors.append(f"{url}: empty")
        except Exception as exc:
            errors.append(f"{url}: {exc}")
    raise RuntimeError("; ".join(errors[-3:]))


def fetch_arxiv_query(query, start, max_results):
    params = {
        "search_query": f'all:{query}',
        "start": str(start),
        "max_results": str(max_results),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = "http://export.arxiv.org/api/query?" + urllib.parse.urlencode(params)
    xml_text = get_text(url, timeout=30)
    root = ET.fromstring(xml_text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entries = []
    for item in root.findall("atom:entry", ns):
        title = clean(item.findtext("atom:title", default="", namespaces=ns))
        abstract = clean(item.findtext("atom:summary", default="", namespaces=ns))
        published = item.findtext("atom:published", default="", namespaces=ns)
        year = published[:4] if published else ""
        authors = [
            clean(author.findtext("atom:name", default="", namespaces=ns))
            for author in item.findall("atom:author", ns)
        ]
        link = ""
        for link_node in item.findall("atom:link", ns):
            if link_node.attrib.get("rel") == "alternate":
                link = link_node.attrib.get("href", "")
                break
        if not title:
            continue
        entries.append(
            {
                "type": "ARTICLE",
                "key": item.findtext("atom:id", default="", namespaces=ns),
                "author": " and ".join(a for a in authors if a),
                "booktitle": "arXiv",
                "title": title,
                "year": year,
                "abstract": abstract,
                "keywords": "arxiv text-to-sql nl2sql natural language sql database semantic parsing",
                "url": link,
                "doi": "",
                "venue": f"arXiv{year}" if year else "arXiv",
                "venue_track": "arXiv",
            }
        )
    return entries


def write_json(path, papers):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Fetch CCF-A DBLP and arXiv rawdata")
    parser.add_argument("--from-year", type=int, default=2020)
    parser.add_argument("--to-year", type=int, default=2026)
    parser.add_argument("--tracks", default="AI,DB,SE,Security",
                        help="Comma-separated CCF-A tracks: AI,DB,SE,Security")
    parser.add_argument("--venues", help="Comma-separated venue abbreviations for debugging")
    parser.add_argument("--include-arxiv", action="store_true", default=True)
    parser.add_argument("--no-arxiv", dest="include_arxiv", action="store_false")
    parser.add_argument("--arxiv-max-results", type=int, default=200)
    parser.add_argument("--sleep", type=float, default=0.3)
    args = parser.parse_args()

    tracks = [item.strip() for item in args.tracks.split(",") if item.strip()]
    allowed_venues = None
    if args.venues:
        allowed_venues = {item.strip().lower() for item in args.venues.split(",") if item.strip()}

    total = 0
    failures = []
    for track, venue, dblp_key, year in iter_ccf_a_venues(args.from_year, args.to_year, tracks=tracks):
        if allowed_venues and venue.lower() not in allowed_venues:
            continue
        out_path = RAWDATA_DIR / str(year) / f"{venue}{year}.json"
        print(f"Fetching DBLP {venue}{year}", file=sys.stderr)
        try:
            papers = fetch_dblp_venue(dblp_key, venue, year, track)
        except Exception as exc:
            print(f"  WARN: failed {venue}{year}: {exc}", file=sys.stderr)
            failures.append({"venue": venue, "year": year, "track": track, "source": "dblp", "error": str(exc)})
            continue
        write_json(out_path, papers)
        total += len(papers)
        print(f"  wrote {len(papers)} papers -> {out_path}", file=sys.stderr)
        if args.sleep:
            time.sleep(args.sleep)

    if args.include_arxiv:
        arxiv_papers = {}
        per_query = max(1, args.arxiv_max_results // len(ARXIV_QUERIES))
        for query in ARXIV_QUERIES:
            print(f"Fetching arXiv query {query}", file=sys.stderr)
            try:
                for entry in fetch_arxiv_query(query, 0, per_query):
                    year = entry.get("year", "")
                    if year and (int(year) < args.from_year or int(year) > args.to_year):
                        continue
                    arxiv_papers[entry["title"]] = entry
            except Exception as exc:
                print(f"  WARN: arXiv query failed {query}: {exc}", file=sys.stderr)
                failures.append({"venue": "arXiv", "year": "", "track": "arXiv", "source": query, "error": str(exc)})
            if args.sleep:
                time.sleep(max(args.sleep, 3.0))
        write_json(RAWDATA_DIR / "arxiv" / "arXiv-text2sql.json", arxiv_papers)
        total += len(arxiv_papers)
        print(f"  wrote {len(arxiv_papers)} arXiv papers", file=sys.stderr)

    print(f"Fetched rawdata entries: {total}", file=sys.stderr)
    if failures:
        write_json(RAWDATA_DIR / "fetch_failures.json", {f"{item['venue']}{item['year']}:{i}": item for i, item in enumerate(failures)})
        print(f"Wrote failure report: {RAWDATA_DIR / 'fetch_failures.json'}", file=sys.stderr)


if __name__ == "__main__":
    main()
