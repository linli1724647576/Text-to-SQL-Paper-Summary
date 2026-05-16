#!/usr/bin/env python3
"""Crawl Text-to-SQL paper metadata from OpenAlex.

OpenAlex is used because it is public, keyless, and exposes abstracts for many
works through an inverted-index field. The script is intentionally conservative:
it gathers candidates by multiple Text-to-SQL queries, normalizes metadata, and
leaves relevance filtering/classification to label_papers.py.
"""

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from venues import iter_tracked_venues, normalize_entry_venue, normalize_venue_name, publication_category


DEFAULT_SEARCH_QUERIES = [
    "text-to-SQL",
    "NL2SQL",
    "natural language to SQL",
    "natural language interface to database",
    "semantic parsing SQL database",
    "large language model text-to-SQL",
]

VENUE_SEARCH_TERMS = [
    "text-to-sql",
    "text to sql",
    "text2sql",
    "nl2sql",
    "natural language to sql",
    "semantic parsing sql",
    "database question answering",
    "question answering database",
    "large language model sql",
    "llm sql generation",
]


def abstract_from_inverted_index(index):
    if not index:
        return ""
    positions = []
    for word, offsets in index.items():
        for offset in offsets:
            positions.append((offset, word))
    return " ".join(word for _, word in sorted(positions))


def clean_text(text):
    return re.sub(r"\s+", " ", (text or "")).strip()


def openalex_get(url, timeout=12):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Text2SQL-Paper-Summary/1.0 (mailto:example@example.com)"
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def json_get(url, timeout=20):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Text2SQL-Paper-Summary/1.0 (mailto:example@example.com)"
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def source_name(work):
    primary = work.get("primary_location") or {}
    source = primary.get("source") or {}
    if source.get("display_name"):
        return source["display_name"]
    host_venue = work.get("host_venue") or {}
    return host_venue.get("display_name") or work.get("type_crossref") or "Unknown"


def work_url(work):
    doi = work.get("doi") or ""
    if doi:
        return doi
    primary = work.get("primary_location") or {}
    landing = primary.get("landing_page_url")
    if landing:
        return landing
    return work.get("id") or ""


def normalize_s2_paper(paper, venue_override=None, venue_track=None):
    title = clean_text(paper.get("title") or "")
    abstract = clean_text(paper.get("abstract") or "")
    if not title or not abstract:
        return None
    year = str(paper.get("year") or "")
    venue = paper.get("venue") or paper.get("publicationVenue", {}).get("name") or "Unknown"
    authors = [author.get("name", "") for author in paper.get("authors") or [] if author.get("name")]
    url = paper.get("url") or ""
    if paper.get("externalIds", {}).get("DOI"):
        url = "https://doi.org/" + paper["externalIds"]["DOI"]
    entry = {
        "type": paper.get("publicationTypes", [""])[0] if paper.get("publicationTypes") else "",
        "key": paper.get("paperId") or "",
        "author": " and ".join(authors),
        "booktitle": venue,
        "title": title,
        "year": year,
        "abstract": abstract,
        "keywords": ", ".join(paper.get("fieldsOfStudy") or []),
        "url": url,
        "doi": paper.get("externalIds", {}).get("DOI", ""),
        "venue": normalize_venue_name(venue, title, year),
        "venue_track": venue_track or "",
        "semantic_scholar_id": paper.get("paperId") or "",
    }
    entry["venue"] = normalize_entry_venue(entry)
    entry["venue_track"] = publication_category(entry)
    return entry


def normalize_work(work, venue_override=None, venue_track=None):
    title = clean_text(work.get("title") or work.get("display_name") or "")
    if not title:
        return None

    authors = []
    for authorship in work.get("authorships") or []:
        author = authorship.get("author") or {}
        name = author.get("display_name")
        if name:
            authors.append(name)

    concepts = [
        concept.get("display_name", "")
        for concept in work.get("concepts") or []
        if concept.get("display_name")
    ]

    year = str(work.get("publication_year") or "")
    venue = source_name(work)
    venue_label = normalize_venue_name(venue, title, year)

    entry = {
        "type": work.get("type") or "",
        "key": work.get("id") or "",
        "author": " and ".join(authors),
        "booktitle": venue,
        "title": title,
        "year": year,
        "abstract": clean_text(abstract_from_inverted_index(work.get("abstract_inverted_index"))),
        "keywords": ", ".join(concepts),
        "url": work_url(work),
        "doi": work.get("doi") or "",
        "venue": venue_label,
        "venue_track": venue_track or "",
        "openalex_id": work.get("id") or "",
    }
    entry["venue"] = normalize_entry_venue(entry)
    entry["venue_track"] = publication_category(entry)
    return entry


def crawl_query(query, from_year, to_year, max_results, sleep):
    per_page = min(200, max_results)
    cursor = "*"
    collected = []
    base_filter = f"from_publication_date:{from_year}-01-01,to_publication_date:{to_year}-12-31"

    while len(collected) < max_results:
        params = {
            "search": query,
            "filter": base_filter,
            "per-page": str(per_page),
            "cursor": cursor,
            "sort": "publication_date:desc",
        }
        url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
        payload = openalex_get(url)
        results = payload.get("results") or []
        if not results:
            break
        collected.extend(results)
        cursor = (payload.get("meta") or {}).get("next_cursor")
        if not cursor:
            break
        if sleep:
            time.sleep(sleep)
    return collected[:max_results]


def crawl_venue_query(venue_query, term, year, max_results, sleep):
    return crawl_query(f"{term} {venue_query}", year, year, max_results, sleep)


