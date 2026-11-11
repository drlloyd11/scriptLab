"""Invented HTML test patterns for multi-speaker musical-era scripts."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scriptlab.models import EpisodeFile
from scriptlab.readers import read_episode
from scriptlab.parser import parse_document
from scriptlab.validator import validate_parsed


HTML = """<html><head><title>Sample</title></head><body>
<center><table width=85%><tr><td><p>Act One</p><p>INT. LOUNGE - DAY
<center><font>MARIA<br>Good morning!
<p>DAVID<br>(talking softly)<br>Morning to you.
<p>MARIA/DAVID<br>WE SING TOGETHER</font></center>
<p>They turn toward the band.
<center><table width=60%><tr>
<td>MARIA<br>THE SKY IS BLUE</td><td>DAVID<br>THE SEA IS GREEN</td>
</tr><tr><td><p>DAVID<br>MY NEXT LINE</p><p>MARIA<br>HER NEXT LINE</p></td><td>MARIA/DAVID<br>AGAIN TOGETHER</td></tr></table></center>
<p>EXT. GARDEN - NIGHT
<center><font>MARIA<br>(quiet and<br>uneasy)<br>Where are we?</font></center>
<center>END OF SHOW</center>
</td></tr></table></center>
</body></html>"""


class MusicalHtmlTests(unittest.TestCase):
    def parse(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "6x07.htm"
            p.write_text(HTML, encoding="utf-8")
            return parse_document(read_episode(EpisodeFile("buffy", 6, 7, p)))

    def test_multiple_speakers_within_center(self):
        result = self.parse()
        assert not result["issues"], result["issues"]
        assert not validate_parsed(result), validate_parsed(result)
        assert [t["speaker"] for t in result["dialogue_turns"][:3]] == [
            "MARIA", "DAVID", "MARIA/DAVID"
        ]
        assert any(t["speaker"] == "DAVID" and t["text"] == "MY NEXT LINE"
                   for t in result["dialogue_turns"])
        assert any(t["speaker"] == "MARIA" and t["text"] == "HER NEXT LINE"
                   for t in result["dialogue_turns"])
        assert sum(e["kind"] == "scene_heading" for e in result["elements"]) == 2

    def test_parallel_columns_and_wrapped_parenthetical(self):
        result = self.parse()
        duet = [t for t in result["dialogue_turns"] if t["parallel_row"] is not None]
        first = [t for t in duet if t["text"] in ("THE SKY IS BLUE", "THE SEA IS GREEN")]
        assert len(first) == 2
        assert first[0]["parallel_row"] == first[1]["parallel_row"]
        assert {t["parallel_column"] for t in first} == {1, 2}
        wrapped = next(t for t in result["dialogue_turns"] if t["text"] == "Where are we?")
        assert [s["kind"] for s in wrapped["segments"]] == [
            "parenthetical", "parenthetical", "dialogue"
        ]
        assert not [e for e in result["elements"] if e["kind"] == "unknown"]
        assert any(e["kind"] == "act_end" and e["text"] == "END OF SHOW"
                   for e in result["elements"])

    def test_narrow_table_inside_center_is_parallel_dialogue_without_outer_table(self):
        source = """<html><body><center><table width="60%"><tr>
<td>MARIA<br>THE SKY IS BLUE</td><td>DAVID<br>THE SEA IS GREEN</td>
</tr></table></center></body></html>"""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "6x07.htm"
            path.write_text(source, encoding="utf-8")
            result = parse_document(read_episode(EpisodeFile("buffy", 6, 7, path)))
        turns = {turn["speaker"]: turn for turn in result["dialogue_turns"]}
        assert turns["MARIA"]["parallel_row"] == turns["DAVID"]["parallel_row"]
        assert turns["MARIA"]["parallel_column"] != turns["DAVID"]["parallel_column"]
        assert not validate_parsed(result), validate_parsed(result)

    def test_explicit_discordant_note_description_is_musical_direction(self):
        source = """<html><body><center><table width="85%"><tr><td>
<p>Act One</p><p>INT. LOUNGE - DAY</p>
<p>That last note is entirely discordant. They ignore it.</p>
</td></tr></table></center></body></html>"""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "6x07.htm"
            path.write_text(source, encoding="utf-8")
            result = parse_document(read_episode(EpisodeFile("buffy", 6, 7, path)))
        direction = next(e for e in result["elements"] if "discordant" in e["text"])
        assert direction["kind"] == "musical_direction"
        assert not validate_parsed(result), validate_parsed(result)

    def test_music_accompanying_action_remains_action(self):
        source = """<html><body><center><table width="85%"><tr><td>
<p>Act One</p><p>INT. LOUNGE - DAY</p>
<p>They dance as the music plays.</p>
</td></tr></table></center></body></html>"""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "6x07.htm"
            path.write_text(source, encoding="utf-8")
            result = parse_document(read_episode(EpisodeFile("buffy", 6, 7, path)))
        action = next(e for e in result["elements"] if "dance" in e["text"])
        assert action["kind"] == "action"

    def test_center_aligned_paragraphs_inside_outer_table_are_dialogue(self):
        source = """<html><body><center><table width="85%"><tr><td>
<p>INT. ROOM - DAY</p>
<p align="center">BUFFY<br>Are you coming?</p>
<p>She looks toward the door.</p>
</td></tr></table></center></body></html>"""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "6x12.htm"
            path.write_text(source, encoding="utf-8")
            result = parse_document(read_episode(EpisodeFile("buffy", 6, 12, path)))
        self.assertEqual(result["profile"]["mode"], "html_center")
        self.assertEqual(
            [(e["kind"], e["speaker"], e["text"]) for e in result["elements"]
             if e["text"] in {"BUFFY", "Are you coming?"}],
            [("character_cue", "BUFFY", "BUFFY"), ("dialogue", "BUFFY", "Are you coming?")],
        )
        self.assertTrue(any(e["kind"] == "action" and e["text"] == "She looks toward the door."
                            for e in result["elements"]))
        self.assertEqual(validate_parsed(result), [])
