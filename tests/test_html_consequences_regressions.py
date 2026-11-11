"""Synthetic regressions for Buffy S03E15 formatting anomalies.

No episode text is redistributed with the parser. The fixtures are invented.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scriptlab.cli import run
from scriptlab.format_detector import is_script_end, is_transition, suspected_scene_reason
from scriptlab.models import EpisodeFile
from scriptlab.parser import parse_document
from scriptlab.readers import read_episode
from scriptlab.validator import validate_parsed

HTML = '''<html><body><center><table><tr><td>
<p>Teaser</p>
<p>INT. STUDY - NIGHT</p>
<p align="right">FADE UP</p>
<p>Someone checks a clock.</p>
<center>JUNE<br>Is anyone there?</center>
<p align="right">BLACK OUT.</p>
<center>END OF TEASER</center>
<p>Act One</p>
<p>EXT. STREET - NIGHT</p>
<p align="right">FLASH TO:</p>
<p>INT. OLD HOUSE - DAY</p>
<p align="right">INTERCUT WITH:</p>
<p>!NT. BARN - BACK ROOM - NIGHT</p>
<center>JUNE<br>First line.</center>
<p>HOUSE - DINING ROOM - NIGHT</p>
<center>LEO<br>Second line.</center>
<p align="right">TIME CUT TO:</p>
<p>A VOICE STOPS HER.</p>
<p>WHOMP!</p>
<p>BOOM!</p>
<p>ANGLE: THE DOOR</p>
<p align="right">FADE TO:</p>
<p align="right">BLACK OUT.</p>
<center>THE END</center>
<center>Read another draft here!</center>
<p>INT. NOT A REAL SCENE - DAY</p>
</td></tr></table></center></body></html>'''


class ConsequencesRegressionTests(unittest.TestCase):
    def parse_html(self, html=HTML):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / '3x15.htm'
            path.write_text(html, encoding='utf-8')
            parsed = parse_document(read_episode(EpisodeFile('buffy', 3, 15, path)))
            return parsed

    def test_provisional_scene_boundaries_are_explicit(self):
        parsed = self.parse_html()
        candidates = [e for e in parsed['elements'] if e['kind'] == 'suspected_scene_heading']
        self.assertEqual([e['text'] for e in candidates], [
            '!NT. BARN - BACK ROOM - NIGHT', 'HOUSE - DINING ROOM - NIGHT'])
        self.assertEqual([e['scene_index'] for e in candidates], [4, 5])
        self.assertEqual([i['kind'] for i in parsed['issues'] if i['kind'] == 'suspected_scene_heading'],
                         ['suspected_scene_heading', 'suspected_scene_heading'])
        self.assertTrue(all('Provisional boundary' in e['evidence'][-1] for e in candidates))
        self.assertEqual(validate_parsed(parsed), [])

    def test_provisional_boundary_isnt_rewritten_or_silent(self):
        parsed = self.parse_html()
        boundary = next(e for e in parsed['elements'] if e['text'].startswith('!NT.'))
        self.assertEqual(boundary['text'], '!NT. BARN - BACK ROOM - NIGHT')
        self.assertTrue(any(i['line'] == boundary['line'] for i in parsed['issues']))
        turns = {t['speaker']: t for t in parsed['dialogue_turns'] if t['speaker'] in {'JUNE', 'LEO'}}
        self.assertEqual(turns['LEO']['scene_index'], 5)
        self.assertEqual(turns['LEO']['text'], 'Second line.')

    def test_new_transitions_and_original_blackout(self):
        parsed = self.parse_html()
        values = [e['text'] for e in parsed['elements'] if e['kind'] == 'transition']
        self.assertEqual(values, ['FADE UP', 'BLACK OUT.', 'FLASH TO:', 'INTERCUT WITH:',
                                  'TIME CUT TO:', 'FADE TO:', 'BLACK OUT.'])
        self.assertEqual(len([e for e in parsed['elements'] if e['kind'] == 'act_end'
                              and e['text'] == 'THE END']), 1)

    def test_impact_effects_vs_shot_and_action(self):
        parsed = self.parse_html()
        by_text = {e['text']: e['kind'] for e in parsed['elements']}
        self.assertEqual(by_text['A VOICE STOPS HER.'], 'action')
        self.assertEqual(by_text['WHOMP!'], 'sound_effect')
        self.assertEqual(by_text['BOOM!'], 'sound_effect')
        self.assertEqual(by_text['ANGLE: THE DOOR'], 'shot_heading')

    def test_camera_cues_ending_in_period_are_still_shots(self):
        from scriptlab.format_detector import is_shot_heading
        self.assertTrue(is_shot_heading('ANGLE: EVERYBODY ELSE.'))
        self.assertFalse(is_shot_heading('ANYA, DAWN AND XANDER BURST IN.'))
        self.assertTrue(is_transition('INTERCUT WITH WILLOW IN HER ROOM.'))

    def test_the_end_stops_following_paragraphs(self):
        parsed = self.parse_html()
        by_text = {e['text']: e['kind'] for e in parsed['elements']}
        self.assertEqual(by_text['Read another draft here!'], 'supplementary_metadata')
        self.assertEqual(by_text['INT. NOT A REAL SCENE - DAY'], 'supplementary_metadata')
        self.assertEqual(len([e for e in parsed['elements'] if e['kind'] == 'scene_heading']), 3)
        self.assertEqual(validate_parsed(parsed), [])

    def test_provisional_scene_detection_is_conservative(self):
        self.assertIsNone(suspected_scene_reason('INT. DINING ROOM - NIGHT'))
        self.assertIsNone(suspected_scene_reason('ON BUFFY AND FRIENDS'))
        self.assertIsNone(suspected_scene_reason('A VOICE STOPS HER.'))
        self.assertIsNone(suspected_scene_reason('!NT. NO TIME GIVEN'))
        self.assertIsNone(suspected_scene_reason('THE END'))
        self.assertIsNone(suspected_scene_reason('EXT. RIVER - DAY'))
        self.assertTrue(suspected_scene_reason('HOUSE - LIVING ROOM - NIGHT'))

    def test_user_reviewed_location_heading_variants_are_scene_boundaries(self):
        source = """<html><body>
