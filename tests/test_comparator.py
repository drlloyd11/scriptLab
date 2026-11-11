import unittest
from scriptlab.comparator import compare_labels, independent_llm_labels


class ComparatorTests(unittest.TestCase):
    def setUp(self):
        self.parsed = {
            "episode": {"key": "buffy/S01E01"},
            "lines": [{"line": 1, "text": "BUFFY:"}, {"line": 2, "text": "Hi"}, {"line": 3, "text": ""}],
            "elements": [
                {"line": 1, "kind": "character_cue", "speaker": "BUFFY"},
                {"line": 2, "kind": "dialogue", "speaker": "BUFFY"},
            ],
        }

    def test_detects_speaker_mismatch(self):
        result = compare_labels(self.parsed, {1: {"kind": "character_cue", "speaker": "BUFFY"},
                                              2: {"kind": "dialogue", "speaker": "WILLOW"}}, "fake")
        self.assertEqual(result["agreements"], 1)
        self.assertEqual(len(result["disagreements"]), 1)
        self.assertEqual(result["disagreements"][0]["line"], 2)

    def test_missing_llm_line_not_agreement(self):
        result = compare_labels(self.parsed, {1: {"kind": "character_cue", "speaker": "BUFFY"}}, "fake")
        self.assertEqual(result["compared_lines"], 1)
        self.assertEqual(len(result["llm_failures"]), 1)

    def test_ollama_can_be_stubbed(self):
        def fake_ollama(system, user, model, base_url):
            self.assertIn("[1] txt | BUFFY:", user)
            self.assertNotIn("character_cue / BUFFY", user)
            return {"labels": [
                {"line": 1, "kind": "character_cue", "speaker": "BUFFY"},
                {"line": 2, "kind": "dialogue", "speaker": "BUFFY"},
            ]}
        labels, failures = independent_llm_labels(self.parsed, "fake", ask=fake_ollama)
        self.assertFalse(failures)
        self.assertEqual(labels[2]["speaker"], "BUFFY")
