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
import xml.etree.ElementTree as ET
from pathlib import Path

from http_utils import get_json, get_text
from venues import iter_ccf_a_venues, iter_readme_journals

REPO_ROOT = Path(__file__).resolve().parents[1]
RAWDATA_DIR = REPO_ROOT / "data" / "rawdata"
REPORT_DIR = REPO_ROOT / "data" / "reports"

ARXIV_QUERIES = [
    '"text-to-sql"',
    '"text to sql"',
    "text2sql",
    "nl2sql",
    '"natural language to sql"',
    '"semantic parsing" sql database',
]

JOURNAL_URL_CACHE = {}
JOURNAL_VOLUME_HINTS = {
    "tse": ("tse", -1974),
    "tosem": ("tosem", -1991),
    "tkde": ("tkde", -1988),
    "vldb": ("vldb", -1991),
}

OPENALEX_JOURNAL_SOURCES = {
    "AIJ": "S196139623",
    "TKDE": "S30698027",
    "VLDBJ": "S78926909",
    "TSE": "S8351582",
    "TOSEM": "S142627899",
}


def clean(text):
    return re.sub(r"\s+", " ", (text or "")).strip()


def dblp_url(dblp_key, year):
    return f"https://dblp.org/db/conf/{dblp_key}/{dblp_key}{year}.xml"


def dblp_journal_index_url(dblp_key):
    return f"https://dblp.org/db/journals/{dblp_key}/index.html"


def hinted_journal_urls(dblp_key, year):
    if dblp_key not in JOURNAL_VOLUME_HINTS or year < 2020 or year > 2026:
        return []
    prefix, offset = JOURNAL_VOLUME_HINTS[dblp_key]
    volume = year + offset
    return [f"https://dblp.org/db/journals/{dblp_key}/{prefix}{volume}.xml"]


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
        node_year = clean(node.findtext("year", default="")) or str(year)
        if str(node_year) != str(year):
            continue
        title = clean(" ".join("".join(title_node.itertext()) for title_node in node.findall("title")))
        if not title:
            continue
        authors = [clean(author.text or "") for author in node.findall("author") if clean(author.text or "")]
        url_node = node.find("ee")
        doi_node = node.find("doi")
        booktitle_node = node.find("booktitle")
        journal_node = node.find("journal")
        source_title = clean(
            booktitle_node.text
            if booktitle_node is not None
            else journal_node.text if journal_node is not None else venue
        )
        entry = {
            "type": node.tag.upper(),
            "key": node.attrib.get("key", ""),
            "author": " and ".join(authors),
            "booktitle": source_title,
            "title": title,
            "year": str(node_year),
            "abstract": "",
            "keywords": "",
            "url": clean(url_node.text if url_node is not None else ""),
            "doi": clean(doi_node.text if doi_node is not None else ""),
            "venue": f"{venue}{year}",
            "venue_track": track,
        }
        journal = clean(journal_node.text if journal_node is not None else "")
        if journal:
            entry["journal"] = journal
        if entry["doi"] and not entry["url"]:
            entry["url"] = "https://doi.org/" + entry["doi"]
        papers[title] = entry
    return papers


def abstract_from_inverted_index(index):
    if not index:
        return ""
    positions = []
    for word, offsets in index.items():
        for offset in offsets:
            positions.append((offset, word))
    return clean(" ".join(word for _, word in sorted(positions)))


def openalex_source_name(work):
    primary = work.get("primary_location") or {}
    source = primary.get("source") or {}
    if source.get("display_name"):
        return clean(source["display_name"])
    host_venue = work.get("host_venue") or {}
    return clean(host_venue.get("display_name") or "Unknown")


def openalex_work_url(work):
    doi = clean(work.get("doi") or "")
    if doi:
        return doi
    primary = work.get("primary_location") or {}
    if primary.get("landing_page_url"):
        return clean(primary["landing_page_url"])
    return clean(work.get("id") or "")


