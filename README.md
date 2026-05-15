# Text-to-SQL Paper Summary

[![Build, Crawl, and Deploy Pages](https://github.com/linli1724647576/Text-to-SQL-Paper-Summary/actions/workflows/pages.yml/badge.svg)](https://github.com/linli1724647576/Text-to-SQL-Paper-Summary/actions/workflows/pages.yml)

A GitHub Pages literature browser for **Text-to-SQL / NL2SQL** research. The project follows the same pipeline style as [PurCL/ASE](https://github.com/PurCL/ASE): collect raw proceedings, extract papers, filter relevant work, classify papers, merge the database, and rebuild a static website.

Website, after deployment:

```text
https://linli1724647576.github.io/Text-to-SQL-Paper-Summary/
```

## Current Status

The repository is ready for GitHub deployment and full crawl through GitHub Actions.

| Item | Current local value |
| --- | ---: |
| Classified Text-to-SQL papers | 0 |
| Rawdata venue/year files downloaded | 88 |
| Website output | `web/index.html` |
| Full crawl mode | GitHub Actions manual trigger |

The classified paper count is currently `0` because the previous API-bootstrap data was removed to avoid unreliable venue labels. Run the full crawl workflow on GitHub to populate `data/labeldata/labeldata.json` and rebuild the website with real data.

## What The Website Supports

- Full-text search over paper title, abstract, author, venue, topic labels, and pipeline labels.
- Year and venue filters.
- Research-topic filters.
- Text-to-SQL pipeline-stage filters.
- Clickable label pills on paper cards.
- Expandable abstracts.
- Static GitHub Pages deployment, no backend required.

## Text-to-SQL Pipeline Taxonomy

The website includes the five-stage Text-to-SQL pipeline dimension:

| Stage | Sub-stages |
| --- | --- |
| Task Understanding | Intent Detection, Question Decomposition, Dialogue Context Tracking, Domain Constraint Understanding |
| Grounding | Schema Linking, Value Linking, Context Retrieval, Database Content Grounding |
| Query Planning | SQL Sketch / Skeleton, Intermediate Representation, Join Path Planning, Step-by-step Reasoning |
| SQL Generation | Prompt-based Generation, Fine-tuned Generation, Constrained Decoding, Dialect Adaptation |
| Verification & Repair | Execution Feedback, Self-correction, Static SQL Validation, Result Validation |

## Research Topic Taxonomy

The topic taxonomy is designed around common Text-to-SQL research axes:

| Group | Examples |
| --- | --- |
| Task Setting | Single-turn, multi-turn, cross-domain, enterprise BI, conversational data analysis |
| Pre-training and Fine-tuning | Pre-training, supervised fine-tuning, instruction tuning, RL, distillation |
| Prompting and ICL | Zero/few-shot ICL, prompt engineering, CoT, self-consistency, example selection |
| Grounding and Retrieval | Schema linking, value linking, schema/content retrieval, semantic layers, external knowledge |
| Planning and Generation | IR/sketches, decomposition, join planning, constrained decoding, dialect adaptation |
| Agentic Feedback and Repair | Agents, tool use, execution guidance, self-repair, verification, guardrails, human feedback |
| Benchmarks and Evaluation | Datasets, benchmarks, metrics, robustness, contamination, industrial evaluation |

The taxonomy lives in [`scripts/taxonomy.py`](scripts/taxonomy.py).

## Data Sources

The full crawl targets CCF-A venues in AI, DB, Software Engineering, and Security, plus arXiv Text-to-SQL preprints.

| Area | Venues |
| --- | --- |
| AI | AAAI, NeurIPS, ACL, CVPR, ICCV, ICML, IJCAI |
| DB / IR / Web | SIGMOD, VLDB, ICDE, KDD, WWW, SIGIR |
| SE | ICSE, FSE, ASE, ISSTA |
| Security | CCS, S&P, USENIX Security, NDSS |
| Preprints | arXiv Text-to-SQL / NL2SQL queries |

Venue labels are normalized from rawdata filenames, for example `ACL2024`, `SIGMOD2025`, `ICSE2023`, and `CCS2024`.

## Full Crawl On GitHub

After this repository is pushed to GitHub:

1. Open **Actions**.
2. Select **Build, Crawl, and Deploy Pages**.
3. Click **Run workflow**.
4. Set:
   - `full_crawl = true`
   - `process_rawdata = true`
   - `from_year = 2020`
   - `to_year = 2026`
5. Start the workflow.

Recommended repository secret:

```text
SEMANTIC_SCHOLAR_API_KEY
```

This reduces Semantic Scholar rate limits while enriching DBLP rawdata with abstracts. Without this key, the workflow can still run, but abstract enrichment may be incomplete due to HTTP 429 limits.

## Local Pipeline

Run the same flow locally:

```bash
python scripts/fetch_rawdata.py --from-year 2020 --to-year 2026
python scripts/enrich_abstracts.py data/rawdata --delay 1.0
python scripts/process_folder.py
python scripts/build_site.py
```

Pipeline stages:

```text
fetch_rawdata.py
  -> enrich_abstracts.py
  -> extract_papers.py
  -> label_papers.py
  -> merge_labeldata.py
  -> build_site.py
```

## Supported Rawdata Formats

Place raw proceedings under `data/rawdata/<year>/`.

Supported formats:

- BibTeX with `title` and optional `abstract`.
- ACL Anthology-style HTML proceedings pages.
- NDSS-style HTML proceedings pages.
- JSON shaped as `{ "Paper title": { ... } }` or `[ { "title": "...", ... } ]`.
- CSV with at least `title` and `abstract` columns.

## Build Only

```bash
python scripts/build_site.py
```

Output:

```text
web/index.html
```

## Notes

DBLP proceedings often do not include abstracts. This project therefore separates rawdata collection from abstract enrichment. Filtering and classification are much more reliable after `enrich_abstracts.py` has filled abstracts from Semantic Scholar.
