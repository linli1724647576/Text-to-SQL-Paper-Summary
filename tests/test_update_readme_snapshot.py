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
                json.dumps({"Paper A": {}, "Paper B": {}}),
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

    def test_update_readme_snapshot_rewrites_only_snapshot_block(self):
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
                "## Next\n",
                encoding="utf-8",
            )

            changed = update_readme_snapshot(
                readme,
                classified_papers=1234,
                rawdata_files=56,
                official_source_files=7,
                official_candidates=89012,
            )

            self.assertTrue(changed)
            self.assertIn("- **1,234** classified Text-to-SQL papers", readme.read_text(encoding="utf-8"))
            self.assertIn("- **89,012** official accepted candidates before relevance filtering", readme.read_text(encoding="utf-8"))
            self.assertIn("- Website: <https://example.test/>", readme.read_text(encoding="utf-8"))
            self.assertIn("## Next\n", readme.read_text(encoding="utf-8"))

    def test_format_count_adds_thousands_separators(self):
        self.assertEqual(format_count(44130), "44,130")


if __name__ == "__main__":
    unittest.main()
