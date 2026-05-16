#!/usr/bin/env python3
"""Create a reproducible stratified audit sample for literature quality checks."""

import argparse
import json
import random
from pathlib import Path

from label_papers import relevance_level
from venues import (
    AI_CCF_A_VENUES,
    ARXIV_VENUE,
    CROSS_CCF_A_VENUES,
    DATABASE_CCF_A_VENUES,
    README_CCF_A_JOURNALS,
    SE_CCF_A_VENUES,
    normalize_entry_venue,
    publication_category,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LABELDATA = REPO_ROOT / "data" / "labeldata" / "labeldata.json"
DEFAULT_PRUNE_REPORT = REPO_ROOT / "data" / "reports" / "pruned_irrelevant.json"
DEFAULT_JSON = REPO_ROOT / "data" / "reports" / "literature_audit_sample.json"
DEFAULT_MD = REPO_ROOT / "data" / "reports" / "literature_audit_sample.md"
SEED = 20260517

JOURNAL_VENUES = sorted({venue for venues in README_CCF_A_JOURNALS.values() for venue in venues})
CCF_CONFERENCE_VENUES = sorted(
    (AI_CCF_A_VENUES | DATABASE_CCF_A_VENUES | SE_CCF_A_VENUES | CROSS_CCF_A_VENUES)
    - set(JOURNAL_VENUES)
)

RISK_TITLES = [
    "Few-shot Text-to-SQL Translation using Structure and Content Prompt Learning",
    "Text-to-SQL Generation for Question Answering on Electronic Medical Records.",
    "SQL-Checker: Error Detection and Labeling for Text-to-SQL with Interpretability Analysis",
    "CoSQA <sup>+</sup> : Enhancing Code Search Evaluation With a Multi-Choice Benchmark and Test-Driven Agents",
    "AI-powered natural language to SQL generation for lange-scale data analysis solutions",
    "A New Paradigm of User-Centric Wireless Communication Driven by Large Language Models",
    "Castle: Causal Cascade Updates in Relational Databases with Large Language Models",
    "Towards Automating Domain-Specific Data Generation for Text-to-SQL: A Comprehensive Approach",
]

KNOWN_SOURCES = {
    "Few-shot Text-to-SQL Translation using Structure and Content Prompt Learning": [
        "https://2023.sigmod.org/sigmod_research_list.shtml",
        "https://dblp.org/rec/journals/pacmmod/GuF00JM023.html",
    ],
    "Text-to-SQL Generation for Question Answering on Electronic Medical Records.": [
        "https://doi.org/10.1145/3366423.3380120",
    ],
    "SQL-Checker: Error Detection and Labeling for Text-to-SQL with Interpretability Analysis": [
        "https://www2026.thewebconf.org/accepted/research-tracks.html",
    ],
    "CoSQA <sup>+</sup> : Enhancing Code Search Evaluation With a Multi-Choice Benchmark and Test-Driven Agents": [
        "https://doi.org/10.1109/TSE.2025.3631886",
    ],
    "AI-powered natural language to SQL generation for lange-scale data analysis solutions": [
        "http://www.theseus.fi/handle/10024/917028",
    ],
    "A New Paradigm of User-Centric Wireless Communication Driven by Large Language Models": [
        "https://arxiv.org/abs/2504.11696",
    ],
    "Castle: Causal Cascade Updates in Relational Databases with Large Language Models": [
        "https://arxiv.org/abs/2511.14762",
    ],
    "Towards Automating Domain-Specific Data Generation for Text-to-SQL: A Comprehensive Approach": [
        "https://doi.org/10.1145/3746226",
    ],
}


def load_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def paper_record(title, entry, present=True, stratum=""):
    entry = dict(entry)
    level = relevance_level(title, entry.get("abstract", ""), entry.get("keywords", ""))
    normalized_venue = normalize_entry_venue(entry)
    if not present or level == "irrelevant":
        verdict = "false_positive_removed" if not present else "false_positive"
    elif level == "core":
        verdict = "true_positive_core"
    else:
        verdict = "true_positive_application"

    sources = []
    for key in ("doi", "url", "openalex_id", "semantic_scholar_id"):
        value = entry.get(key)
        if value:
            sources.append(str(value))
    sources.extend(KNOWN_SOURCES.get(title, []))
    deduped_sources = []
    for source in sources:
        if source not in deduped_sources:
            deduped_sources.append(source)

    missing = []
    if not entry.get("doi"):
        missing.append("doi")
    if not entry.get("abstract"):
        missing.append("abstract")
    notes = []
    if missing:
        notes.append("missing " + ", ".join(missing))
    if not present:
        notes.append("removed by prune-irrelevant")
    if title in KNOWN_SOURCES:
        notes.append("risk-directed sample")

    return {
        "title": entry.get("title") or title,
        "present_in_labeldata": present,
        "stratum": stratum,
        "verdict": verdict,
        "relevance_level_expected": level,
        "venue": entry.get("venue", ""),
        "normalized_venue": normalized_venue,
        "category": publication_category(entry),
        "year": entry.get("year", ""),
        "venue_ok": normalized_venue == normalize_entry_venue(entry),
        "year_ok": bool(entry.get("year")),
        "doi_or_url_ok": bool(entry.get("doi") or entry.get("url")),
        "external_sources": deduped_sources,
        "notes": "; ".join(notes),
    }


def pruned_records(prune_report):
    payload = load_json(prune_report, {})
    out = {}
    for item in payload.get("removed") or []:
        entry = item.get("entry") or item
        title = entry.get("title") or item.get("title")
        if title:
            out[title] = entry
    return out


def sample_from(candidates, n, rng, selected):
    pool = [(title, entry) for title, entry in candidates if title not in selected]
    if len(pool) <= n:
        return pool
    return rng.sample(pool, n)


def main():
    parser = argparse.ArgumentParser(description="Generate literature audit sample")
    parser.add_argument("--labeldata", default=str(DEFAULT_LABELDATA))
    parser.add_argument("--prune-report", default=str(DEFAULT_PRUNE_REPORT))
    parser.add_argument("--output-json", default=str(DEFAULT_JSON))
    parser.add_argument("--output-md", default=str(DEFAULT_MD))
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--sample-size", type=int, default=40)
    parser.add_argument("--max-current-false-positive-ratio", type=float, default=0.10)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    papers = load_json(args.labeldata, {})
    removed = pruned_records(args.prune_report)
    selected = set()
    sample = []

    for title in RISK_TITLES:
        if title in papers:
            sample.append(paper_record(title, papers[title], present=True, stratum="risk"))
            selected.add(title)
        elif title in removed:
            sample.append(paper_record(title, removed[title], present=False, stratum="risk"))
            selected.add(title)

    items = list(papers.items())
    strata = {
        "ccf_conference": [(title, entry) for title, entry in items if normalize_entry_venue(entry) in CCF_CONFERENCE_VENUES],
        "readme_journal": [(title, entry) for title, entry in items if normalize_entry_venue(entry) in JOURNAL_VENUES],
        "arxiv": [(title, entry) for title, entry in items if normalize_entry_venue(entry) == ARXIV_VENUE],
        "supplemental": [
            (title, entry)
            for title, entry in items
            if normalize_entry_venue(entry) == "其他" or entry.get("openalex_id") or entry.get("semantic_scholar_id")
        ],
    }
    for stratum, candidates in strata.items():
        for title, entry in sample_from(candidates, 8, rng, selected):
            sample.append(paper_record(title, entry, present=True, stratum=stratum))
            selected.add(title)

    if len(sample) < args.sample_size:
        for title, entry in sample_from(items, args.sample_size - len(sample), rng, selected):
            sample.append(paper_record(title, entry, present=True, stratum="fill"))
            selected.add(title)
    sample = sample[: args.sample_size]

    current_sample = [item for item in sample if item["present_in_labeldata"]]
    current_false = [item for item in current_sample if item["verdict"] == "false_positive"]
    false_ratio = len(current_false) / len(current_sample) if current_sample else 0.0
    metrics = {
        "seed": args.seed,
        "sample_size": len(sample),
        "current_labeldata_sample_size": len(current_sample),
        "current_false_positive_count": len(current_false),
        "current_false_positive_ratio": round(false_ratio, 6),
        "removed_false_positive_count": sum(1 for item in sample if item["verdict"] == "false_positive_removed"),
    }
    payload = {
        "summary": metrics,
        "sample": sample,
    }
    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    output_md = Path(args.output_md)
    with open(output_md, "w", encoding="utf-8") as f:
        f.write("# Literature Audit Sample\n\n")
        f.write(f"- Seed: `{args.seed}`\n")
        f.write(f"- Sample size: `{len(sample)}`\n")
        f.write(f"- Current false positive ratio: `{false_ratio:.2%}`\n")
        f.write(f"- Removed false positives in risk sample: `{metrics['removed_false_positive_count']}`\n\n")
        f.write("| Stratum | Verdict | Venue | Year | Title | Notes |\n")
        f.write("| --- | --- | --- | --- | --- | --- |\n")
        for item in sample:
            title = item["title"].replace("|", "\\|")
            notes = item["notes"].replace("|", "\\|")
            f.write(
                f"| {item['stratum']} | {item['verdict']} | {item['normalized_venue']} | "
                f"{item['year']} | {title} | {notes} |\n"
            )

    print(f"Written {len(sample)} audit records -> {output_json}")
    print(f"Written audit summary -> {output_md}")
    print(f"Current false positive ratio: {false_ratio:.2%}")
    if false_ratio > args.max_current_false_positive_ratio:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
