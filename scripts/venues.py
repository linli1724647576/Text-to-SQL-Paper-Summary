"""Tracked venue configuration matching the ASE survey coverage style."""

import re

TRACKED_VENUES = {
    "Software Engineering": {
        "ICSE": {
            "years": [2023, 2024, 2025],
            "queries": ["ICSE", "International Conference on Software Engineering"],
        },
        "FSE": {
            "years": [2023, 2024, 2025],
            "queries": ["FSE", "Foundations of Software Engineering"],
        },
        "ASE": {
            "years": [2023, 2024, 2025],
            "queries": ["ASE", "Automated Software Engineering"],
        },
        "ISSTA": {
            "years": [2022, 2023, 2024, 2025],
            "queries": ["ISSTA", "International Symposium on Software Testing and Analysis"],
        },
        "TSE": {
            "years": [2023, 2024],
            "queries": ["IEEE Transactions on Software Engineering", "TSE"],
        },
        "TOSEM": {
            "years": [2023, 2024],
            "queries": ["ACM Transactions on Software Engineering and Methodology", "TOSEM"],
        },
    },
    "Programming Languages": {
        "PLDI": {
            "years": [2023, 2025],
            "queries": ["PLDI", "Programming Language Design and Implementation"],
        },
        "OOPSLA": {
            "years": [2023, 2024, 2025],
            "queries": ["OOPSLA", "Object-Oriented Programming Systems Languages and Applications"],
        },
        "POPL": {
            "years": [2025],
            "queries": ["POPL", "Principles of Programming Languages"],
        },
        "CC": {
            "years": [2025],
            "queries": ["International Conference on Compiler Construction", "CC"],
        },
        "COLM": {
            "years": [2025],
            "queries": ["COLM", "Conference on Language Modeling"],
        },
    },
    "Security": {
        "S&P": {
            "years": [2023, 2024, 2025],
            "queries": ["IEEE Symposium on Security and Privacy", "Oakland security privacy"],
        },
        "USENIXSec": {
            "years": [2023, 2024, 2025],
            "queries": ["USENIX Security Symposium", "USENIX Security"],
        },
        "CCS": {
            "years": [2023, 2024, 2025],
            "queries": ["ACM Conference on Computer and Communications Security", "CCS"],
        },
        "NDSS": {
            "years": [2024, 2025, 2026],
            "queries": ["Network and Distributed System Security Symposium", "NDSS"],
        },
        "RAID": {
            "years": [2023],
            "queries": ["Research in Attacks Intrusions and Defenses", "RAID"],
        },
    },
    "Natural Language Processing": {
        "ACL": {
            "years": [2020, 2023, 2024, 2025],
            "queries": ["ACL", "Annual Meeting of the Association for Computational Linguistics"],
        },
        "EMNLP": {
            "years": [2020, 2023, 2024, 2025],
            "queries": ["EMNLP", "Empirical Methods in Natural Language Processing"],
        },
        "NAACL": {
            "years": [2024, 2025],
            "queries": ["NAACL", "North American Chapter of the Association for Computational Linguistics"],
        },
    },
    "Machine Learning": {
        "ICML": {
            "years": [2021, 2023, 2024, 2025],
            "queries": ["ICML", "International Conference on Machine Learning"],
        },
        "NeurIPS": {
            "years": [2022, 2023, 2024],
            "queries": ["NeurIPS", "Neural Information Processing Systems"],
        },
        "ICLR": {
            "years": [2021, 2023, 2024, 2025],
            "queries": ["ICLR", "International Conference on Learning Representations"],
        },
    },
}


