#!/usr/bin/env python3
"""Shared paper normalization and merge helpers."""

import html
import re
import unicodedata

from taxonomy import normalize_topic_labels
from venues import (
    ARXIV_VENUE,
    ALL_CCF_A_VENUES,
    OTHER_VENUE,
    normalize_entry_venue,
    publication_category,
    venue_base_name,
)


MOJIBAKE_REPLACEMENTS = {
    "\u00e2\u20ac\u201c": "-",
    "\u00e2\u20ac\u201d": "-",
    "\u00e2\u20ac\u02dc": "'",
    "\u00e2\u20ac\u2122": "'",
    "\u00e2\u20ac\u0153": '"',
    "\u00e2\u20ac\u009d": '"',
    "\u00e2\u20ac\u00a6": "...",
}


def repair_mojibake(text):
    out = text or ""
    for bad, good in MOJIBAKE_REPLACEMENTS.items():
        out = out.replace(bad, good)
    return out


def clean_text(text):
    text = html.unescape(str(text or ""))
    text = repair_mojibake(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\u2010-\u2015\u2212]", "-", text)
    return re.sub(r"\s+", " ", text).strip()


def clean_title(text):
    text = clean_text(text)
    text = re.sub(
        r"\s*\[[^\]]*(experiment|analysis|benchmark|vision|systems)[^\]]*\]\s*\.?$",
        "",
        text,
        flags=re.I,
    )
    return text.strip(" .")


def normalize_title_key(title):
    text = clean_title(title).casefold()
    text = re.sub(r"\btext\s*[- ]?\s*to\s*[- ]?\s*sql\b", "texttosql", text)
    text = re.sub(r"\btext\s*2\s*sql\b", "texttosql", text)
    text = re.sub(r"\bnl\s*[- ]?\s*2\s*sql\b", "nl2sql", text)
    text = re.sub(r"\bnatural\s+language\s+to\s+sql\b", "naturallanguagetosql", text)
    text = re.sub(r"\s*[\.:;,!?]+$", "", text)
    tokens = re.findall(r"[a-z0-9]+", text)
    return " ".join(tokens)


def is_empty(value):
    return value is None or value == "" or value == [] or value == {}


def as_list(value):
    if isinstance(value, list):
        return value
    if is_empty(value):
        return []
    return [value]


def merge_lists(first, second):
    out = []
    seen = set()
    for item in as_list(first) + as_list(second):
        key = str(item)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def known_venue(value):
    base = venue_base_name(value)
    return bool(base and base != OTHER_VENUE)


def known_category(value):
    return bool(value and value != OTHER_VENUE)


def venue_precedence(entry):
    venue = normalize_entry_venue(entry)
    base = venue_base_name(venue)
    if base in ALL_CCF_A_VENUES:
        return 3
    if venue == ARXIV_VENUE:
        return 2
    return 1


def record_score(entry):
    score = 0
    abstract = clean_text(entry.get("abstract", ""))
    if len(abstract) >= 80:
        score += 8
    elif abstract:
        score += 3
    for field, weight in (
        ("doi", 4),
        ("url", 3),
        ("author", 2),
        ("year", 1),
        ("keywords", 1),
        ("openalex_id", 2),
        ("semantic_scholar_id", 2),
        ("key", 1),
    ):
        if not is_empty(entry.get(field)):
            score += weight
    if known_venue(entry.get("venue", "")):
        score += 3
    if known_category(entry.get("venue_track", "")):
        score += 2
    if entry.get("labels"):
        score += 2
    if entry.get("pipeline_stages"):
        score += 2
    return score


def title_score(title):
    text = clean_title(title)
    score = min(len(text), 140)
    if any(bad in (title or "") for bad in MOJIBAKE_REPLACEMENTS):
        score -= 80
    return score


def choose_title(first, second):
    first_title = clean_title(first)
    second_title = clean_title(second)
    if not first_title:
        return second_title
    if not second_title:
        return first_title
    return second_title if title_score(second_title) > title_score(first_title) else first_title


