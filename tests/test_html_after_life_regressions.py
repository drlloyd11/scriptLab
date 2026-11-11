"""Short synthetic v0.5 regression fixtures for Buffy HTML edge cases.

Actual copyrighted episode text is NOT redistributed in the package.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scriptlab.format_detector import is_act_end
from scriptlab.models import EpisodeFile
from scriptlab.parser import parse_document
from scriptlab.readers import read_episode
from scriptlab.validator import validate_parsed


FIXTURE = '''<html><body><center><table width="85%"><tr><td>
<p>Act One
<p>INT. LIVING ROOM - NIGHT
<center><font>DAWN<br>What a surprise!</font></center>
<center><font>DAWN (cont'd.)<br>Are you okay?</font></center>
<center><font>XANDER<br>Yes, I'm fine.</font></center>
<center><font>XAN'DER<br>How about you?</font></center>
<center>END OF EPISODE</center>
</td></tr></table></center></body></html>'''


class AfterLifeRegressionTests(unittest.TestCase):
    def parse(self, html: str = FIXTURE):
        with tempfile.TemporaryDirectory() as td:
            file = Path(td) / '6x03.htm'
            file.write_text(html, encoding='utf-8')
            result = parse_document(read_episode(EpisodeFile('buffy', 6, 3, file)))
        result['issues'].extend(validate_parsed(result))
        return result

    def test_continued_period_cue_is_valid(self):
        r = self.parse()
        turns = r['dialogue_turns']
        self.assertEqual([t['speaker'] for t in turns[:2]], ['DAWN', 'DAWN'])
        self.assertEqual(turns[1]['cue'], "DAWN (cont'd.)")
        self.assertEqual(turns[1]['text'], 'Are you okay?')

    def test_end_of_episode_is_act_end(self):
        r = self.parse()
        self.assertTrue(is_act_end('END OF EPISODE'))
        self.assertEqual([e['kind'] for e in r['elements'] if e['text'] == 'END OF EPISODE'], ['act_end'])
        self.assertFalse(any(e['kind'] == 'unknown' for e in r['elements']))

    def test_attested_internal_apostrophe_typo_is_not_silent(self):
        r = self.parse()
        turn = next(t for t in r['dialogue_turns'] if t['cue'] == "XAN'DER")
        self.assertEqual(turn['speaker'], 'XANDER')
        self.assertEqual(turn['text'], 'How about you?')
        self.assertTrue(any(i['kind'] == 'speaker_spelling_variant' for i in r['issues']))
        cue_element = next(e for e in r['elements'] if e['text'] == "XAN'DER")
        self.assertTrue(any('Punctuation-only' in evidence for evidence in cue_element['evidence']))

    def test_does_not_rewrite_an_unattested_proper_name(self):
        r = self.parse(FIXTURE.replace('<font>XANDER<br>Yes, I\'m fine.</font>',
                                       '<font>MARY<br>Yes, I\'m fine.</font>')
                                  .replace("XAN'DER", "O'BRIEN"))
        self.assertIn("O'BRIEN", [t['speaker'] for t in r['dialogue_turns']])
        self.assertFalse(any(i['kind'] == 'speaker_spelling_variant' for i in r['issues']))

    def test_validation_and_cue_coverage(self):
        r = self.parse()
        self.assertFalse(any(i['severity'] == 'error' for i in r['issues']))
        self.assertEqual(len(r['dialogue_turns']), 4)
        self.assertEqual(len([e for e in r['elements'] if e['kind'] == 'character_cue']), 4)


if __name__ == '__main__':
    unittest.main()
