#!/usr/bin/env python3
"""Enrich paper JSON files with abstracts via Semantic Scholar."""

import argparse
import html as html_lib
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import tempfile
from pathlib import Path

from http_utils import get_json as http_get_json, get_text as http_get_text, post_json as http_post_json, request as http_request


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


def get_json(url, timeout=20):
    headers = {}
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key
    return http_get_json(url, timeout=timeout, headers=headers)


def post_json(url, payload, timeout=30):
    headers = {
        "Content-Type": "application/json",
    }
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key
    return http_post_json(url, payload, timeout=timeout, headers=headers)


def get_text(url, timeout=20):
    return http_get_text(url, timeout=timeout)


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


def source_abstract(entry, title):
    url = clean(entry.get("url", ""))
    doi = entry_doi(entry)
    if url.lower().endswith(".pdf"):
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


def doi_id(entry):
    doi = entry_doi(entry)
    if not doi:
        return ""
    if not entry.get("doi"):
        entry["doi"] = doi
    return "DOI:" + doi


def batch_by_doi(entries):
    indexed = []
    ids = []
    for title, entry in entries:
        if entry.get("abstract"):
            continue
        paper_id = doi_id(entry)
        if not paper_id:
            continue
        indexed.append((title, entry, paper_id))
        ids.append(paper_id)
    if not ids:
        return 0

    fields = "title,abstract,year,venue,externalIds,url"

    def apply_results(payload, chunk):
        updated = 0
        for result, (_, entry, _) in zip(payload, chunk):
            if not result:
                continue
            abstract = clean(result.get("abstract", ""))
            if abstract:
                entry["abstract"] = abstract
                updated += 1
            external_ids = result.get("externalIds") or {}
            result_doi = normalize_doi(external_ids.get("DOI", ""))
            if result_doi and not entry.get("doi"):
                entry["doi"] = result_doi
            if not entry.get("url") and result.get("url"):
                entry["url"] = result["url"]
        return updated

    def fetch_chunk(chunk):
        payload = post_json(
            "https://api.semanticscholar.org/graph/v1/paper/batch?"
            + urllib.parse.urlencode({"fields": fields}),
            {"ids": [paper_id for _, _, paper_id in chunk]},
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
    for start in range(0, len(indexed), 500):
        updated += fetch_resilient(indexed[start:start + 500])
    return updated


def enrich_file(path, limit=None, delay=1.0, skip_title_search=False, skip_doi_batch=False):
    with open(path, encoding="utf-8") as f:
        papers = json.load(f)
    items = list(papers.items())
    if skip_doi_batch:
        updated = 0
    else:
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
            abstract = source_abstract(entry, entry.get("title") or title)
            if abstract:
                entry["abstract"] = abstract
                updated += 1
                continue
        except Exception as exc:
            print(f"WARN: source fallback {title[:80]}: {exc}", file=sys.stderr)
        if skip_title_search:
            continue
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
    parser.add_argument("--skip-doi-batch", action="store_true")
    parser.add_argument("--skip-title-search", action="store_true")
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
        updated, checked = enrich_file(
            path,
            limit=args.limit_per_file,
            delay=args.delay,
            skip_doi_batch=args.skip_doi_batch,
            skip_title_search=args.skip_title_search,
        )
        total_updated += updated
        print(f"  updated {updated}/{checked}", file=sys.stderr)
    print(f"Total updated abstracts: {total_updated}", file=sys.stderr)


if __name__ == "__main__":
    main()