CCF_A_VENUES = {
    "AI": {
        "AAAI": {"dblp": "aaai", "years": [2020, 2021, 2022, 2023, 2024, 2025]},
        "NeurIPS": {"dblp": "nips", "years": [2020, 2021, 2022, 2023, 2024, 2025]},
        "ACL": {"dblp": "acl", "years": [2020, 2021, 2022, 2023, 2024, 2025]},
        "CVPR": {"dblp": "cvpr", "years": [2020, 2021, 2022, 2023, 2024, 2025]},
        "ICCV": {"dblp": "iccv", "years": [2021, 2023, 2025]},
        "ICML": {"dblp": "icml", "years": [2020, 2021, 2022, 2023, 2024, 2025]},
        "IJCAI": {"dblp": "ijcai", "years": [2020, 2021, 2022, 2023, 2024, 2025]},
    },
    "DB": {
        "SIGMOD": {"dblp": "sigmod", "years": [2020, 2021, 2022, 2023, 2024, 2025]},
        "VLDB": {"dblp": "vldb", "years": [2020, 2021, 2022, 2023, 2024, 2025]},
        "ICDE": {"dblp": "icde", "years": [2020, 2021, 2022, 2023, 2024, 2025]},
        "KDD": {"dblp": "kdd", "years": [2020, 2021, 2022, 2023, 2024, 2025]},
        "WWW": {"dblp": "www", "years": [2020, 2021, 2022, 2023, 2024, 2025]},
        "SIGIR": {"dblp": "sigir", "years": [2020, 2021, 2022, 2023, 2024, 2025]},
    },
    "SE": {
        "ICSE": {"dblp": "icse", "years": [2020, 2021, 2022, 2023, 2024, 2025]},
        "FSE": {"dblp": "sigsoft", "years": [2020, 2021, 2022, 2023, 2024, 2025]},
        "ASE": {"dblp": "kbse", "years": [2020, 2021, 2022, 2023, 2024, 2025]},
        "ISSTA": {"dblp": "issta", "years": [2020, 2021, 2022, 2023, 2024, 2025]},
    },
    "Security": {
        "CCS": {"dblp": "ccs", "years": [2020, 2021, 2022, 2023, 2024, 2025]},
        "S&P": {"dblp": "sp", "years": [2020, 2021, 2022, 2023, 2024, 2025]},
        "USENIXSec": {"dblp": "uss", "years": [2020, 2021, 2022, 2023, 2024, 2025]},
        "NDSS": {"dblp": "ndss", "years": [2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    },
}

README_CCF_A_JOURNALS = {
    "AI": {
        "AIJ": {
            "dblp": "ai",
            "queries": ["Artificial Intelligence", "Artificial Intelligence Journal"],
        },
    },
    "DB": {
        "TKDE": {
            "dblp": "tkde",
            "queries": ["IEEE Transactions on Knowledge and Data Engineering", "TKDE"],
        },
        "VLDBJ": {
            "dblp": "vldb",
            "queries": ["VLDB Journal", "The VLDB Journal"],
        },
    },
    "SE": {
        "TSE": {
            "dblp": "tse",
            "queries": ["IEEE Transactions on Software Engineering", "TSE"],
        },
        "TOSEM": {
            "dblp": "tosem",
            "queries": ["ACM Transactions on Software Engineering and Methodology", "TOSEM"],
        },
    },
}


AI_CCF_A_VENUES = {
    "AAAI",
    "ACL",
    "AIJ",
    "CVPR",
    "ICCV",
    "ICML",
    "IJCV",
    "IJCAI",
    "JMLR",
    "NeurIPS",
    "TPAMI",
}

DATABASE_CCF_A_VENUES = {
    "ICDE",
    "KDD",
    "PODS",
    "SIGIR",
    "SIGMOD",
    "TKDE",
    "TODS",
    "TOIS",
    "VLDB",
    "VLDBJ",
}

SE_CCF_A_VENUES = {
    "ASE",
    "FSE",
    "ICSE",
    "ISSTA",
    "TOSEM",
    "TSE",
}

CROSS_CCF_A_VENUES = {
    "WWW",
}

PUBLICATION_CATEGORIES = [
    "软件工程",
    "数据库领域",
    "AI 领域",
    "ArXiv",
    "交叉/综合/新兴",
    "其他",
]

OTHER_VENUE = "其他"
ARXIV_VENUE = "ArXiv"

ALL_CCF_A_VENUES = AI_CCF_A_VENUES | DATABASE_CCF_A_VENUES | SE_CCF_A_VENUES | CROSS_CCF_A_VENUES

VENUE_ALIASES = {
    "aaai": "AAAI",
    "aaai conference on artificial intelligence": "AAAI",
    "acl": "ACL",
    "annual meeting of the association for computational linguistics": "ACL",
    "aij": "AIJ",
    "artificial intelligence": "AIJ",
    "artificial intelligence journal": "AIJ",
    "computer vision and pattern recognition": "CVPR",
    "cvpr": "CVPR",
    "iccv": "ICCV",
    "international conference on computer vision": "ICCV",
    "icml": "ICML",
    "international conference on machine learning": "ICML",
    "ijcai": "IJCAI",
    "international joint conference on artificial intelligence": "IJCAI",
    "international journal of computer vision": "IJCV",
    "journal of machine learning research": "JMLR",
    "neurips": "NeurIPS",
    "neural information processing systems": "NeurIPS",
    "nips": "NeurIPS",
    "transactions on pattern analysis and machine intelligence": "TPAMI",
    "tpami": "TPAMI",
    "acm sigmod": "SIGMOD",
    "international conference on management of data": "SIGMOD",
    "pacmmod": "SIGMOD",
    "proceedings of the acm on management of data": "SIGMOD",
    "sigmod": "SIGMOD",
    "acm transactions on database systems": "TODS",
    "tods": "TODS",
    "acm transactions on information systems": "TOIS",
    "tois": "TOIS",
    "ieee transactions on knowledge and data engineering": "TKDE",
    "tkde": "TKDE",
    "icde": "ICDE",
    "international conference on data engineering": "ICDE",
    "kdd": "KDD",
    "knowledge discovery and data mining": "KDD",
    "pods": "PODS",
    "principles of database systems": "PODS",
    "sigir": "SIGIR",
    "research and development in information retrieval": "SIGIR",
    "the web conference": "WWW",
    "web conference": "WWW",
    "www": "WWW",
    "www conference": "WWW",
    "world wide web conference": "WWW",
    "thewebconf": "WWW",
    "vldb": "VLDB",
    "very large data bases": "VLDB",
    "proceedings of the vldb endowment": "VLDB",
    "vldb journal": "VLDBJ",
    "vldbj": "VLDBJ",
    "ieee/acm international conference on automated software engineering": "ASE",
    "ieee / acm international conference on automated software engineering": "ASE",
    "international conference on automated software engineering": "ASE",
    "automated software engineering": "ASE",
    "ase": "ASE",
    "joint meeting on european software engineering conference and symposium on the foundations of software engineering": "FSE",
    "foundations of software engineering": "FSE",
    "fse": "FSE",
    "icse": "ICSE",
    "international conference on software engineering": "ICSE",
    "international symposium on software testing and analysis": "ISSTA",
    "issta": "ISSTA",
    "acm transactions on software engineering and methodology": "TOSEM",
    "tosem": "TOSEM",
    "ieee transactions on software engineering": "TSE",
    "tse": "TSE",
}


def _contains_alias(haystack, alias):
    if len(alias) <= 4 and re.fullmatch(r"[a-z&]+", alias):
        pattern = rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])"
        return re.search(pattern, haystack) is not None
    return alias in haystack


