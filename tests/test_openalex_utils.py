import os
import sys
import unittest
from unittest.mock import patch


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from openalex_utils import abstract_from_inverted_index, openalex_url, sanitize_openalex_url
import openalex_utils


class OpenAlexUtilsTest(unittest.TestCase):
    def test_openalex_url_adds_api_key_from_environment(self):
        with patch.dict(os.environ, {"OPENALEX_API_KEY": "secret-value"}):
            url = openalex_url("https://api.openalex.org/works", {"filter": "doi:10.123/a"})

        self.assertIn("filter=doi%3A10.123%2Fa", url)
        self.assertIn("api_key=secret-value", url)

    def test_sanitize_openalex_url_removes_api_key(self):
        url = "https://api.openalex.org/works?filter=x&api_key=secret-value&per-page=100"

        sanitized = sanitize_openalex_url(url)

        self.assertEqual(sanitized, "https://api.openalex.org/works?filter=x&api_key=REDACTED&per-page=100")

    def test_abstract_from_inverted_index_restores_word_order(self):
        abstract = abstract_from_inverted_index({"world": [1], "hello": [0], "again": [2]})

        self.assertEqual(abstract, "hello world again")

    def test_get_openalex_json_redacts_api_key_in_errors(self):
        with patch.dict(os.environ, {"OPENALEX_API_KEY": "secret-value"}):
            with patch.object(openalex_utils, "get_json", side_effect=RuntimeError("boom")):
                with self.assertRaises(RuntimeError) as context:
                    openalex_utils.get_openalex_json("https://api.openalex.org/works", {"filter": "x"})

        message = str(context.exception)
        self.assertIn("api_key=REDACTED", message)
        self.assertNotIn("secret-value", message)


if __name__ == "__main__":
    unittest.main()
