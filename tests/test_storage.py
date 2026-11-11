import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from scriptlab.models import EpisodeFile
from scriptlab.parser import parse_document
from scriptlab.readers import read_episode
from scriptlab.storage import save_parsed
from scriptlab.validator import validate_parsed


class StorageTests(unittest.TestCase):
    def test_save_and_reprocess_same_file(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "S01E01.txt"
            source.write_text("BUFFY: Hello.\n")
            doc = read_episode(EpisodeFile("buffy", 1, 1, source))
            parsed = parse_document(doc)
            parsed["issues"].extend(validate_parsed(parsed))
            db = root / "scriptlab.sqlite"
            save_parsed(db, parsed)
            save_parsed(db, parsed)
            with closing(sqlite3.connect(db)) as conn, conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0], 1)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM elements").fetchone()[0], 1)
                self.assertEqual(conn.execute("SELECT raw_text FROM script_lines").fetchone()[0], "BUFFY: Hello.")

    def test_block_same_episode_different_file(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db = root / "db.sqlite"
            for name in ("one", "two"):
                folder = root / name
                folder.mkdir()
                source = folder / "S01E01.txt"
                source.write_text("BUFFY: Hello.\n")
                parsed = parse_document(read_episode(EpisodeFile("buffy", 1, 1, source)))
                if name == "one":
                    save_parsed(db, parsed)
                else:
                    with self.assertRaises(ValueError):
                        save_parsed(db, parsed)
