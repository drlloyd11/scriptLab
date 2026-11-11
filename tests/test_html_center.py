"""Small invented examples reproducing the *layout* seen in the provided HTML.

No actual Buffy dialogue is redistributed with the test package.
"""
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from scriptlab.models import EpisodeFile
from scriptlab.parser import parse_document
from scriptlab.readers import malformed_html_warnings, read_episode
from scriptlab.validator import validate_parsed


HTML = '''<html><head><title>Ignore this</title></head><body>
<center><table><tr><td><p><b>A Sample</b></p></td></tr><tr><td>
<p>Teaser</p><p>INT. SCHOOL - NIGHT</p>
<center><font>MS. HALL (V.O.)<br>Welcome to the school.</font></center>
<p>She turns to the principal.</p>
<center><font>MR. BOOTH (cont'd)<br>(softly)<br>This is the first line.<br>Then another.</font></center>
<p>MR. BOOTH</p><p>Turns to the window.</p>
<center><font>SMASH CUT TO:</font></center>
<p>EXT. SCHOOL - DAY</p>
<center><font>BIG BAD<br>Who are you?</font></center>
<center><font>BIG<br>BAD<br>Not your friend.</font></center>
<center><font>MS. HALL<br>(cont'd)<br>Let's go.</font></center>
<center>END OF TEASER</center>
</td></tr></table></center></body></html>'''


