import os
import sys
import unittest
from unittest.mock import patch


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import enrich_abstracts


class EnrichOpenAlexTest(unittest.TestCase):
    def test_batch_by_doi_enriches_from_openalex_results(self):
        entry = {"title": "Example", "doi": "10.1234/example"}
        payload = {
            "results": [
                {
                    "doi": "https://doi.org/10.1234/example",
                    "abstract_inverted_index": {"hello": [0], "world": [1]},
                    "id": "https://openalex.org/W1",
                    "primary_location": {"landing_page_url": "https://example.test/paper"},
                }
            ]
        }

        with patch.object(enrich_abstracts, "get_openalex_json", return_value=payload):
            updated = enrich_abstracts.batch_by_doi([("Example", entry)])

        self.assertEqual(updated, 1)
        self.assertEqual(entry["abstract"], "hello world")
        self.assertEqual(entry["openalex_id"], "https://openalex.org/W1")
        self.assertEqual(entry["url"], "https://example.test/paper")

    def test_search_title_uses_openalex_abstract(self):
        payload = {
            "results": [
                {
                    "title": "Example",
                    "abstract_inverted_index": {"openalex": [0], "abstract": [1]},
                }
            ]
        }

        with patch.object(enrich_abstracts, "get_openalex_json", return_value=payload):
            abstract = enrich_abstracts.search_title("Example")

        self.assertEqual(abstract, "openalex abstract")


if __name__ == "__main__":
    unittest.main()