def normalize_openalex_work(work, venue, year, track):
    title = clean(work.get("title") or work.get("display_name") or "")
    if not title:
        return None
    authors = []
    for authorship in work.get("authorships") or []:
        author = authorship.get("author") or {}
        name = clean(author.get("display_name") or "")
        if name:
            authors.append(name)
    concepts = [
        clean(concept.get("display_name") or "")
        for concept in work.get("concepts") or []
        if clean(concept.get("display_name") or "")
    ]
    source_title = openalex_source_name(work)
    entry = {
        "type": clean(work.get("type") or "ARTICLE").upper(),
        "key": clean(work.get("id") or ""),
        "author": " and ".join(authors),
        "booktitle": source_title or venue,
        "journal": source_title or venue,
        "title": title,
        "year": str(work.get("publication_year") or year),
        "abstract": abstract_from_inverted_index(work.get("abstract_inverted_index")),
        "keywords": ", ".join(concepts),
        "url": openalex_work_url(work),
        "doi": clean(work.get("doi") or ""),
        "venue": f"{venue}{year}",
        "venue_track": track,
        "openalex_id": clean(work.get("id") or ""),
    }
    return entry


def fetch_openalex_journal(source_id, venue, year, track):
    cursor = "*"
    combined = {}
    while True:
        params = {
            "filter": (
                f"primary_location.source.id:{source_id},"
                f"from_publication_date:{year}-01-01,"
                f"to_publication_date:{year}-12-31"
            ),
            "per-page": "200",
            "cursor": cursor,
            "sort": "publication_date:desc",
        }
        url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
        payload = get_json(url, timeout=30)
        results = payload.get("results") or []
        for work in results:
            entry = normalize_openalex_work(work, venue, year, track)
            if entry:
                combined[entry["title"]] = entry
        next_cursor = (payload.get("meta") or {}).get("next_cursor")
        if not results or not next_cursor:
            break
        cursor = next_cursor
        time.sleep(0.2)
    if not combined:
        raise RuntimeError("empty")
    return combined


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


def discover_journal_urls(dblp_key, year):
    hinted = hinted_journal_urls(dblp_key, year)
    if hinted:
        return hinted
    if dblp_key in JOURNAL_URL_CACHE:
        return JOURNAL_URL_CACHE[dblp_key].get(year, [])
    index_url = dblp_journal_index_url(dblp_key)
    html = get_text(index_url, timeout=10, attempts=2)
    pattern = re.compile(
        rf'href="([^"]*/db/journals/{re.escape(dblp_key)}/[^"]+\.html)"',
        re.I,
    )
    by_year = {}
    for match in pattern.finditer(html):
        href = match.group(1)
        context = html[max(0, match.start() - 500): match.end() + 500]
        context_text = re.sub(r"<[^>]+>", " ", context)
        years = set(int(item) for item in re.findall(r"\b(20\d{2})\b", context_text))
        for item_year in years:
            by_year.setdefault(item_year, []).append(href[:-5] + ".xml")
    for item_year, urls in list(by_year.items()):
        seen = set()
        unique = []
        for url in urls:
            if url in seen:
                continue
            seen.add(url)
            unique.append(url)
        by_year[item_year] = unique
    JOURNAL_URL_CACHE[dblp_key] = by_year
    return by_year.get(year, [])


def fetch_dblp_journal(dblp_key, venue, year, track):
    errors = []
    combined = {}
    for url in discover_journal_urls(dblp_key, year):
        try:
            xml_text = get_text(url, timeout=10, attempts=2)
            combined.update(parse_dblp_publications(xml_text, venue, year, track))
        except Exception as exc:
            errors.append(f"{url}: {exc}")
        time.sleep(0.2)
    if combined:
        return combined
    raise RuntimeError("; ".join(errors[-3:]) if errors else "empty")


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


def write_fetch_report(failures, warnings, total):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": {
            "fetched_entries": total,
            "failure_count": len(failures),
            "warning_count": len(warnings),
        },
        "failures": failures,
        "warnings": warnings,
    }
    write_json(REPORT_DIR / "fetch_failures.json", payload)