def normalize_paper_metadata(entry):
    out = dict(entry)
    if out.get("title"):
        out["title"] = clean_title(out.get("title", ""))
    venue = normalize_entry_venue(out)
    out["venue"] = ARXIV_VENUE if venue == ARXIV_VENUE else venue
    out["venue_track"] = publication_category(out)
    out["labels"] = normalize_topic_labels(out.get("labels", []))
    return out


SOURCE_VENUE_FIELDS = {"booktitle", "journal", "container", "source", "publisher"}


def choose_venue_entry(first, second, primary):
    first_priority = venue_precedence(first)
    second_priority = venue_precedence(second)
    if first_priority > second_priority:
        return first
    if second_priority > first_priority:
        return second
    return primary


def apply_venue_metadata(merged, venue_entry):
    normalized = normalize_paper_metadata(venue_entry)
    for field in SOURCE_VENUE_FIELDS:
        value = normalized.get(field, "")
        if value:
            merged[field] = value
        else:
            merged.pop(field, None)
    if normalized.get("year"):
        merged["year"] = normalized["year"]
    merged["venue"] = normalized.get("venue", OTHER_VENUE)
    merged["venue_track"] = normalized.get("venue_track", publication_category(normalized))
    return merged


def merge_entries(existing, incoming, prefer_existing=False):
    existing = normalize_paper_metadata(existing)
    incoming = normalize_paper_metadata(incoming)
    if prefer_existing:
        primary, secondary = existing, incoming
    elif record_score(incoming) > record_score(existing):
        primary, secondary = incoming, existing
    else:
        primary, secondary = existing, incoming

    venue_entry = choose_venue_entry(existing, incoming, primary)
    merged = dict(primary)
    merged["title"] = choose_title(primary.get("title", ""), secondary.get("title", ""))

    for field, value in secondary.items():
        if field in {"labels", "pipeline_stages"}:
            merged[field] = merge_lists(merged.get(field), value)
            continue
        if field == "title" or field in SOURCE_VENUE_FIELDS:
            continue
        if field == "abstract":
            current = clean_text(merged.get(field, ""))
            candidate = clean_text(value)
            if not current or (candidate and len(candidate) > len(current) + 40):
                merged[field] = candidate
            continue
        if field == "venue":
            continue
        if field == "venue_track":
            continue
        if is_empty(merged.get(field)) and not is_empty(value):
            merged[field] = value

    merged["labels"] = normalize_topic_labels(merged.get("labels", []))
    merged = apply_venue_metadata(merged, venue_entry)
    return normalize_paper_metadata(merged)


def dedupe_papers(papers):
    merged = {}
    index = {}
    duplicates = 0
    for title, entry in papers.items():
        entry = normalize_paper_metadata({**entry, "title": entry.get("title") or title})
        key = normalize_title_key(entry.get("title") or title)
        if not key:
            continue
        if key in index:
            existing_key = index[key]
            combined = merge_entries(merged[existing_key], entry)
            new_key = combined.get("title") or existing_key
            if new_key != existing_key:
                del merged[existing_key]
            merged[new_key] = combined
            index[key] = new_key
            duplicates += 1
        else:
            out_key = entry.get("title") or title
            merged[out_key] = entry
            index[key] = out_key
    return dict(sorted(merged.items())), duplicates


def upsert_paper(papers, index, title, entry, no_overwrite=False):
    entry = normalize_paper_metadata({**entry, "title": entry.get("title") or title})
    key = normalize_title_key(entry.get("title") or title)
    if not key:
        return "invalid"
    if key not in index:
        out_key = entry.get("title") or title
        papers[out_key] = entry
        index[key] = out_key
        return "added"

    existing_key = index[key]
    before = papers[existing_key]
    merged = merge_entries(before, entry, prefer_existing=no_overwrite)
    new_key = merged.get("title") or existing_key
    changed = merged != before or new_key != existing_key
    if new_key != existing_key:
        del papers[existing_key]
    papers[new_key] = merged
    index[key] = new_key
    if no_overwrite and not changed:
        return "skipped"
    return "updated" if changed else "skipped"
