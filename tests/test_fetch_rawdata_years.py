import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from fetch_rawdata import current_year_dblp_conferences, hinted_journal_urls


class FetchRawdataYearsTest(unittest.TestCase):
    def test_current_year_dblp_conferences_uses_supplied_year(self):
        records = current_year_dblp_conferences(2027)

        self.assertIn(("AI", "AAAI", "aaai", 2027), records)
        self.assertIn(("DB", "VLDB", "vldb", 2027), records)

    def test_hinted_journal_urls_does_not_stop_at_2026(self):
        urls = hinted_journal_urls("tse", 2027)

        self.assertEqual(urls, ["https://dblp.org/db/journals/tse/tse53.xml"])


if __name__ == "__main__":
    unittest.main()
