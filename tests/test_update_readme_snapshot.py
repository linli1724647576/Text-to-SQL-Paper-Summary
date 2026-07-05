import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from update_readme_snapshot import collect_counts, format_count, update_readme_snapshot


class UpdateReadmeSnapshotTest(unittest.TestCase):
    def test_collect_counts_uses_canonical_data_sources(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            labeldata = root / "data" / "labeldata"
            raw_2026 = root / "data" / "rawdata" / "2026"
            raw_2025 = root / "data" / "rawdata" / "2025"
            labeldata.mkdir(parents=True)
            raw_2026.mkdir(parents=True)
            raw_2025.mkdir(parents=True)
            (root / "data" / "rawdata" / ".gitkeep").write_text("", encoding="utf-8")

            (labeldata / "labeldata.json").write_text(
                json.dumps(
                    {
                        "Paper A": {"year": "2025", "booktitle": "SIGMOD"},
                        "Paper B": {"year": "2026", "venue": "ArXiv", "url": "https://arxiv.org/abs/1234.5678"},
                    }
                ),
                encoding="utf-8",
            )
            (raw_2026 / "ACL2026.json").write_text(json.dumps({"A": {}}), encoding="utf-8")
            (raw_2026 / "ACL2026-accepted.json").write_text(
                json.dumps({"Accepted A": {}, "Accepted B": {}}),
                encoding="utf-8",
            )
            (raw_2025 / "SIGMOD2025-accepted.json").write_text(
                json.dumps({"Accepted C": {}}),
                encoding="utf-8",
            )

            counts = collect_counts(root)

        self.assertEqual(counts.classified_papers, 2)
        self.assertEqual(counts.rawdata_files, 3)
        self.assertEqual(counts.official_source_files, 2)
        self.assertEqual(counts.official_candidates, 3)
        self.assertEqual(counts.year_counts, {"2025": 1, "2026": 1})
        self.assertEqual(counts.venue_counts, {"ArXiv": 1, "SIGMOD": 1})

    def test_update_readme_snapshot_rewrites_snapshot_and_count_tables(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            readme = root / "README.md"
            readme.write_text(
                "# Title\n\n"
                "Current snapshot:\n\n"
                "- **1** classified Text-to-SQL papers\n"
                "- **2** rawdata files under `data/rawdata/`\n"
                "- **3** official accepted/proceedings source files\n"
                "- **4** official accepted candidates before relevance filtering\n"
                "- Website: <https://example.test/>\n\n"
                "## Paper Counts\n\n"
                "### Counts by Year\n\n"
                "| Year | Papers |\n"
                "| --- | ---: |\n"
                "| 2024 | 99 |\n"
                "| **Total** | **99** |\n\n\n"
                "### Counts by Venue\n\n"
                "| Venue | Papers |\n"
                "| --- | ---: |\n"
                "| Old | 99 |\n\n"
                "## Next\n",
                encoding="utf-8",
            )

            changed = update_readme_snapshot(
                readme,
                classified_papers=1234,
                rawdata_files=56,
                official_source_files=7,
                official_candidates=89012,
                year_counts={"2025": 2, "2026": 3},
                venue_counts={"ArXiv": 3, "SIGMOD": 2},
            )

            contents = readme.read_text(encoding="utf-8")
            self.assertTrue(changed)
            self.assertIn("- **1,234** classified Text-to-SQL papers", contents)
            self.assertIn("- **89,012** official accepted candidates before relevance filtering", contents)
            self.assertIn("- Website: <https://example.test/>", contents)
            self.assertIn("| 2025 | 2 |", contents)
            self.assertIn("| 2026 | 3 |", contents)
            self.assertIn("| **Total** | **5** |", contents)
            self.assertIn("| ArXiv | 3 |", contents)
            self.assertIn("| SIGMOD | 2 |", contents)
            self.assertNotIn("| Old | 99 |", contents)
            self.assertIn("## Next\n", contents)

    def test_format_count_adds_thousands_separators(self):
        self.assertEqual(format_count(44130), "44,130")


if __name__ == "__main__":
    unittest.main()
