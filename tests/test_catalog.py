import tempfile
import unittest
from pathlib import Path
from scriptlab.catalog import parse_episode_filename, scan_sources


class CatalogTests(unittest.TestCase):
    def test_filename_patterns(self):
        self.assertEqual(parse_episode_filename("S01E02.txt"), (1, 2))
        self.assertEqual(parse_episode_filename("buffy_2x17.html"), (2, 17))
        self.assertEqual(parse_episode_filename("Season_7_Episode_22.txt"), (7, 22))
        self.assertIsNone(parse_episode_filename("some_random_file.txt"))
        self.assertIsNone(parse_episode_filename("S01E01-S01E02.txt"))

    def test_duplicate_episode_excluded_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "S01E01.txt").write_text("a")
            (root / "S01E01.html").write_text("b")
            episodes, issues = scan_sources([("buffy", str(root))])
            self.assertEqual(episodes, [])
            self.assertTrue(any(i.kind == "duplicate_episode" for i in issues))

    def test_recursive_and_separate_series(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for series in ["buffy", "angel"]:
                folder = root / series / "season1"
                folder.mkdir(parents=True)
                (folder / "S01E01.txt").write_text("hello")
            eps, issues = scan_sources([("buffy", str(root / "buffy")), ("angel", str(root / "angel"))])
            self.assertEqual(len(eps), 2)
            self.assertFalse(issues)

    def test_extension_filter_ignores_other_formats_before_collision_checks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "S01E01.txt").write_text("text script")
            (root / "S01E01.htm").write_text("HTML alternate")
            (root / "corrupt.htm").write_text("unidentified HTML")
            eps, issues = scan_sources([("angel", str(root))], extensions=["txt"])
            self.assertEqual([ep.path.name for ep in eps], ["S01E01.txt"])
            self.assertFalse(issues)
