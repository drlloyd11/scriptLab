import hashlib
import tempfile
import unittest
from pathlib import Path
from scriptlab.models import EpisodeFile
from scriptlab.parser import parse_document
from scriptlab.readers import read_episode
from scriptlab.validator import validate_parsed


SCRIPT = """INT. LIBRARY - NIGHT

Giles examines the book.

                 BUFFY
        Are you listening?

                 GILES
           (dryly)
        Of course.

Buffy drops the book.
"""


class ParserTests(unittest.TestCase):
    def parse(self, text: str, ext="txt") -> dict:
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / f"S01E01.{ext}"
            p.write_text(text, encoding="utf-8")
            ep = EpisodeFile("buffy", 1, 1, p)
            return parse_document(read_episode(ep))

    def test_screenplay_dialogue_and_parenthetical(self):
        parsed = self.parse(SCRIPT)
        by_line = {e["line"]: e for e in parsed["elements"]}
        self.assertEqual(by_line[1]["kind"], "scene_heading")
        self.assertEqual((by_line[5]["kind"], by_line[6]["speaker"]), ("character_cue", "BUFFY"))
        self.assertEqual((by_line[8]["kind"], by_line[9]["speaker"]), ("character_cue", "GILES"))
        self.assertEqual(by_line[8]["speaker"], "GILES")
        self.assertEqual(by_line[9]["kind"], "parenthetical")
        self.assertEqual(by_line[10]["kind"], "dialogue")
        self.assertEqual(by_line[12]["kind"], "action")
        self.assertEqual(validate_parsed(parsed), [])

    def test_ambiguity_is_explicit(self):
        parsed = self.parse("INT. ROOM - NIGHT\n\nTHE MASTER\nHe steps forward.\n")
        self.assertTrue(any(i["kind"] == "ambiguous_cue" for i in parsed["issues"]))
        self.assertEqual([e for e in parsed["elements"] if e["text"] == "THE MASTER"][0]["kind"], "unknown")
        self.assertEqual(validate_parsed(parsed), [])

    def test_transcript_dialogue(self):
        parsed = self.parse("BUFFY: Hello.\nWILLOW: Hi.\nGILES: Morning.\n")
        self.assertEqual([e["kind"] for e in parsed["elements"]], ["dialogue"] * 3)
        self.assertEqual([e["speaker"] for e in parsed["elements"]], ["BUFFY", "WILLOW", "GILES"])

    def test_unindented_screenplay_dialogue(self):
        script = """Title
Written by: Example Writer
Teaser
INT. ROOM - DAY
BUFFY
Hello there.

WILLOW
Who are you?

GILES
I am Giles.

XANDER
I am Xander.

FAITH
I am Faith.

BUFFY
I know.

WILLOW
So do I.

GILES
Excellent.

XANDER
That tracks.

FAITH
Sure.

BUFFY
Let's go.

WILLOW
After you.

GILES
Certainly.

BUFFY
Good.
"""
        parsed = self.parse(script)
        self.assertEqual(parsed["profile"]["mode"], "screenplay_unindented")
        self.assertEqual(
            [e["speaker"] for e in parsed["elements"] if e["kind"] == "character_cue"],
            ["BUFFY", "WILLOW", "GILES", "XANDER", "FAITH",
             "BUFFY", "WILLOW", "GILES", "XANDER", "FAITH",
             "BUFFY", "WILLOW", "GILES", "BUFFY"],
        )
        self.assertTrue(all(
            e["kind"] == "metadata"
            for e in parsed["elements"][:2]
        ))
        self.assertEqual(sum(e["kind"] == "dialogue" for e in parsed["elements"]), 14)
        self.assertEqual(validate_parsed(parsed), [])

    def test_html_pre_preserves_whitespace(self):
        parsed = self.parse("<html><head><title>x</title></head><body><pre>" + SCRIPT + "</pre></body></html>", ext="html")
        self.assertTrue(any(e["kind"] == "dialogue" and e["speaker"] == "BUFFY" for e in parsed["elements"]))
        self.assertFalse(any("title" in e["text"].lower() for e in parsed["elements"]))
        self.assertEqual(validate_parsed(parsed), [])

    def test_integrity_validator_finds_removed_line(self):
        parsed = self.parse(SCRIPT)
        parsed["elements"].pop(0)
        findings = validate_parsed(parsed)
        self.assertTrue(any(i["kind"] == "line_coverage" for i in findings))

    def test_integrity_validator_finds_tampered_text(self):
        parsed = self.parse(SCRIPT)
        parsed["elements"][0]["text"] = "ALTERED"
        self.assertTrue(any(i["kind"] == "text_integrity" for i in validate_parsed(parsed)))
