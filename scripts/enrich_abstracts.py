#!/usr/bin/env python3
"""Enrich paper JSON files with abstracts via OpenAlex and source pages."""

import argparse
import html as html_lib
import json
import re
import subprocess
import sys
import time
import urllib.parse
import tempfile
from pathlib import Path

from http_utils import get_text as http_get_text, request as http_request
from openalex_utils import abstract_from_inverted_index, get_openalex_json
from paper_utils import arxiv_id_from_openalex_work


def clean(text):
    return re.sub(r"\s+", " ", (text or "")).strip()


def clean_html(text):
    text = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", text or "")
    text = re.sub(r"(?is)<br\s*/?>|</p>|</div>|</li>|</h\d>", " ", text)
    text = re.sub(r"(?is)<.*?>", " ", text)
    return clean(html_lib.unescape(text))


def simple_title_key(text):
    text = clean_html(text).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return clean(text)


def get_text(url, timeout=20):
    return http_get_text(url, timeout=timeout)


def search_title(title):
    params = {
        "search": title,
        "per-page": "3",
        "select": "id,title,doi,abstract_inverted_index,primary_location",
    }
    payload = get_openalex_json("https://api.openalex.org/works", params, timeout=20)
    title_norm = clean(title).lower()
    for work in payload.get("results") or []:
        candidate = clean(work.get("title", "")).lower()
        if candidate == title_norm or title_norm in candidate or candidate in title_norm:
            abstract = clean(abstract_from_inverted_index(work.get("abstract_inverted_index")))
            if abstract:
                return abstract
    return ""


def meta_content(html, names):
    for name in names:
        pattern = (
            r"<meta\b(?=[^>]*(?:name|property)=[\"']"
            + re.escape(name)
            + r"[\"'])(?=[^>]*content=[\"']([^\"']*)[\"'])[^>]*>"
        )
        match = re.search(pattern, html, flags=re.I)
        if match:
            value = clean_html(match.group(1))
            if value:
                return value
    return ""


def abstract_from_html(html):
    abstract = meta_content(html, ["DC.Description", "citation_abstract", "description"])
    if abstract:
        return abstract
    patterns = [
        r"<div[^>]+id=[\"']abstractText[\"'][^>]*>.*?<div[^>]+class=[\"'][^\"']*abstract-text-inner[^\"']*[\"'][^>]*>(.*?)</div>\s*</div>",
        r"<div[^>]*class=[\"'][^\"']*acl-abstract[^\"']*[\"'][^>]*>.*?<span[^>]*>(.*?)</span>",
        r"<div[^>]*id=[\"']abstract[\"'][^>]*>(.*?)</div>",
        r"<p[^>]*class=[\"']paper-abstract[\"'][^>]*>(.*?)</section>",
    ]
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.I | re.S)
        if match:
            abstract = clean_html(match.group(1))
            if abstract:
                return abstract
    return ""


def apply_jsonld_metadata(entry, html):
    if entry.get("author"):
        return
    for match in re.finditer(
        r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        html,
        flags=re.I | re.S,
    ):
        try:
            payload = json.loads(html_lib.unescape(match.group(1)))
        except Exception:
            continue
        authors = payload.get("author") or []
        if isinstance(authors, dict):
            authors = [authors]
        names = [clean(author.get("name", "")) for author in authors if isinstance(author, dict)]
        names = [name for name in names if name]
        if names:
            entry["author"] = " and ".join(names)
            return


