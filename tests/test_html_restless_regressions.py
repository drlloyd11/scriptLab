"""Synthetic fixtures for Buffy S04E22 structural edge cases.

The user's copyrighted episode is not redistributed with the parser.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scriptlab.models import EpisodeFile
from scriptlab.parser import parse_document
from scriptlab.readers import read_episode
from scriptlab.validator import validate_parsed


HTML_FIXTURE = '''<html><body><center><table width="85%"><tr><td>
<p>Teaser</p><p>EXT. FAIRGROUND - DAY</p>
<center>VOICE:<br>Look at the bright lights!</center>
<center>BUFFY<br>That sounds lovely.</center>
<center>END OF TEASER</center>
<p>Act One</p><p>INT. CONTROL ROOM - NIGHT</p>
<center>VOICE:<br>Attention, visitors.<br>Please remain calm.</center>
<p>A monitor blinks.</p>
<center>END OF SHOW</center>
<center><i>Read Act Four of the <a href="draft.html">Writer's Draft!</a></i></center>
<p>EXT. NOT A NEW SCENE - DAY</p>
</td></tr></table></center></body></html>'''


class RestlessRegressionTests(unittest.TestCase):
    def parse_html(self, source=HTML_FIXTURE):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "4x22.htm"
            path.write_text(source, encoding="utf-8")
            result = parse_document(read_episode(EpisodeFile("buffy", 4, 22, path)))
            result["issues"].extend(validate_parsed(result))
            return result

    def test_voice_with_colon_becomes_cue_and_preserves_raw_cue(self):
        result = self.parse_html()
        voices = [turn for turn in result["dialogue_turns"] if turn["speaker"] == "VOICE"]
        self.assertEqual(len(voices), 2)
        self.assertEqual(voices[0]["cue"], "VOICE:")
        self.assertEqual(voices[0]["text"], "Look at the bright lights!")
        self.assertEqual(voices[1]["text"], "Attention, visitors. Please remain calm.")
        self.assertFalse(any(e["kind"] == "unknown" for e in result["elements"]))

    def test_episode_end_marks_supplementary_content(self):
        result = self.parse_html()
        supplemental = [e for e in result["elements"] if e["kind"] == "supplementary_metadata"]
        self.assertEqual(len(supplemental), 2)
        self.assertIn("Writer's Draft!", supplemental[0]["text"])
        self.assertEqual(supplemental[1]["text"], "EXT. NOT A NEW SCENE - DAY")
        self.assertEqual(len([e for e in result["elements"] if e["kind"] == "scene_heading"]), 2)
        self.assertFalse(any(i["kind"] == "ambiguous_html_block" for i in result["issues"]))

    def test_end_of_teaser_is_not_end_of_script(self):
        result = self.parse_html()
        self.assertEqual(len([e for e in result["elements"] if e["kind"] == "act_heading"]), 2)
        self.assertEqual(len([e for e in result["elements"] if e["kind"] == "dialogue"]), 4)
        self.assertTrue(any(t["speaker"] == "BUFFY" for t in result["dialogue_turns"]))

    def test_end_of_episode_also_stops_structural_parsing(self):
        result = self.parse_html(HTML_FIXTURE.replace("END OF SHOW", "END OF EPISODE"))
        self.assertEqual(len([e for e in result["elements"] if e["kind"] == "supplementary_metadata"]), 2)
        self.assertTrue(any(e["kind"] == "act_end" and e["text"] == "END OF EPISODE"
                            for e in result["elements"]))

    def test_normal_dialogue_with_colon_is_not_new_cue(self):
        fixture = HTML_FIXTURE.replace("That sounds lovely.", "VOICE: not a character cue here.")
        result = self.parse_html(fixture)
        buffy = next(t for t in result["dialogue_turns"] if t["speaker"] == "BUFFY")
        self.assertEqual(buffy["text"], "VOICE: not a character cue here.")
        self.assertEqual(len([t for t in result["dialogue_turns"] if t["speaker"] == "VOICE"]), 2)

    def test_punctuation_only_affects_centered_cue_recognition(self):
        fixture = HTML_FIXTURE.replace('<p>A monitor blinks.</p>', '<p>VOICE:</p><p>A monitor blinks.</p>')
        result = self.parse_html(fixture)
        standalone = [e for e in result["elements"] if e["text"] == "VOICE:"]
        self.assertEqual(len(standalone), 3)
        self.assertEqual(len([e for e in standalone if e["kind"] == "character_cue"]), 2)

    def test_no_integrity_errors_and_source_line_numbers_preserved(self):
        result = self.parse_html()
        self.assertFalse([i for i in result["issues"] if i["severity"] == "error"])
        self.assertTrue(all(e["source_line"] >= 1 for e in result["elements"]))
        self.assertEqual(len(result["elements"]), len([l for l in result["lines"] if l["text"].strip()]))


if __name__ == "__main__":
    unittest.main()
