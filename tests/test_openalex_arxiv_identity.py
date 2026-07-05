import os
import sys
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from crawl_papers import normalize_work
from fetch_rawdata import normalize_openalex_work


class OpenAlexArxivIdentityTest(unittest.TestCase):
    def test_crawl_normalize_work_preserves_arxiv_id_from_locations(self):
        work = {
            "id": "https://openalex.org/W1",
            "title": "Example",
            "publication_year": 2026,
            "doi": "https://doi.org/10.1145/example",
            "primary_location": {"source": {"display_name": "Proceedings of the ACM on Management of Data"}},
            "locations": [{"landing_page_url": "https://arxiv.org/abs/2501.01234"}],
        }

        entry = normalize_work(work, venue_override="SIGMOD2026", venue_track="DB")

        self.assertEqual(entry["doi"], "https://doi.org/10.1145/example")
        self.assertEqual(entry["arxiv_id"], "2501.01234")

    def test_rawdata_openalex_fallback_preserves_arxiv_id_from_locations(self):
        work = {
            "id": "https://openalex.org/W1",
            "title": "Example",
            "publication_year": 2026,
            "doi": "https://doi.org/10.1145/example",
            "primary_location": {"source": {"display_name": "Proceedings of the ACM on Management of Data"}},
            "best_oa_location": {"pdf_url": "https://arxiv.org/pdf/2501.01234v2.pdf"},
        }

        entry = normalize_openalex_work(work, "SIGMOD", 2026, "DB")

        self.assertEqual(entry["doi"], "https://doi.org/10.1145/example")
        self.assertEqual(entry["arxiv_id"], "2501.01234")


if __name__ == "__main__":
    unittest.main()
