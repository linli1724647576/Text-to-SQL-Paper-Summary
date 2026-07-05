#!/usr/bin/env python3
"""Crawl Text-to-SQL paper metadata from OpenAlex.

OpenAlex provides reproducible API-backed supplemental searches. The script
gathers candidates by multiple Text-to-SQL queries, normalizes metadata, and
leaves relevance filtering/classification to label_papers.py.
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from openalex_utils import abstract_from_inverted_index, get_openalex_json
from paper_utils import arxiv_id_from_openalex_work, normalize_title_key
from venues import (
    iter_ccf_a_venues,
    iter_readme_journals,
    iter_tracked_venues,
    normalize_entry_venue,
    normalize_venue_name,
    publication_category,
    venue_base_name,
)


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

CCF_VENUE_SEARCH_TERMS = [
    "text-to-sql",
    "text to sql",
    "text2sql",
    "nl2sql",
    "natural language to sql",
    "natural language interface to database",
    "semantic parsing sql",
    "database question answering",
    "sql generation",
    "llm sql generation",
]

CCF_VENUE_QUERIES = {
    "AAAI": ["AAAI Conference on Artificial Intelligence", "AAAI"],
    "ACL": ["Annual Meeting of the Association for Computational Linguistics", "ACL"],
    "AIJ": ["Artificial Intelligence", "Artificial Intelligence Journal"],
    "ASE": ["Automated Software Engineering", "IEEE/ACM International Conference on Automated Software Engineering"],
    "CVPR": ["Computer Vision and Pattern Recognition", "CVPR"],
    "FSE": ["Foundations of Software Engineering", "ESEC/FSE"],
    "ICCV": ["International Conference on Computer Vision", "ICCV"],
    "ICDE": ["International Conference on Data Engineering", "ICDE"],
    "ICML": ["International Conference on Machine Learning", "ICML"],
    "ICSE": ["International Conference on Software Engineering", "ICSE"],
    "IJCAI": ["International Joint Conference on Artificial Intelligence", "IJCAI"],
    "ISSTA": ["International Symposium on Software Testing and Analysis", "ISSTA"],
    "KDD": ["Knowledge Discovery and Data Mining", "KDD"],
    "NeurIPS": ["Neural Information Processing Systems", "NeurIPS"],
    "SIGIR": ["Research and Development in Information Retrieval", "SIGIR"],
    "SIGMOD": ["ACM SIGMOD", "Proceedings of the ACM on Management of Data"],
    "TKDE": ["IEEE Transactions on Knowledge and Data Engineering", "TKDE"],
    "TOSEM": ["ACM Transactions on Software Engineering and Methodology", "TOSEM"],
    "TSE": ["IEEE Transactions on Software Engineering", "TSE"],
    "VLDB": ["Proceedings of the VLDB Endowment", "PVLDB", "Very Large Data Bases"],
    "VLDBJ": ["VLDB Journal", "The VLDB Journal"],
    "WWW": ["The Web Conference", "World Wide Web Conference"],
}


def current_year():
    return datetime.now(timezone.utc).year


def clean_text(text):
    return re.sub(r"\s+", " ", (text or "")).strip()


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
    venue_label = normalize_venue_name(venue_override or venue, title, year)

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
    arxiv_id = arxiv_id_from_openalex_work(work)
    if arxiv_id:
        entry["arxiv_id"] = arxiv_id
    entry["venue"] = normalize_entry_venue(entry)
    entry["venue_track"] = publication_category(entry)
    return entry


def high_confidence_venue_source(text, target_venue):
    source = clean_text(text).lower()
    if not source:
        return False
    target = venue_base_name(target_venue)
    if target == "ACL" and "findings" in source:
        return False
    normalized = venue_base_name(normalize_venue_name(source))
    if normalized == target:
        return True
    # OpenAlex often represents PVLDB as a journal-like source rather than the
    # conference name. Treat PVLDB as VLDB only for the explicit VLDB target.
    if target == "VLDB" and ("vldb endowment" in source or "pvldb" in source):
        return True
    return False


def openalex_source_matches(work, target_venue):
    source = source_name(work)
    primary = work.get("primary_location") or {}
    source_obj = primary.get("source") or {}
    candidates = [
        source,
        source_obj.get("display_name") or "",
        work.get("type_crossref") or "",
    ]
    return any(high_confidence_venue_source(candidate, target_venue) for candidate in candidates)


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
        payload = get_openalex_json("https://api.openalex.org/works", params, timeout=12)
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


def add_work(by_title, work, venue_override=None, venue_track=None, require_venue_match=False):
    if venue_override and require_venue_match and not openalex_source_matches(work, venue_override):
        return False
    entry = normalize_work(work, venue_override=venue_override, venue_track=venue_track)
    if not entry or not entry["abstract"]:
        return False
    title_key = normalize_title_key(entry["title"])
    by_title.setdefault(title_key, entry)
    return True


def ccf_venue_queries(abbr):
    return CCF_VENUE_QUERIES.get(abbr, [abbr])


def iter_ccf_search_venues(from_year, to_year, allowed_venues=None):
    for track, abbr, _dblp_key, year in iter_ccf_a_venues(from_year, to_year, tracks=["AI", "DB", "SE"]):
        if allowed_venues and abbr.lower() not in allowed_venues:
            continue
        yield track, abbr, year, ccf_venue_queries(abbr)
    for track, abbr, _dblp_key, year in iter_readme_journals(from_year, to_year, tracks=["AI", "DB", "SE"]):
        if allowed_venues and abbr.lower() not in allowed_venues:
            continue
        yield track, abbr, year, ccf_venue_queries(abbr)


def crawl_ccf_venues(by_title, args):
    terms = CCF_VENUE_SEARCH_TERMS[:4] if args.quick else CCF_VENUE_SEARCH_TERMS
    allowed_venues = None
    if args.limit_venues:
        allowed_venues = {item.strip().lower() for item in args.limit_venues.split(",") if item.strip()}
    for track, abbr, year, venue_queries in iter_ccf_search_venues(args.from_year, args.to_year, allowed_venues):
        venue_query = venue_queries[0]
        print(f"Crawling CCF-A venue: {abbr}{year} ({track})", file=sys.stderr)
        before = len(by_title)
        for term in terms:
            try:
                works = crawl_venue_query(venue_query, term, year, args.max_venue_results, args.sleep)
            except Exception as exc:
                print(f"  WARN: OpenAlex {abbr}{year} / {term}: {exc}", file=sys.stderr)
                continue
            for work in works:
                add_work(
                    by_title,
                    work,
                    venue_override=f"{abbr}{year}",
                    venue_track=track,
                    require_venue_match=True,
                )
        print(f"  added candidates: {len(by_title) - before}; accumulated: {len(by_title)}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Crawl Text-to-SQL metadata from OpenAlex")
    parser.add_argument("--output", "-o", default="data/autocrawl/openalex.json")
    parser.add_argument("--from-year", type=int, default=2020)
    parser.add_argument("--to-year", type=int, default=current_year())
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
        choices=["supplemental", "venues", "global", "both", "all", "ccf", "ccf-supplemental"],
        default="supplemental",
        help="supplemental runs broad search; ccf-supplemental adds high-confidence CCF-A venue-year search.",
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
    if args.source in ("ccf", "ccf-supplemental", "all"):
        crawl_ccf_venues(by_title, args)

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

    if args.source in ("global", "both", "all", "supplemental", "ccf-supplemental"):
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