def add_work(by_title, work, venue_override=None, venue_track=None):
    entry = normalize_work(work, venue_override=venue_override, venue_track=venue_track)
    if not entry or not entry["abstract"]:
        return False
    title_key = entry["title"].lower()
    by_title.setdefault(title_key, entry)
    return True


def add_s2_paper(by_title, paper, venue_override=None, venue_track=None):
    entry = normalize_s2_paper(paper, venue_override=venue_override, venue_track=venue_track)
    if not entry:
        return False
    title_key = entry["title"].lower()
    by_title.setdefault(title_key, entry)
    return True


def crawl_s2(query, year, limit):
    fields = "paperId,title,abstract,year,venue,publicationVenue,authors,externalIds,url,fieldsOfStudy,publicationTypes"
    params = {
        "query": query,
        "year": str(year),
        "limit": str(min(limit, 100)),
        "fields": fields,
    }
    url = "https://api.semanticscholar.org/graph/v1/paper/search?" + urllib.parse.urlencode(params)
    payload = json_get(url)
    return payload.get("data") or []


def main():
    parser = argparse.ArgumentParser(description="Crawl Text-to-SQL metadata from OpenAlex")
    parser.add_argument("--output", "-o", default="data/autocrawl/openalex.json")
    parser.add_argument("--from-year", type=int, default=2020)
    parser.add_argument("--to-year", type=int, default=2026)
    parser.add_argument(
        "--max-results",
        type=int,
        default=60,
        help="Maximum works per query per year. The crawler scans each year separately.",
    )
    parser.add_argument("--sleep", type=float, default=0.15)
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Use fewer broad queries for faster local refreshes.",
    )
    parser.add_argument(
        "--source",
        choices=["venues", "global", "both", "s2", "all"],
        default="all",
        help="venues scans ASE-style OpenAlex venues; s2 uses Semantic Scholar; global runs broad OpenAlex keyword search.",
    )
    parser.add_argument(
        "--max-venue-results",
        type=int,
        default=25,
        help="Maximum works per venue-term-year query.",
    )
    parser.add_argument(
        "--limit-venues",
        help="Comma-separated venue abbreviations for local debugging, e.g. ACL,EMNLP,ICLR.",
    )
    args = parser.parse_args()

    by_title = {}
    if args.source in ("venues", "both", "all"):
        terms = VENUE_SEARCH_TERMS[:4] if args.quick else VENUE_SEARCH_TERMS
        allowed_venues = None
        if args.limit_venues:
            allowed_venues = {item.strip().lower() for item in args.limit_venues.split(",") if item.strip()}
        for track, abbr, year, venue_queries in iter_tracked_venues(args.from_year, args.to_year):
            if allowed_venues and abbr.lower() not in allowed_venues:
                continue
            print(f"Crawling tracked venue: {abbr}{year} ({track})", file=sys.stderr)
            before = len(by_title)
            venue_query = venue_queries[0]
            for term in terms:
                try:
                    works = crawl_venue_query(
                        venue_query,
                        term,
                        year,
                        args.max_venue_results,
                        args.sleep,
                    )
                except Exception as exc:
                    print(f"  WARN: {abbr}{year} / {term}: {exc}", file=sys.stderr)
                    continue
                for work in works:
                    add_work(by_title, work, venue_override=f"{abbr}{year}", venue_track=track)
            print(f"  added candidates: {len(by_title) - before}; accumulated: {len(by_title)}", file=sys.stderr)

    if args.source in ("s2", "all"):
        terms = VENUE_SEARCH_TERMS[:4] if args.quick else VENUE_SEARCH_TERMS
        allowed_venues = None
        if args.limit_venues:
            allowed_venues = {item.strip().lower() for item in args.limit_venues.split(",") if item.strip()}
        for track, abbr, year, venue_queries in iter_tracked_venues(args.from_year, args.to_year):
            if allowed_venues and abbr.lower() not in allowed_venues:
                continue
            print(f"Crawling Semantic Scholar venue: {abbr}{year} ({track})", file=sys.stderr)
            before = len(by_title)
            venue_query = venue_queries[0]
            for term in terms:
                try:
                    papers = crawl_s2(f"{term} {venue_query}", year, args.max_venue_results)
                except Exception as exc:
                    print(f"  WARN: S2 {abbr}{year} / {term}: {exc}", file=sys.stderr)
                    continue
                for paper in papers:
                    add_s2_paper(by_title, paper, venue_override=f"{abbr}{year}", venue_track=track)
                if args.sleep:
                    time.sleep(args.sleep)
            print(f"  added candidates: {len(by_title) - before}; accumulated: {len(by_title)}", file=sys.stderr)

    if args.source in ("global", "both", "all"):
        queries = DEFAULT_SEARCH_QUERIES
        if args.quick:
            queries = [
                "text-to-SQL",
                "NL2SQL",
                "natural language to SQL",
                "semantic parsing SQL database",
            ]
        for year in range(args.from_year, args.to_year + 1):
            print(f"Crawling global OpenAlex year: {year}", file=sys.stderr)
            for query in queries:
                print(f"  query: {query}", file=sys.stderr)
                try:
                    works = crawl_query(query, year, year, args.max_results, args.sleep)
                except Exception as exc:
                    print(f"    WARN: query failed: {exc}", file=sys.stderr)
                    continue

                for work in works:
                    add_work(by_title, work)
                print(f"    accumulated candidates: {len(by_title)}", file=sys.stderr)

    papers = {entry["title"]: entry for entry in by_title.values()}
    if not papers:
        print("No candidates collected; keeping existing output unchanged.", file=sys.stderr)
        return
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)

    print(f"Written {len(papers)} candidates to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
