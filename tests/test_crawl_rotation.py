import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from crawl_rotation import select_year_batch, year_venue_manifest


class CrawlRotationTest(unittest.TestCase):
    def test_select_year_batch_rotates_one_year_at_a_time(self):
        state = {"year_rotation": {"cursor": 1}}

        selection = select_year_batch(state, 2020, 2022, "AI,DB,SE")

        self.assertEqual(selection["year"], 2021)
        self.assertEqual(selection["cursor_before"], 1)
        self.assertEqual(selection["cursor_after"], 2)
        self.assertIn("AAAI", selection["venues"])
        self.assertIn("SIGMOD", selection["venues"])
        self.assertIn("TOSEM", selection["venues"])

    def test_select_year_batch_wraps_cursor(self):
        state = {"year_rotation": {"cursor": 2}}

        selection = select_year_batch(state, 2020, 2021, "AI,DB,SE")

        self.assertEqual(selection["year"], 2020)
        self.assertEqual(selection["cursor_before"], 0)
        self.assertEqual(selection["cursor_after"], 1)

    def test_year_venue_manifest_uses_year_specific_venues(self):
        venues_2020 = year_venue_manifest(2020, "AI,DB,SE")
        venues_2021 = year_venue_manifest(2021, "AI,DB,SE")

        self.assertNotIn("ICCV", venues_2020)
        self.assertIn("ICCV", venues_2021)


if __name__ == "__main__":
    unittest.main()
