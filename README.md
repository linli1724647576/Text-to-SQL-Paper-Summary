# Text-to-SQL Paper Summary <a href="https://github.com/linli1724647576/Text-to-SQL-Paper-Summary"><img src="https://img.shields.io/github/stars/linli1724647576/Text-to-SQL-Paper-Summary" width="120" height="26" /></a>

A curated paper list and static browser for **Text-to-SQL / NL2SQL / natural-language database querying** research.

This repository follows an ASE-style workflow: crawl DBLP/arXiv raw metadata, fetch official accepted-paper pages, enrich missing abstracts, filter Text-to-SQL related papers, assign topic and pipeline labels, merge the canonical dataset, and rebuild the website.

Current snapshot:

- **588** classified Text-to-SQL papers
- **182** rawdata files under `data/rawdata/`
- **43** official accepted/proceedings source files
- **56,574** official accepted candidates before relevance filtering
- Website: <https://linli1724647576.github.io/Text-to-SQL-Paper-Summary/>

## Table of Contents

- [Text-to-SQL Paper Summary ](#text-to-sql-paper-summary-)
  - [Table of Contents](#table-of-contents)
  - [Website](#website)
  - [Paper Counts](#paper-counts)
    - [Counts by Year](#counts-by-year)
    - [Counts by Venue](#counts-by-venue)
  - [Official Accepted Sources](#official-accepted-sources)
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
- strict venue buckets: CCF-A venue/journal name, `ArXiv`, or `Other`
- strict category buckets: `Software Engineering`, `Databases`, `AI`, `Interdisciplinary/General/Emerging`, `ArXiv`, `Other`
- expandable paper cards with abstracts and source links


## Paper Counts

### Counts by Year

| Year | Papers |
| --- | ---: |
| 2020 | 25 |
| 2021 | 22 |
| 2022 | 20 |
| 2023 | 51 |
| 2024 | 47 |
| 2025 | 191 |
| 2026 | 232 |
| **Total** | **588** |


### Counts by Venue

| Venue | Papers |
| --- | ---: |
| ArXiv | 373 |
| SIGMOD | 37 |
| AAAI | 35 |
| ACL | 33 |
| ICDE | 26 |
| VLDB | 19 |
| NeurIPS | 11 |
| ICML | 9 |
| KDD | 8 |
| TKDE | 8 |
| SIGIR | 5 |
| VLDBJ | 5 |
| IJCAI | 4 |
| CVPR | 3 |
| TOSEM | 3 |
| ASE | 2 |
| WWW | 2 |
| FSE | 1 |
| ICCV | 1 |
| ICSE | 1 |
| ISSTA | 1 |
| TSE | 1 |

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
| Update README snapshot counts | `scripts/update_readme_snapshot.py` |
| Build the static site | `scripts/build_site.py` |

Typical local update:

```bash
CURRENT_YEAR="$(date -u +%Y)"
python scripts/fetch_rawdata.py --from-year 2020 --to-year "${CURRENT_YEAR}" --arxiv-max-results 1000 --sleep 0.5
python scripts/fetch_official_accepted.py --from-year 2020 --to-year "${CURRENT_YEAR}" --sleep 0.5
python scripts/enrich_abstracts.py data/rawdata --delay 1.0
python scripts/process_folder.py
python scripts/merge_labeldata.py --dedupe-only --prune-irrelevant
python scripts/validate_dataset.py --mode balanced --baseline HEAD:data/labeldata/labeldata.json
python scripts/audit_literature_sample.py
python scripts/update_readme_snapshot.py
python scripts/build_site.py
```

`data/labeldata/labeldata.json` is the canonical labeled dataset. `web/index.html` is generated from it. `data/autocrawl/openalex.json` is not part of the default production dataset; it can be included only for explicit diagnostics with `scripts/process_folder.py --include-autocrawl`.

## Daily Automation

GitHub Actions runs the update workflow every day at **01:00 Asia/Shanghai**.

The workflow:

1. selects one crawl year between 2020 and the current UTC year
2. fetches selected-year DBLP/OpenAlex rawdata
3. fetches selected-year official accepted/proceedings pages
4. enriches missing abstracts
5. filters and merges new Text-to-SQL papers
6. validates and audits the dataset
7. updates the `Current snapshot` counts in `README.md`
8. rebuilds `web/index.html`
9. commits refreshed data back to the repository
10. deploys the website to GitHub Pages

Manual run:

1. Open the repository **Actions** tab.
2. Select **Build, Crawl, and Deploy Pages**.
3. Click **Run workflow**.
4. Use `full_crawl=true` for a complete refresh, including arXiv.

Optional secret:

```text
OPENALEX_API_KEY
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
    "venue_track": "AI",
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
