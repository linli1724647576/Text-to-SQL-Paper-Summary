"""Tracked venue configuration matching the ASE survey coverage style."""

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


VENUE_ALIASES = {
    "acl": "ACL",
    "annual meeting of the association for computational linguistics": "ACL",
    "findings of the association for computational linguistics": "ACL",
    "emnlp": "EMNLP",
    "empirical methods in natural language processing": "EMNLP",
    "naacl": "NAACL",
    "north american chapter of the association for computational linguistics": "NAACL",
    "icml": "ICML",
    "international conference on machine learning": "ICML",
    "aaai": "AAAI",
    "aaai conference on artificial intelligence": "AAAI",
    "ijcai": "IJCAI",
    "international joint conference on artificial intelligence": "IJCAI",
    "cvpr": "CVPR",
    "computer vision and pattern recognition": "CVPR",
    "iccv": "ICCV",
    "international conference on computer vision": "ICCV",
    "neurips": "NeurIPS",
    "nips": "NeurIPS",
    "neural information processing systems": "NeurIPS",
    "iclr": "ICLR",
    "international conference on learning representations": "ICLR",
    "openreview.net": "ICLR",
    "icse": "ICSE",
    "international conference on software engineering": "ICSE",
    "fse": "FSE",
    "foundations of software engineering": "FSE",
    "joint meeting on european software engineering conference and symposium on the foundations of software engineering": "FSE",
    "ase": "ASE",
    "automated software engineering": "ASE",
    "issta": "ISSTA",
    "international symposium on software testing and analysis": "ISSTA",
    "tse": "TSE",
    "ieee transactions on software engineering": "TSE",
    "tosem": "TOSEM",
    "acm transactions on software engineering and methodology": "TOSEM",
    "sigmod": "SIGMOD",
    "international conference on management of data": "SIGMOD",
    "vldb": "VLDB",
    "very large data bases": "VLDB",
    "icde": "ICDE",
    "international conference on data engineering": "ICDE",
    "kdd": "KDD",
    "knowledge discovery and data mining": "KDD",
    "www": "WWW",
    "web conference": "WWW",
    "sigir": "SIGIR",
    "research and development in information retrieval": "SIGIR",
    "pldi": "PLDI",
    "programming language design and implementation": "PLDI",
    "oopsla": "OOPSLA",
    "popl": "POPL",
    "principles of programming languages": "POPL",
    "ccs": "CCS",
    "computer and communications security": "CCS",
    "conference on computer and communications security": "CCS",
    "usenix security": "USENIXSec",
    "s&p": "S&P",
    "security and privacy": "S&P",
    "ndss": "NDSS",
    "network and distributed system security": "NDSS",
}


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


def normalize_venue_name(raw_venue, title="", year=""):
    haystack = f"{raw_venue} {title}".lower()
    for alias, abbr in sorted(VENUE_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if alias in haystack:
            return f"{abbr}{year}" if year else abbr
    compact = (raw_venue or "Unknown").strip()
    compact = compact.strip()
    if year:
        compact = compact.replace(str(year), "").strip(" -_")
    if not compact:
        compact = "Unknown"
    return f"{compact} {year}".strip()


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
