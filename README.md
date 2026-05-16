# Text-to-SQL Paper Summary <a href="https://github.com/linli1724647576/Text-to-SQL-Paper-Summary"><img src="https://img.shields.io/github/stars/linli1724647576/Text-to-SQL-Paper-Summary" width="120" height="26" /></a>

A curated paper list and static browser for **Text-to-SQL / NL2SQL / natural-language database querying** research.

This repository follows an ASE-style workflow: crawl DBLP/arXiv raw metadata, fetch official accepted-paper pages, enrich missing abstracts, filter Text-to-SQL related papers, assign topic and pipeline labels, merge the canonical dataset, and rebuild the website.

Current snapshot:

- **463** classified Text-to-SQL papers
- **174** rawdata files under `data/rawdata/`
- **38** official accepted/proceedings source files
- **44,130** official accepted candidates before relevance filtering
- Website: <https://linli1724647576.github.io/Text-to-SQL-Paper-Summary/>

## Table of Contents

- [Website](#website)
- [Tracked Scope](#tracked-scope)
- [Paper Counts](#paper-counts)
- [Official Accepted Sources](#official-accepted-sources)
- [Taxonomy](#taxonomy)
- [Update Pipeline](#update-pipeline)
- [Daily Automation](#daily-automation)
- [Adding Papers](#adding-papers)
- [Disclaimer](#disclaimer)

## Website

Open the online browser:

<https://linli1724647576.github.io/Text-to-SQL-Paper-Summary/>

The browser supports:

- full-text search over title, abstract, authors, venue, category, topic labels, and pipeline labels
- dynamic filters for category, year, venue, topic, and pipeline stage
- strict venue buckets: CCF-A venue/journal name, `ArXiv`, or `其他`
- strict category buckets: `软件工程`, `数据库领域`, `AI 领域`, `交叉/综合/新兴`, `ArXiv`, `其他`
- expandable paper cards with abstracts and source links

## Tracked Scope

The project focuses on Text-to-SQL papers from CCF-A software engineering, database, and AI venues/journals, plus arXiv and selected cross-domain venues.

| Category | CCF-A venues / journals |
| --- | --- |
| 软件工程 | ICSE, FSE, ASE, ISSTA, TSE, TOSEM |
| 数据库领域 | SIGMOD, VLDB, ICDE, KDD, SIGIR, TKDE, VLDBJ |
| AI 领域 | AAAI, NeurIPS, ACL, CVPR, ICCV, ICML, IJCAI, AIJ |
| 交叉/综合/新兴 | WWW |
| ArXiv | arXiv Text-to-SQL / NL2SQL / semantic parsing preprints |
| 其他 | Papers that are relevant to Text-to-SQL but do not map to the buckets above |

`ASE` is treated only as **IEEE/ACM International Conference on Automated Software Engineering**.

## Paper Counts

### Counts by Year

| Year | Papers |
| --- | ---: |
| 2020 | 26 |
| 2021 | 22 |
| 2022 | 22 |
| 2023 | 43 |
| 2024 | 46 |
| 2025 | 185 |
| 2026 | 119 |
| **Total** | **463** |

### Counts by Category

| Category | Papers |
| --- | ---: |
| ArXiv | 295 |
| 数据库领域 | 90 |
| AI 领域 | 69 |
| 软件工程 | 7 |
| 交叉/综合/新兴 | 2 |

### Counts by Venue

| Venue | Papers |
| --- | ---: |
| ArXiv | 295 |
| SIGMOD | 35 |
| ACL | 28 |
| AAAI | 27 |
| ICDE | 19 |
| VLDB | 18 |
| KDD | 8 |
| TKDE | 5 |
| SIGIR | 5 |
| NeurIPS | 5 |
| CVPR | 3 |
| IJCAI | 3 |
| ICML | 2 |
| ASE | 2 |
| TOSEM | 2 |
| WWW | 2 |
| ICSE | 1 |
| ISSTA | 1 |
| TSE | 1 |
| ICCV | 1 |

## Official Accepted Sources

Official accepted/proceedings pages are used to supplement DBLP and arXiv. The crawler keeps pages only when the parser can extract clean paper records; pages that parse as navigation, FAQ, or schedule junk are skipped.

Current official accepted candidate coverage:

| Venue | Candidate records |
| --- | ---: |
| NeurIPS | 20,757 |
| ICML | 11,268 |
| IJCAI | 5,540 |
| ACL | 1,700 |
| SIGMOD | 1,481 |
| KDD | 963 |
| WWW | 676 |
| ICSE | 479 |
| ASE | 401 |
| ICDE | 300 |
| SIGIR | 239 |
| FSE | 231 |
| ISSTA | 95 |

Examples of official sources:

- SIGMOD accepted research papers
- IJCAI proceedings pages
- KDD research track papers
- SIGIR accepted full papers
- ICSE/FSE/ASE/ISSTA research tracks on researchr
- ACL main conference papers
- ICML and NeurIPS proceedings
- TheWebConf accepted research tracks

## Taxonomy

Papers are labeled with topic labels and Text-to-SQL pipeline-stage labels. A paper can have multiple labels. `Benchmarks and Evaluation` is intentionally limited to three child labels: `Benchmark`, `Empirical Study`, and `Survey`.

### Top Topic Counts

| Topic Label | Papers |
| --- | ---: |
| Task Setting | 384 |
| Single-turn Text-to-SQL | 381 |
| Benchmarks and Evaluation | 296 |
| Prompting and ICL | 286 |
| Prompt Engineering | 257 |
| Empirical Study | 231 |
| Benchmark | 220 |
| Agentic Feedback and Repair | 146 |
| Pre-training and Fine-tuning | 134 |
| Cross-domain Text-to-SQL | 122 |
| Chain-of-Thought Reasoning | 114 |
| Grounding and Retrieval | 111 |
| Supervised Fine-tuning | 106 |
| Planning and Generation | 91 |
| Agentic Workflow | 66 |

### Top Pipeline Counts

| Pipeline Label | Papers |
| --- | ---: |
| SQL Generation | 397 |
| Grounding | 227 |
| Task Understanding | 121 |
| Query Planning | 120 |
| Context Retrieval | 118 |
| Step-by-step Reasoning | 113 |
| Verification & Repair | 78 |
| Prompt-based Generation | 71 |
| Fine-tuned Generation | 67 |
| Schema Linking | 30 |
| Self-correction | 30 |
| Question Decomposition | 26 |
| Intent Detection | 22 |
| Execution Feedback | 17 |
| Result Validation | 17 |

## Update Pipeline

The main scripts are:

| Step | Script |
| --- | --- |
| Fetch DBLP/arXiv rawdata | `scripts/fetch_rawdata.py` |
| Fetch official accepted pages | `scripts/fetch_official_accepted.py` |
| Enrich missing abstracts | `scripts/enrich_abstracts.py` |
| Extract normalized paper records | `scripts/extract_papers.py` |
| Filter and label Text-to-SQL papers | `scripts/label_papers.py` |
| Merge labeled papers | `scripts/merge_labeldata.py` |
| Validate and audit the dataset | `scripts/validate_dataset.py`, `scripts/audit_literature_sample.py` |
| Build the static site | `scripts/build_site.py` |

Typical local update:

```bash
python scripts/fetch_rawdata.py --from-year 2020 --to-year 2026 --arxiv-max-results 1000 --sleep 0.5
python scripts/fetch_official_accepted.py --from-year 2020 --to-year 2026 --sleep 0.5
python scripts/enrich_abstracts.py data/rawdata --delay 1.0
python scripts/process_folder.py
python scripts/merge_labeldata.py --dedupe-only --prune-irrelevant
python scripts/validate_dataset.py --mode balanced --baseline HEAD:data/labeldata/labeldata.json
python scripts/audit_literature_sample.py
python scripts/build_site.py
```

`data/labeldata/labeldata.json` is the canonical labeled dataset. `web/index.html` is generated from it. `data/autocrawl/openalex.json` is not part of the default production dataset; it can be included only for explicit diagnostics with `scripts/process_folder.py --include-autocrawl`.

## Daily Automation

GitHub Actions runs the update workflow every day at **01:00 Asia/Shanghai**.

The workflow:

1. fetches DBLP/arXiv rawdata
2. fetches official accepted/proceedings pages
3. enriches missing abstracts
4. filters and merges new Text-to-SQL papers
5. validates and audits the dataset
6. rebuilds `web/index.html`
7. commits refreshed data back to the repository
8. deploys the website to GitHub Pages

Manual run:

1. Open the repository **Actions** tab.
2. Select **Build, Crawl, and Deploy Pages**.
3. Click **Run workflow**.
4. Use `full_crawl=true` for a complete refresh.

Optional secret:

```text
SEMANTIC_SCHOLAR_API_KEY
```

## Adding Papers

Add rawdata under `data/rawdata/<year>/`, then run:

```bash
python scripts/process_folder.py
python scripts/build_site.py
```

For one-off manual additions, edit `data/labeldata/labeldata.json` with the fields below:

```json
{
  "Paper Title": {
    "type": "INPROCEEDINGS",
    "author": "Author A and Author B",
    "title": "Paper Title",
    "booktitle": "ACL",
    "year": "2025",
    "abstract": "...",
    "url": "https://...",
    "venue": "ACL",
    "venue_track": "AI 领域",
    "labels": ["Task Setting", "Single-turn Text-to-SQL"],
    "pipeline_stages": ["SQL Generation"]
  }
}
```

Then rebuild the site:

```bash
python scripts/build_site.py
```

## Disclaimer

The dataset is maintained by automated crawlers plus rule-based filtering/classification. It is intended as a research navigation aid, not an authoritative bibliography. Some papers may be missing, duplicated under different metadata, or classified imperfectly.