def abstract_from_pdf(url):
    data = http_request(url, timeout=40)
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        tmp.write(data)
        tmp.flush()
        try:
            result = subprocess.run(
                ["pdftotext", "-f", "1", "-l", "2", "-raw", tmp.name, "-"],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (FileNotFoundError, subprocess.SubprocessError):
            return ""
    text = result.stdout
    text = re.sub(r"-\n(?=[a-z])", "", text)
    match = re.search(
        r"(?is)\babstract\b[:.\s-]*(.*?)(?:\n\s*(?:p?vldb reference format|(?:1\s+)?introduction|keywords?|ccs concepts)\b)",
        text,
    )
    if not match:
        return ""
    abstract = clean(match.group(1))
    if len(abstract.split()) < 20:
        return ""
    return abstract


def find_indexed_paper_url(index_url, title, link_text="abs"):
    html = get_text(index_url, timeout=40)
    target = simple_title_key(title)
    for block in re.findall(r"(?is)<div class=[\"']paper[\"']>(.*?)</div>", html):
        title_match = re.search(r"(?is)<p class=[\"']title[\"']>(.*?)</p>", block)
        if not title_match or simple_title_key(title_match.group(1)) != target:
            continue
        link_match = re.search(
            r"(?is)<a href=[\"']([^\"']+)[\"'][^>]*>\s*" + re.escape(link_text) + r"\s*</a>",
            block,
        )
        if link_match:
            return urllib.parse.urljoin(index_url, link_match.group(1))
    return ""


def find_neurips_paper_url(index_url, title):
    html = get_text(index_url, timeout=40)
    target = simple_title_key(title)
    for match in re.finditer(r"(?is)<a[^>]+href=[\"']([^\"']+-Abstract[^\"']*)[\"'][^>]*>(.*?)</a>", html):
        if simple_title_key(match.group(2)) == target:
            return urllib.parse.urljoin(index_url, match.group(1))
    return ""


def source_abstract(entry, title, skip_pdf=False):
    url = clean(entry.get("url", ""))
    doi = entry_doi(entry)
    if "/virtual/" in url and re.search(r"/(?:poster|paper)/", url):
        html = get_text(url, timeout=30)
        apply_jsonld_metadata(entry, html)
        return abstract_from_html(html)
    if "conf.researchr.org/details/" in url:
        html = get_text(url, timeout=30)
        apply_jsonld_metadata(entry, html)
        return abstract_from_html(html)
    if url.lower().endswith(".pdf"):
        if skip_pdf:
            return ""
        return abstract_from_pdf(url)
    if "proceedings.mlr.press/" in url:
        paper_url = url if url.endswith(".html") else find_indexed_paper_url(url, title)
        if paper_url:
            abstract = abstract_from_html(get_text(paper_url, timeout=30))
            if abstract:
                entry["url"] = paper_url
                return abstract
    if "proceedings.neurips.cc/" in url:
        paper_url = url if "Abstract" in url else find_neurips_paper_url(url, title)
        if paper_url:
            abstract = abstract_from_html(get_text(paper_url, timeout=30))
            if abstract:
                entry["url"] = paper_url
                return abstract
    if doi.lower().startswith("10.18653/v1/"):
        anthology_id = re.sub(r"^10\.18653/v1/", "", doi, flags=re.I)
        paper_url = "https://aclanthology.org/" + anthology_id + "/"
        abstract = abstract_from_html(get_text(paper_url, timeout=30))
        if abstract:
            entry["url"] = paper_url
            return abstract
    if doi:
        abstract = abstract_from_html(get_text("https://doi.org/" + doi, timeout=30))
        if abstract:
            return abstract
    return ""


DOI_RE = re.compile(r"(10\.\d{4,9}/[^\s\"<>]+)", re.I)


def normalize_doi(value):
    value = urllib.parse.unquote(clean(value))
    if not value:
        return ""
    value = re.sub(r"^doi:\s*", "", value, flags=re.I)
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value, flags=re.I)
    match = DOI_RE.search(value)
    if not match:
        return ""
    doi = match.group(1).strip()
    return doi.rstrip(".,;:)]}")


def entry_doi(entry):
    for field in ("doi", "url", "ee", "paper_url"):
        doi = normalize_doi(entry.get(field, ""))
        if doi:
            return doi
    return ""


def openalex_work_url(work):
    primary = work.get("primary_location") or {}
    landing = primary.get("landing_page_url") or ""
    return landing or work.get("doi") or work.get("id") or ""


def batch_by_doi(entries):
    indexed = []
    for title, entry in entries:
        if entry.get("abstract"):
            continue
        doi = entry_doi(entry)
        if not doi:
            continue
        if not entry.get("doi"):
            entry["doi"] = doi
        indexed.append((title, entry, doi))
    if not indexed:
        return 0

    def apply_results(payload, chunk):
        by_doi = {
            normalize_doi(work.get("doi", "")): work
            for work in payload.get("results") or []
            if normalize_doi(work.get("doi", ""))
        }
        updated = 0
        for _, entry, doi in chunk:
            work = by_doi.get(doi.lower()) or by_doi.get(doi)
            if not work:
                continue
            abstract = clean(abstract_from_inverted_index(work.get("abstract_inverted_index")))
            if abstract:
                entry["abstract"] = abstract
                updated += 1
            result_doi = normalize_doi(work.get("doi", ""))
            if result_doi and not entry.get("doi"):
                entry["doi"] = result_doi
            if work.get("id"):
                entry["openalex_id"] = work["id"]
            arxiv_id = arxiv_id_from_openalex_work(work)
            if arxiv_id and not entry.get("arxiv_id"):
                entry["arxiv_id"] = arxiv_id
            url = openalex_work_url(work)
            if url:
                entry["url"] = url
        return updated

    def fetch_chunk(chunk):
        payload = get_openalex_json(
            "https://api.openalex.org/works",
            {
                "filter": "doi:" + "|".join(doi for _, _, doi in chunk),
                "per-page": str(len(chunk)),
                "select": "id,title,doi,abstract_inverted_index,primary_location,best_oa_location,locations",
            },
            timeout=30,
        )
        return apply_results(payload, chunk)

    def fetch_resilient(chunk):
        try:
            return fetch_chunk(chunk)
        except Exception as exc:
            if "429" in str(exc):
                print(f"WARN: DOI batch rate-limited for {len(chunk)} ids: {exc}", file=sys.stderr)
                return 0
            if len(chunk) <= 1:
                print(f"WARN: DOI batch skipped {chunk[0][2]}: {exc}", file=sys.stderr)
                return 0
            mid = len(chunk) // 2
            return fetch_resilient(chunk[:mid]) + fetch_resilient(chunk[mid:])

    updated = 0
    for start in range(0, len(indexed), 100):
        updated += fetch_resilient(indexed[start:start + 100])
    return updated