def main():
    parser = argparse.ArgumentParser(description="Fetch CCF-A DBLP and arXiv rawdata")
    parser.add_argument("--from-year", type=int, default=2020)
    parser.add_argument("--to-year", type=int, default=2026)
    parser.add_argument("--tracks", default="AI,DB,SE",
                        help="Comma-separated CCF-A tracks: AI,DB,SE")
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
    warnings = []
    for track, venue, dblp_key, year in iter_ccf_a_venues(args.from_year, args.to_year, tracks=tracks):
        if allowed_venues and venue.lower() not in allowed_venues:
            continue
        out_path = RAWDATA_DIR / str(year) / f"{venue}{year}.json"
        print(f"Fetching DBLP {venue}{year}", file=sys.stderr)
        try:
            papers = fetch_dblp_venue(dblp_key, venue, year, track)
        except Exception as exc:
            print(f"  WARN: failed {venue}{year}: {exc}", file=sys.stderr)
            failures.append(
                {
                    "venue": venue,
                    "year": year,
                    "track": track,
                    "source": "dblp",
                    "source_type": "dblp-conference",
                    "status": "failed",
                    "error": str(exc),
                }
            )
            continue
        write_json(out_path, papers)
        total += len(papers)
        print(f"  wrote {len(papers)} papers -> {out_path}", file=sys.stderr)
        if args.sleep:
            time.sleep(args.sleep)

    for track, venue, dblp_key, year in iter_readme_journals(args.from_year, args.to_year, tracks=tracks):
        if allowed_venues and venue.lower() not in allowed_venues:
            continue
        out_path = RAWDATA_DIR / str(year) / f"{venue}{year}.json"
        print(f"Fetching DBLP journal {venue}{year}", file=sys.stderr)
        try:
            papers = fetch_dblp_journal(dblp_key, venue, year, track)
        except Exception as exc:
            print(f"  WARN: DBLP journal failed {venue}{year}: {exc}", file=sys.stderr)
            source_id = OPENALEX_JOURNAL_SOURCES.get(venue)
            if not source_id:
                failures.append(
                    {
                        "venue": venue,
                        "year": year,
                        "track": track,
                        "source": "dblp-journal",
                        "source_type": "journal",
                        "status": "failed",
                        "error": str(exc),
                    }
                )
                continue
            try:
                print(f"  trying OpenAlex fallback {venue}{year}", file=sys.stderr)
                papers = fetch_openalex_journal(source_id, venue, year, track)
                warnings.append(
                    {
                        "venue": venue,
                        "year": year,
                        "track": track,
                        "source": "openalex-journal-fallback",
                        "status": "fallback_used",
                        "reason": f"DBLP journal failed or empty: {exc}",
                    }
                )
            except Exception as fallback_exc:
                print(f"  WARN: OpenAlex fallback failed {venue}{year}: {fallback_exc}", file=sys.stderr)
                failures.append(
                    {
                        "venue": venue,
                        "year": year,
                        "track": track,
                        "source": "journal",
                        "source_type": "journal",
                        "status": "failed",
                        "error": f"DBLP: {exc}; OpenAlex: {fallback_exc}",
                    }
                )
                continue
        write_json(out_path, papers)
        total += len(papers)
        print(f"  wrote {len(papers)} journal papers -> {out_path}", file=sys.stderr)
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
                warnings.append(
                    {
                        "venue": "arXiv",
                        "year": "",
                        "track": "arXiv",
                        "source": query,
                        "source_type": "arxiv",
                        "status": "partial_failed",
                        "error": str(exc),
                    }
                )
            if args.sleep:
                time.sleep(max(args.sleep, 3.0))
        if arxiv_papers:
            write_json(RAWDATA_DIR / "arxiv" / "arXiv-text2sql.json", arxiv_papers)
            total += len(arxiv_papers)
            print(f"  wrote {len(arxiv_papers)} arXiv papers", file=sys.stderr)
        else:
            warnings.append(
                {
                    "venue": "arXiv",
                    "year": "",
                    "track": "arXiv",
                    "source": "arxiv",
                    "source_type": "arxiv",
                    "status": "empty_skipped",
                    "error": "no arXiv candidates collected; existing output kept unchanged",
                }
            )
            print("  WARN: no arXiv candidates collected; existing output kept unchanged", file=sys.stderr)

    print(f"Fetched rawdata entries: {total}", file=sys.stderr)
    write_fetch_report(failures, warnings, total)
    print(f"Wrote fetch report: {REPORT_DIR / 'fetch_failures.json'}", file=sys.stderr)


if __name__ == "__main__":
    main()