def venue_base_name(venue):
    compact = (venue or "").strip()
    if "arxiv" in compact.lower():
        return ARXIV_VENUE
    compact = re.sub(r"\s*20\d{2}$", "", compact)
    compact = re.sub(r"20\d{2}$", "", compact)
    compact = re.sub(r"[-_ ]?(main|findings|short|long|demo|industry)$", "", compact, flags=re.I)
    compact = compact.strip(" -_")
    if compact in ALL_CCF_A_VENUES:
        return compact
    if compact == ARXIV_VENUE:
        return ARXIV_VENUE
    return OTHER_VENUE


def iter_tracked_venues(from_year=None, to_year=None):
    for track, venues in TRACKED_VENUES.items():
        for abbr, spec in venues.items():
            for year in spec["years"]:
                if from_year is not None and year < from_year:
                    continue
                if to_year is not None and year > to_year:
                    continue
                yield track, abbr, year, spec["queries"]


def iter_ccf_a_venues(from_year=None, to_year=None, tracks=None):
    allowed_tracks = {track.lower() for track in tracks} if tracks else None
    for track, venues in CCF_A_VENUES.items():
        if allowed_tracks and track.lower() not in allowed_tracks:
            continue
        for abbr, spec in venues.items():
            for year in spec["years"]:
                if from_year is not None and year < from_year:
                    continue
                if to_year is not None and year > to_year:
                    continue
                yield track, abbr, spec["dblp"], year


