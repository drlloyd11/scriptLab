"""Offline, source-grounded regressions for S02E04 live pilot discrepancies.

These are synthetic HTML samples reproducing the reported layout, not original
copyrighted episode text or human-approved accuracy gold cases.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scriptlab.format_detector import cue_like, cue_modifiers
from scriptlab.html_verifier import compare_raw_html
from scriptlab.models import EpisodeFile
from scriptlab.parser import parse_document
from scriptlab.readers import read_episode


HTML = """<html><body>
<p>CUT TO:</p>
<p>INT. BUS STATION - NIGHT</p>
<center><font>VOICE (cont'd;
O.C.)<br>Ampata!</font></center>
<p>AMPATA'S POV: A HIDEOUS MONSTER</p>
</body></html>"""


class S02E04LivePilotFixTests(unittest.TestCase):
    def parse(self, html=HTML):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / '2x04.htm'
        path.write_text(html, encoding='utf-8')
        parsed = parse_document(read_episode(EpisodeFile('buffy', 2, 4, path)))
        return path, parsed

    def test_compound_cue_and_dialogue_in_multiline_html(self):
        _, parsed = self.parse()
        cue = [e for e in parsed['elements'] if e['kind'] == 'character_cue']
        self.assertEqual(len(cue), 1)
        self.assertEqual(cue[0]['speaker'], 'VOICE')
        self.assertEqual(cue[0]['text'], "VOICE (cont'd; O.C.)")
        speech = [e for e in parsed['elements'] if e['kind'] == 'dialogue']
        self.assertEqual([(e['text'], e['speaker']) for e in speech], [('Ampata!', 'VOICE')])
        turns = parsed['dialogue_turns']
        self.assertEqual(turns[0]['modifiers'], ["cont'd", 'O.C.'])
        self.assertEqual(turns[0]['text'], 'Ampata!')
        self.assertFalse([e for e in parsed['elements'] if e['kind'] == 'unknown'])

    def test_cue_vocab_is_conservative_and_supports_commas(self):
        self.assertTrue(cue_like('VOICE (O.C., CONT\'D)'))
        self.assertEqual(cue_modifiers('VOICE (O.C., CONT\'D)'), ['O.C.', "CONT'D"])
        self.assertTrue(cue_like('DEMON (V.0.)'))
        self.assertFalse(cue_like('VOICE (thinking about tomorrow)'))
        self.assertFalse(cue_like('VOICE (O.C.; not a modifier)'))

    def test_explicit_pov_shot_remains_camera_direction(self):
        _, parsed = self.parse()
        shot = [e for e in parsed['elements'] if e['text'] == "AMPATA'S POV: A HIDEOUS MONSTER"]
        self.assertEqual(len(shot), 1)
        self.assertEqual(shot[0]['kind'], 'shot_heading')

    def test_mixed_case_close_on_direction_is_shot_heading(self):
        html = HTML.replace(
            "<p>AMPATA'S POV: A HIDEOUS MONSTER</p>",
            "<p>CLOSE ON: THE MUMMY'S MOUTH as it puckers into a hideous KISS.</p>",
        )
        _, parsed = self.parse(html)
        shot = [e for e in parsed['elements']
                if e['text'] == "CLOSE ON: THE MUMMY'S MOUTH as it puckers into a hideous KISS."]
        self.assertEqual(len(shot), 1)
        self.assertEqual(shot[0]['kind'], 'shot_heading')

    def test_mixed_case_camera_words_without_direction_marker_are_not_promoted(self):
        from scriptlab.format_detector import is_shot_heading

        self.assertFalse(is_shot_heading("Close on the mummy's mouth as it puckers."))

    def test_scoring_excludes_line_before_requested_html_window(self):
        path, parsed = self.parse()
        # The physical HTML source line 2 is CUT TO:, but the independent
        # pilot only requests lines 3-6. No model output should be needed for it.
        def fake_llm(system, user, model, base_url):
            self.assertIn("AMPATA'S POV: A HIDEOUS MONSTER", system)
            self.assertIn("VOICE (cont'd; O.C.)", system)
            self.assertIn('<br>Ampata!', user)
            return {'elements': [
                {'element_type': 'scene_heading', 'original_text': 'INT. BUS STATION - NIGHT',
                 'speaker': None, 'normalized_speaker': None, 'source_span': None, 'uncertainty': None},
                {'element_type': 'character_cue', 'original_text': "VOICE (cont'd; O.C.)",
                 'speaker': "VOICE (cont'd; O.C.)", 'normalized_speaker': 'VOICE',
                 'source_span': None, 'uncertainty': None},
                {'element_type': 'dialogue', 'original_text': 'Ampata!',
                 'speaker': "VOICE (cont'd; O.C.)", 'normalized_speaker': 'VOICE',
                 'source_span': None, 'uncertainty': None},
                {'element_type': 'shot_direction', 'original_text': "AMPATA'S POV: A HIDEOUS MONSTER",
                 'speaker': None, 'normalized_speaker': None, 'source_span': None, 'uncertainty': None},
            ]}

        result = compare_raw_html(
            path.read_text(encoding='utf-8'), parsed, path, parsed['episode']['sha256'],
            start_line=3, end_line=6, ask=fake_llm,
        )
        self.assertEqual(result['selected_source_lines'], {'start': 3, 'end': 6})
        self.assertFalse([e for e in result['unmatched_python_elements'] if e['text'] == 'CUT TO:'])
        self.assertEqual(result['llm_failures_or_omissions'], [])
        self.assertFalse(result['uncertain_alignments'])
        # Different nomenclature is intentional: the verifier uses
        # "shot_direction" and Python uses "shot_heading".
        self.assertFalse(result['classification_disagreements'])
        self.assertEqual(result['agreement_count'], 4)


if __name__ == '__main__':
    unittest.main()