<p>A FROG - INT. SCIENCE CLASS - DAY</p>
<p>BUFFY OUT THERE ALONE - EXT. WEATHERLY PARK - NIGHT</p>
<p>FLASHBACK - XANDER IN BIOLOGY CLASS - DAY</p>
<p>HOUSE - LIVING ROOM - NIGHT</p>
</body></html>"""
        parsed = self.parse_html(source)
        by_text = {e['text']: e['kind'] for e in parsed['elements']}
        self.assertEqual(by_text['A FROG - INT. SCIENCE CLASS - DAY'], 'scene_heading')
        self.assertEqual(by_text['BUFFY OUT THERE ALONE - EXT. WEATHERLY PARK - NIGHT'], 'scene_heading')
        self.assertEqual(by_text['FLASHBACK - XANDER IN BIOLOGY CLASS - DAY'], 'scene_heading')
        self.assertEqual(by_text['HOUSE - LIVING ROOM - NIGHT'], 'suspected_scene_heading')

    def test_user_reviewed_season_seven_location_headings(self):
        source = """<html><body>
<p>GNARL'S LAIR - DEEPER INSIDE THE CAVE - NIGHT</p>
<p>40 INT SUMMMERS' HOME - DINING ROOM - NEAR DUSK</p>
<p>OTHER HOUSE - DINING ROOM - NEAR DUSK</p>
</body></html>"""
        parsed = self.parse_html(source)
        by_text = {e['text']: e['kind'] for e in parsed['elements']}
        self.assertEqual(by_text["GNARL'S LAIR - DEEPER INSIDE THE CAVE - NIGHT"], 'scene_heading')
        self.assertEqual(by_text["40 INT SUMMMERS' HOME - DINING ROOM - NEAR DUSK"], 'scene_heading')
        self.assertEqual(by_text['OTHER HOUSE - DINING ROOM - NEAR DUSK'], 'suspected_scene_heading')

    def test_end_and_transition_detectors_are_separate(self):
        self.assertTrue(is_script_end('THE END'))
        self.assertFalse(is_transition('THE END'))
        self.assertFalse(is_script_end('BLACK OUT.'))
        self.assertTrue(is_transition('BLACK OUT.'))
        self.assertTrue(is_transition('BLACKOUT.'))
        self.assertTrue(is_transition('QUICK DISSOLVE TO:'))
        for text in ('FADE UP', 'FLASH TO:', 'INTERCUT WITH:', 'TIME CUT TO:', 'FADE TO:'):
            self.assertTrue(is_transition(text), text)

    def test_txt_input_still_understands_new_transitions(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'S01E01.txt'
            path.write_text('INT. LIBRARY - DAY\nFLASH TO:\nEXT. FOREST - NIGHT\nBOOM!\nTHE END\nWebsite footer\n', encoding='utf-8')
            parsed = parse_document(read_episode(EpisodeFile('angel', 1, 1, path)))
            by_text = {e['text']: e['kind'] for e in parsed['elements']}
            self.assertEqual(by_text['FLASH TO:'], 'transition')
            self.assertEqual(by_text['BOOM!'], 'sound_effect')
            self.assertEqual(by_text['Website footer'], 'supplementary_metadata')
            self.assertEqual(validate_parsed(parsed), [])

    def test_strict_cli_flags_provisional_boundaries(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / 'buffy'
            folder.mkdir()
            (folder / '3x15.htm').write_text(HTML, encoding='utf-8')
            root = str(folder)
            self.assertEqual(run(['parse', '--series', 'buffy', root, '--out', str(Path(temp) / 'out')]), 0)
            self.assertEqual(run(['parse', '--series', 'buffy', root, '--out', str(Path(temp) / 'strict'),
                                  '--fail-on-ambiguity']), 2)


if __name__ == '__main__':
    unittest.main()