def iter_readme_journals(from_year=None, to_year=None, tracks=None):
    allowed_tracks = {track.lower() for track in tracks} if tracks else None
    start = from_year if from_year is not None else 2020
    end = to_year if to_year is not None else start
    for track, venues in README_CCF_A_JOURNALS.items():
        if allowed_tracks and track.lower() not in allowed_tracks:
            continue
        for abbr, spec in venues.items():
            for year in range(start, end + 1):
                yield track, abbr, spec["dblp"], year


def normalize_venue_name(raw_venue, title="", year=""):
    haystack = (raw_venue or "").lower()
    if "arxiv" in haystack:
        return f"{ARXIV_VENUE}{year}" if year else ARXIV_VENUE
    for alias, abbr in sorted(VENUE_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if _contains_alias(haystack, alias):
            return f"{abbr}{year}" if year else abbr
    return OTHER_VENUE


def publication_category(entry):
    """Classify papers into the publication buckets used by the website."""
    venue = normalize_entry_venue(entry)
    if venue == ARXIV_VENUE:
        return "ArXiv"
    base = venue_base_name(venue)
    if base in SE_CCF_A_VENUES:
        return "软件工程"
    if base in DATABASE_CCF_A_VENUES:
        return "数据库领域"
    if base in AI_CCF_A_VENUES:
        return "AI 领域"
    if base in CROSS_CCF_A_VENUES:
        return "交叉/综合/新兴"
    return "其他"


def _venue_source_text(entry):
    # Do not trust the existing "venue" field here: older runs may already have
    # written a wrong bucket such as ASE. Use source-like fields instead.
    return " ".join(
        str(entry.get(key, ""))
        for key in ("booktitle", "journal", "container", "source", "publisher", "url", "doi")
    ).lower()


def normalize_entry_venue(entry):
    """Return a strict CCF-A venue bucket, ArXiv, or Other."""
    source_text = _venue_source_text(entry)
    if "arxiv" in source_text:
        return ARXIV_VENUE
    for alias, abbr in sorted(VENUE_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if _contains_alias(source_text, alias):
            return abbr
    existing = venue_base_name(entry.get("venue", ""))
    if existing != OTHER_VENUE:
        return existing
    return OTHER_VENUE


def canonical_venue_from_filename(path):
    """Derive ASE-style venue keys from rawdata filenames.

    Examples:
        ACL2024.html -> ACL2024
        EMNLP-main2025.html -> EMNLP2025
        S&P2024.bib -> S&P2024
    """
    import re
    from pathlib import Path

    name = Path(path).name
    name = re.sub(r"\.(bib|json|csv|html|htm)$", "", name, flags=re.I)
    name = re.sub(r"[-_]?(main|findings|short|long|demo|srw|industry)", "", name, flags=re.I)
    name = re.sub(r"[-_]+(20\d{2})", r"\1", name)
    year_match = re.search(r"(20\d{2})", name)
    year = year_match.group(1) if year_match else ""
    prefix = re.sub(r"20\d{2}.*$", "", name).strip("-_ ")
    normalized = normalize_venue_name(prefix, year=year)
    normalized = normalized.replace(" ", "")
    return normalized
