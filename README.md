# Text-to-SQL Paper Summary <a href="https://github.com/linli1724647576/Text-to-SQL-Paper-Summary"><img src="https://img.shields.io/github/stars/linli1724647576/Text-to-SQL-Paper-Summary" width="120" height="26" /></a>

A curated paper list and static browser for **Text-to-SQL / NL2SQL / natural-language database querying** research.

This repository follows an ASE-style workflow: crawl raw venue metadata, supplement official accepted-paper pages, filter Text-to-SQL related papers, assign topic and pipeline labels, merge the canonical dataset, and rebuild the website.

Current snapshot:

- **514** classified Text-to-SQL papers
- **124** rawdata files under `data/rawdata/`
- **36** official accepted/proceedings source files
- **41,862** unique official accepted candidates before relevance filtering
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
- strict category buckets: `软件工程`, `数据库领域`, `AI 领域`, `ArXiv`, `其他`
- expandable paper cards with abstracts and source links

## Tracked Scope

The project focuses on Text-to-SQL papers from CCF-A software engineering, database, and AI venues/journals, plus arXiv and other sources.

| Category | CCF-A venues / journals |
| --- | --- |
| 软件工程 | ICSE, FSE, ASE, ISSTA, TSE, TOSEM |
| 数据库领域 | SIGMOD, VLDB, ICDE, KDD, WWW, SIGIR, TKDE, VLDBJ |
| AI 领域 | AAAI, NeurIPS, ACL, CVPR, ICCV, ICML, IJCAI, AIJ |
| ArXiv | arXiv Text-to-SQL / NL2SQL / semantic parsing preprints |
| 其他 | Papers that are relevant to Text-to-SQL but do not map to the buckets above |

`ASE` is treated only as **IEEE/ACM International Conference on Automated Software Engineering**.

## Paper Counts

### Counts by Year

| Year | Papers |
| --- | ---: |
| 2020 | 27 |
| 2021 | 31 |
| 2022 | 35 |
| 2023 | 63 |
| 2024 | 86 |
| 2025 | 171 |
| 2026 | 101 |
| **Total** | **514** |

### Counts by Category

| Category | Papers |
| --- | ---: |
| 软件工程 | 0 |
| 数据库领域 | 46 |
| AI 领域 | 55 |
| ArXiv | 204 |
| 其他 | 209 |

### Counts by Venue

| Venue | Papers |
| --- | ---: |
| 其他 | 209 |
| ArXiv | 204 |
| ACL | 21 |
| SIGMOD | 19 |
| AAAI | 17 |
| VLDB | 10 |
| ICDE | 8 |
| NeurIPS | 8 |
| ICML | 4 |
| IJCAI | 4 |
| KDD | 4 |
| SIGIR | 2 |
| AIJ | 1 |
| VLDBJ | 1 |
| WWW | 1 |
| TKDE | 1 |

## Official Accepted Sources

Official accepted/proceedings pages are used to supplement DBLP and arXiv. The crawler keeps pages only when the parser can extract clean paper records; pages that parse as navigation, FAQ, or schedule junk are skipped.

Current official accepted candidate coverage:

| Venue | Candidate records |
| --- | ---: |
| NeurIPS | 20,757 |
| ICML | 9,001 |
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

Papers are labeled with topic labels and Text-to-SQL pipeline-stage labels. A paper can have multiple labels.

### Top Topic Counts

| Topic Label | Papers |
| --- | ---: |
| Task Setting | 505 |
| Single-turn Text-to-SQL | 447 |
| Benchmarks and Evaluation | 386 |
| Planning and Generation | 381 |
| Intermediate Representation | 365 |
| Enterprise / BI Text-to-SQL | 355 |
| Grounding and Retrieval | 338 |
| Prompting and ICL | 338 |
| Prompt Engineering | 310 |
| Schema / Content Retrieval | 305 |
| Benchmark | 246 |
| Dataset Construction | 203 |
| Agentic Feedback and Repair | 199 |
| Pre-training and Fine-tuning | 192 |
| Cross-domain Text-to-SQL | 153 |

### Top Pipeline Counts

| Pipeline Label | Papers |
| --- | ---: |
| SQL Generation | 481 |
| Grounding | 407 |
| Query Planning | 378 |
| Intermediate Representation | 354 |
| Context Retrieval | 344 |
| Task Understanding | 200 |
| Prompt-based Generation | 127 |
| Verification & Repair | 113 |
| Step-by-step Reasoning | 96 |
| Fine-tuned Generation | 75 |
| Self-correction | 53 |
| Intent Detection | 44 |
| Schema Linking | 41 |
| Domain Constraint Understanding | 37 |
| Question Decomposition | 34 |

## Update Pipeline

The main scripts are:

| Step | Script |
| --- | --- |
| Fetch DBLP/arXiv rawdata | `scripts/fetch_rawdata.py` |
| Fetch official accepted pages | `scripts/fetch_official_accepted.py` |
| Process official accepted pages | `scripts/process_official_accepted.py` |
| Extract normalized paper records | `scripts/extract_papers.py` |
| Filter and label Text-to-SQL papers | `scripts/label_papers.py` |
| Merge labeled papers | `scripts/merge_labeldata.py` |
| Build the static site | `scripts/build_site.py` |

Typical local update:

```bash
python scripts/fetch_rawdata.py --from-year 2020 --to-year 2026 --arxiv-max-results 1000 --sleep 0.5
python scripts/process_folder.py
python scripts/fetch_official_accepted.py --from-year 2020 --to-year 2026 --sleep 0.5
python scripts/process_official_accepted.py
python scripts/build_site.py
```

`data/labeldata/labeldata.json` is the canonical labeled dataset. `web/index.html` is generated from it.

## Daily Automation

GitHub Actions runs the update workflow every day at **01:00 Asia/Shanghai**.

The workflow:

1. fetches DBLP/arXiv rawdata
2. enriches/processes rawdata when needed
3. fetches official accepted/proceedings pages
4. filters and merges new Text-to-SQL papers
5. rebuilds `web/index.html`
6. commits refreshed data back to the repository
7. deploys the website to GitHub Pages

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