class CenterHtmlTests(unittest.TestCase):
    def parse(self, text=HTML):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / '2x03.htm'
            p.write_text(text, encoding='utf-8')
            return parse_document(read_episode(EpisodeFile('buffy', 2, 3, p)))

    def test_centered_blocks_not_indentation(self):
        p = self.parse()
        self.assertEqual(p['profile']['mode'], 'html_center')
        self.assertEqual(validate_parsed(p), [])
        self.assertFalse([e for e in p['elements'] if e['kind'] == 'unknown'])
        counts = Counter(e['kind'] for e in p['elements'])
        self.assertEqual(counts['scene_heading'], 2)
        self.assertEqual(counts['act_heading'], 1)
        self.assertEqual(counts['act_end'], 1)
        self.assertEqual(counts['transition'], 1)
        self.assertEqual(counts['shot_heading'], 1)
        self.assertEqual(counts['metadata'], 1)
        self.assertEqual(len(p['dialogue_turns']), 5)
        spoken = [e for e in p['elements'] if e['kind'] == 'dialogue']
        self.assertEqual(len(spoken), 6)
        self.assertEqual(spoken[0]['speaker'], 'MS. HALL')
        self.assertEqual(spoken[-1]['speaker'], 'MS. HALL')
        self.assertTrue(any(e['kind'] == 'cue_modifier' for e in p['elements']))
        self.assertTrue(any(e['kind'] == 'parenthetical' and e['speaker'] == 'MR. BOOTH' for e in p['elements']))

    def test_speaker_name_wrapped_over_br(self):
        p = self.parse()
        bad = [e for e in p['elements'] if e['speaker'] == 'BIG BAD']
        self.assertEqual([x['kind'] for x in bad], ['character_cue', 'dialogue', 'character_cue', 'cue_modifier', 'dialogue'])
        self.assertEqual([x['text'] for x in bad if x['kind'] == 'dialogue'], ['Who are you?', 'Not your friend.'])

    def test_unknown_center_group_is_flagged(self):
        p = self.parse('<html><body><center><font>???<br>What is this?</font></center></body></html>')
        self.assertEqual([e['kind'] for e in p['elements']], ['unknown', 'unknown'])
        self.assertTrue(any(i['kind'] == 'ambiguous_html_block' for i in p['issues']))
        self.assertEqual(validate_parsed(p), [])

    def test_known_speaker_cue_with_descriptive_parenthetical(self):
        p = self.parse(
            '<html><body><center>BUFFY<br>Hello.</center>'
            '<center>BUFFY (hurt)<br>Why?</center></body></html>'
        )
        cue, dialogue = [e for e in p['elements'] if e['line'] >= 3]
        self.assertEqual((cue['kind'], cue['speaker'], cue['text']),
                         ('character_cue', 'BUFFY', 'BUFFY (hurt)'))
        self.assertEqual((dialogue['kind'], dialogue['speaker'], dialogue['text']),
                         ('dialogue', 'BUFFY', 'Why?'))
        self.assertTrue(any('descriptive parenthetical' in evidence
                            for evidence in cue['evidence']))
        self.assertEqual(validate_parsed(p), [])

    def test_known_speaker_and_dialogue_run_together(self):
        p = self.parse(
            '<html><body><center>VAMP #2<br>Earlier.</center>'
            "<center>VAMP #2 You got the boss' kittens!</center></body></html>"
        )
        dialogue = next(e for e in p['elements'] if "boss" in e['text'])
        self.assertEqual((dialogue['kind'], dialogue['speaker'], dialogue['text']),
                         ('dialogue', 'VAMP #2', "VAMP #2 You got the boss' kittens!"))
        self.assertTrue(any('run together' in evidence for evidence in dialogue['evidence']))
        self.assertEqual(validate_parsed(p), [])

    def test_lowercase_continuation_after_known_name_is_not_inline_cue(self):
        p = self.parse(
            '<html><body><center>BUFFY<br>Earlier.</center>'
            '<center>BUFFY as much as I can take.</center></body></html>'
        )
        line = next(e for e in p['elements'] if 'as much' in e['text'])
        self.assertEqual(line['kind'], 'unknown')
        self.assertTrue(any(i['kind'] == 'ambiguous_html_block' and i['line'] == line['line']
                            for i in p['issues']))

    def test_interrupted_lowercase_dialogue_and_malformed_tag_are_flagged(self):
        source = """<html><body>
<center>BUFFY<br>Prior line.</center>
<center>BUFFY<BR< corrupted tags> as much of it as I can take-</center>
</body></html>"""
        p = self.parse(source)
        line = next(e for e in p['elements'] if 'as much' in e['text'])
        self.assertEqual((line['kind'], line['speaker']),
                         ('dialogue', 'BUFFY'))
        self.assertTrue(any(
            i['kind'] == 'reader_warning' and 'Malformed HTML tag opener near source line 3' in i['message']
            for i in p['issues']
        ))
        self.assertEqual(malformed_html_warnings('<html><body>clean</body></html>'), [])

    def test_voice_over_cue_with_spaced_ocr_modifier(self):
        p = self.parse(
            '<html><body><center>BUFFY<br>Earlier.</center>'
            '<center>BUFFY. (V. 0.)<br>Listen.</center></body></html>'
        )
        cue, dialogue = [e for e in p['elements'] if e['line'] >= 3]
        self.assertEqual((cue['kind'], cue['speaker'], cue['text']),
                         ('character_cue', 'BUFFY', 'BUFFY. (V. 0.)'))
        self.assertEqual((dialogue['kind'], dialogue['speaker'], dialogue['text']),
                         ('dialogue', 'BUFFY', 'Listen.'))

    def test_on_tv_cue_modifier_preserves_speaker_identity(self):
        p = self.parse(
            "<html><body><center>WOMAN'S VOICE (ON TV)<br>Look out!</center></body></html>"
        )
        self.assertEqual(
            [(e['kind'], e['speaker']) for e in p['elements']],
            [('character_cue', "WOMAN'S VOICE"), ('dialogue', "WOMAN'S VOICE")],
        )

    def test_tv_cue_modifier_with_periods(self):
        p = self.parse(
            '<html><body><center>REPORTER (T.V.)<br>The news.</center></body></html>'
        )
        self.assertEqual(
            [(e['kind'], e['speaker'], e['text']) for e in p['elements']],
            [('character_cue', 'REPORTER', 'REPORTER (T.V.)'),
             ('dialogue', 'REPORTER', 'The news.')],
        )

    def test_numeric_offscreen_cue_keeps_role_and_modifier(self):
        p = self.parse(
            '<html><body><center>911 OPERATOR (O.S.)<br>'
            'Help is on the way.<br>Stay on the line.</center></body></html>'
        )
        turns = [turn for turn in p['dialogue_turns'] if turn['speaker'] == '911 OPERATOR']
        self.assertEqual([turn['text'] for turn in turns], [
            'Help is on the way. Stay on the line.',
        ])
        self.assertTrue(all('O.S.' in turn['modifiers'] for turn in turns))

    def test_continued_dialogue_across_centered_paragraphs(self):
        p = self.parse(
            '<html><body><center>BUFFY<br>It is a</center>'
            '<center>person.<br>(shows the photo)<br>Do you know her?</center></body></html>'
        )
        self.assertEqual(
            [(e['kind'], e['speaker'], e['text']) for e in p['elements']],
            [('character_cue', 'BUFFY', 'BUFFY'),
             ('dialogue', 'BUFFY', 'It is a'),
             ('dialogue', 'BUFFY', 'person.'),
             ('parenthetical', 'BUFFY', '(shows the photo)'),
             ('dialogue', 'BUFFY', 'Do you know her?')],
        )

    def test_reviewed_scene_heading_prefix_variants(self):
        source = """<html><body>
<p>EXT./INT. SUPERVAN - CONTINUOUS - NIGHT</p>
<p>INT.CONDEMNED HOUSE - BASEMENT - CONTINUOUS</p>
<p>INT./EXT. CAR - STREET - NIGHT</p>
<p>INT./EXT. CAR - TREET - NIGHT</p>
<p>EXT./INT. CAR - STREET - NIGHT</p>
<p align=center><font>INT. BISON'S LODGE - CORNER OF MAIN ROOM - CONTINUOUS</font></p>
<p>A36 INT. BUFFY'S HOUSE - WILLOW'S BEDROOM - CONTINUOUS</p>
<p>B36 INT. BUFFY'S HOUSE - WILLOW'S BEDROOM - DAY</p>
<p>EXT./INT. - BUFFY'S HOUSE - FOYER - DAY</p>
</body></html>"""
        parsed = self.parse(source)
        expected = [
            "EXT./INT. SUPERVAN - CONTINUOUS - NIGHT",
            "INT.CONDEMNED HOUSE - BASEMENT - CONTINUOUS",
            "INT./EXT. CAR - STREET - NIGHT",
            "INT./EXT. CAR - TREET - NIGHT",
            "EXT./INT. CAR - STREET - NIGHT",
            "INT. BISON'S LODGE - CORNER OF MAIN ROOM - CONTINUOUS",
            "A36 INT. BUFFY'S HOUSE - WILLOW'S BEDROOM - CONTINUOUS",
            "B36 INT. BUFFY'S HOUSE - WILLOW'S BEDROOM - DAY",
            "EXT./INT. - BUFFY'S HOUSE - FOYER - DAY",
        ]
        headings = [e for e in parsed['elements'] if e['text'] in expected]
        self.assertEqual([e['text'] for e in headings], expected)
        self.assertTrue(all(e['kind'] == 'scene_heading' for e in headings))
        self.assertFalse(any(i['kind'] in {'ambiguous_html_block', 'suspected_scene_heading'}
                             for i in parsed['issues']))

    def test_standalone_centered_action_and_camera_direction(self):
        parsed = self.parse(
            '<html><body><center>Xander interjects.</center>'
            '<center>CLOSE UP: A CURVED KNIFE BLADE</center>'
            '<center>ANGLE: XANDER AND AMPATA</center>'
            '<center>???<br>What is this?</center></body></html>'
        )
        by_text = {e['text']: e for e in parsed['elements']}
        self.assertEqual(by_text['Xander interjects.']['kind'], 'action')
        self.assertEqual(by_text['CLOSE UP: A CURVED KNIFE BLADE']['kind'], 'shot_heading')
        self.assertEqual(by_text['ANGLE: XANDER AND AMPATA']['kind'], 'shot_heading')
        self.assertEqual(by_text['???']['kind'], 'unknown')
        self.assertTrue(any(i['kind'] == 'ambiguous_html_block' for i in parsed['issues']))

    def test_html_preserves_layout_provenance(self):
        p = self.parse()
        group = [l for l in p['lines'] if l['text'] in ('MR. BOOTH (cont\'d)', '(softly)', 'This is the first line.')]
        self.assertEqual(len({l['group_id'] for l in group}), 1)
        self.assertTrue(all(l['layout'] == 'html_center' for l in group))
        self.assertTrue(all(isinstance(l['source_line'], int) for l in group))