def candidate_items(items, limit=None, title_filter=None):
    candidates = []
    for title, entry in items:
        if entry.get("abstract"):
            continue
        entry_title = entry.get("title") or title
        if title_filter and not title_filter.search(entry_title):
            continue
        if limit is not None and len(candidates) >= limit:
            break
        candidates.append((title, entry))
    return candidates


def enrich_file(
    path,
    limit=None,
    delay=1.0,
    skip_title_search=False,
    skip_doi_batch=False,
    skip_pdf=False,
    title_filter=None,
):
    with open(path, encoding="utf-8") as f:
        papers = json.load(f)
    items = list(papers.items())
    candidates = candidate_items(items, limit=limit, title_filter=title_filter)
    if skip_doi_batch:
        updated = 0
    else:
        try:
            updated = batch_by_doi(candidates)
        except Exception as exc:
            print(f"WARN: DOI batch failed for {path}: {exc}", file=sys.stderr)
            updated = 0
    for title, entry in candidates:
        if entry.get("abstract"):
            continue
        entry_title = entry.get("title") or title
        try:
            abstract = source_abstract(entry, entry_title, skip_pdf=skip_pdf)
            if abstract:
                entry["abstract"] = abstract
                updated += 1
                continue
        except Exception as exc:
            print(f"WARN: source fallback {title[:80]}: {exc}", file=sys.stderr)
        if skip_title_search:
            continue
        try:
            abstract = search_title(entry_title)
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
    return updated, len(candidates)


def venue_from_path(path):
    match = re.match(r"([A-Za-z]+)\d{4}", Path(path).stem)
    return match.group(1).lower() if match else ""


def selected_files(paths, allowed_venues=None):
    allowed = {item.strip().lower() for item in (allowed_venues or []) if item.strip()}
    files = []
    for item in paths:
        path = Path(item)
        if path.is_dir():
            candidates = sorted(path.rglob("*.json"))
        else:
            candidates = [path]
        for candidate in candidates:
            if allowed and venue_from_path(candidate) not in allowed:
                continue
            files.append(candidate)
    return files


def main():
    parser = argparse.ArgumentParser(description="Enrich rawdata JSON abstracts")
    parser.add_argument("paths", nargs="+", help="JSON files or directories")
    parser.add_argument("--limit-per-file", type=int)
    parser.add_argument("--global-limit", type=int, help="Stop after checking this many eligible records across all files")
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--skip-doi-batch", action="store_true")
    parser.add_argument("--skip-title-search", action="store_true")
    parser.add_argument("--skip-pdf", action="store_true", help="Skip direct PDF downloads during source fallback")
    parser.add_argument("--venues", help="Comma-separated venue abbreviations to process when paths contain rawdata directories")
    parser.add_argument(
        "--title-filter",
        help="Only enrich records whose title matches this regex.",
    )
    args = parser.parse_args()

    allowed_venues = args.venues.split(",") if args.venues else None
    files = selected_files(args.paths, allowed_venues=allowed_venues)

    total_updated = 0
    total_checked = 0
    title_filter = re.compile(args.title_filter, re.I) if args.title_filter else None
    for path in files:
        if path.name == "fetch_failures.json":
            continue
        remaining = None
        if args.global_limit is not None:
            remaining = max(0, args.global_limit - total_checked)
            if remaining == 0:
                break
        limit = args.limit_per_file
        if remaining is not None:
            limit = remaining if limit is None else min(limit, remaining)
        print(f"Enriching {path}", file=sys.stderr)
        updated, checked = enrich_file(
            path,
            limit=limit,
            delay=args.delay,
            skip_doi_batch=args.skip_doi_batch,
            skip_title_search=args.skip_title_search,
            skip_pdf=args.skip_pdf,
            title_filter=title_filter,
        )
        total_updated += updated
        total_checked += checked
        print(f"  updated {updated}/{checked}", file=sys.stderr)
    print(f"Total updated abstracts: {total_updated}; checked: {total_checked}", file=sys.stderr)


if __name__ == "__main__":
    main()
