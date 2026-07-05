import os
import sys
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from paper_utils import arxiv_id_from_text, dedupe_papers, normalize_paper_metadata


class PaperIdentityTest(unittest.TestCase):
    def test_dedupe_merges_by_doi_and_prefers_ccf_venue(self):
        papers = {
            "Arxiv title": {
                "title": "Arxiv title",
                "venue": "ArXiv",
                "year": "2025",
                "doi": "https://doi.org/10.1145/example.paper",
                "url": "https://arxiv.org/abs/2501.01234",
            },
            "Accepted title": {
                "title": "Accepted title",
                "venue": "SIGMOD",
                "booktitle": "Proceedings of the ACM on Management of Data",
                "year": "2026",
                "doi": "10.1145/example.paper",
            },
        }

        merged, duplicates = dedupe_papers(papers)

        self.assertEqual(duplicates, 1)
        self.assertEqual(len(merged), 1)
        entry = next(iter(merged.values()))
        self.assertEqual(entry["venue"], "SIGMOD")
        self.assertEqual(entry["doi"], "10.1145/example.paper")

    def test_dedupe_merges_arxiv_url_with_openalex_arxiv_id(self):
        papers = {
            "Preprint": {
                "title": "Text-to-SQL With a Preliminary Title",
                "venue": "ArXiv",
                "year": "2025",
                "url": "https://arxiv.org/abs/2501.01234",
            },
            "Accepted": {
                "title": "Text-to-SQL With a Final Title",
                "venue": "ACL",
                "booktitle": "Annual Meeting of the Association for Computational Linguistics",
                "year": "2026",
                "doi": "10.18653/v1/2026.acl-long.1",
                "arxiv_id": "2501.01234",
            },
        }

        merged, duplicates = dedupe_papers(papers)

        self.assertEqual(duplicates, 1)
        self.assertEqual(len(merged), 1)
        entry = next(iter(merged.values()))
        self.assertEqual(entry["venue"], "ACL")
        self.assertEqual(entry["arxiv_id"], "2501.01234")
        self.assertEqual(entry["doi"], "10.18653/v1/2026.acl-long.1")

    def test_normalize_extracts_arxiv_id_from_url(self):
        entry = normalize_paper_metadata(
            {
                "title": "Example",
                "venue": "ArXiv",
                "url": "https://arxiv.org/pdf/2501.01234v2.pdf",
            }
        )

        self.assertEqual(entry["arxiv_id"], "2501.01234")
        self.assertEqual(arxiv_id_from_text("doi:10.48550/arXiv.2407.12345v3"), "2407.12345")


if __name__ == "__main__":
    unittest.main()
