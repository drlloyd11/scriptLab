"""Tiny invented fixtures matching tricky structures found in Buffy S05E11.

No copyrighted episode text is redistributed with the source package.
"""
from __future__ import annotations

import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from scriptlab.models import EpisodeFile
from scriptlab.parser import parse_document
from scriptlab.readers import read_episode
from scriptlab.validator import validate_parsed


TRICKY_HTML = """<html><head><title>Example</title></head><body>
<center><table width="85%"><tr><td><p>Act One
<p>INT. CAR - DAY
<center><font>ANYA<br>I drove all this way.<br><br>WILLOW<br>I noticed.</font></center>
<p>Willow looks out the window.
<center><font>WILLOW<br>Is this the correct road?</font></center>
<p>INT. STORE - DAY
<center><font>BUFFY (V.0.)<br>Where did everybody go?</font></center>
<center><font>BUFFY (V.O.)<br>I'm still here.</font></center>
<center>END OF ACT ONE</center>
</td></tr></table></center></body></html>"""


class TriangleRegressionTests(unittest.TestCase):
    def parse(self, html=TRICKY_HTML):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "5x11.htm"
            file.write_text(html, encoding="utf-8")
            return parse_document(read_episode(EpisodeFile("buffy", 5, 11, file)))

    def test_double_br_separates_speaker_within_same_center_block(self):
        parsed = self.parse()
        turns = parsed["dialogue_turns"]
        self.assertEqual([turn["speaker"] for turn in turns[:3]], ["ANYA", "WILLOW", "WILLOW"])
        self.assertEqual(turns[0]["text"], "I drove all this way.")
        self.assertEqual(turns[1]["text"], "I noticed.")
        self.assertEqual(turns[2]["text"], "Is this the correct road?")
        cues = [e for e in parsed["elements"] if e["kind"] == "character_cue"]
        self.assertTrue(any(e["text"] == "WILLOW" and
                            "consecutive <BR>" in " ".join(e["evidence"])
                            for e in cues))
        willow_cue = next(e for e in cues if e["text"] == "WILLOW")
        willow_source = next(line for line in parsed["lines"] if line["line"] == willow_cue["line"])
        self.assertEqual(willow_source["br_run_before"], 2)
        self.assertFalse(validate_parsed(parsed))

    def test_v_zero_typo_is_recognized_as_voiceover_cue(self):
        parsed = self.parse()
        turns = parsed["dialogue_turns"]
        self.assertEqual([(t["speaker"], t["cue"]) for t in turns[-2:]],
                         [("BUFFY", "BUFFY (V.0.)"), ("BUFFY", "BUFFY (V.O.)")])
        self.assertFalse([e for e in parsed["elements"] if e["kind"] == "unknown"])
        self.assertFalse(validate_parsed(parsed))

    def test_double_br_followed_by_unknown_caps_is_not_automatically_a_speaker(self):
        html = TRICKY_HTML.replace("<br><br>WILLOW<br>I noticed.",
                                  "<br><br>IMPORTANT<br>I noticed.")
        parsed = self.parse(html)
        self.assertFalse([e for e in parsed["elements"] if e["kind"] == "character_cue"
                          and e["text"] == "IMPORTANT"])
        self.assertFalse(validate_parsed(parsed))


if __name__ == "__main__":
    unittest.main()

class StorageAndComparisonTests(unittest.TestCase):
    def test_html_boundary_provenance_survives_database_write(self):
        import sqlite3
        from scriptlab.storage import save_parsed
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / '5x11.htm'
            file.write_text(TRICKY_HTML, encoding='utf-8')
            parsed = parse_document(read_episode(EpisodeFile('buffy', 5, 11, file)))
            db = Path(tmp) / 'test.sqlite'
            save_parsed(db, parsed)
            with closing(sqlite3.connect(db)) as conn, conn:
                rows = conn.execute('SELECT raw_text, br_run_before FROM script_lines WHERE raw_text=?',
                                    ('WILLOW',)).fetchall()
            self.assertIn(('WILLOW', 2), rows)

    def test_comparator_is_told_about_double_breaks(self):
        from scriptlab.comparator import independent_llm_labels
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / '5x11.htm'
            file.write_text(TRICKY_HTML, encoding='utf-8')
            parsed = parse_document(read_episode(EpisodeFile('buffy', 5, 11, file)))
        def fake(system, user, model, base_url):
            self.assertIn('br_run_before=2 | WILLOW', user)
            self.assertIn('two consecutive BR tags', system)
            return {"labels": [{"line": l["line"], "kind": "unknown", "speaker": None}
                               for l in parsed["lines"]]}
        labels, failures = independent_llm_labels(parsed, 'fake', ask=fake)
        self.assertEqual(len(labels), len(parsed['lines']))
        self.assertFalse(failures)
