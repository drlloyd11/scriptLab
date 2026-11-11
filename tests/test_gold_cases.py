"""Automatically exercise only explicitly human-reviewed HTML reference cases."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from scriptlab.html_verifier import validate_gold_case
from scriptlab.models import EpisodeFile
from scriptlab.parser import parse_document
from scriptlab.readers import read_episode

FIXTURES = Path(__file__).parent / "fixtures" / "gold_cases"


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


class HumanReviewedGoldCaseTests(unittest.TestCase):
    def test_pending_example_is_not_accepted_as_gold(self):
        case_path = FIXTURES / "pending_review.json"
        case = json.loads(case_path.read_text(encoding="utf-8"))
        self.assertIn("review_status must be 'human_reviewed'",
                      validate_gold_case(case, base_dir=case_path.parent))

    def test_approved_cases_are_parser_regressions(self):
        cases = []
        for case_path in FIXTURES.glob("*.json"):
            case = json.loads(case_path.read_text(encoding="utf-8"))
            if case.get("review_status") == "human_reviewed":
                cases.append((case_path, case))
        if not cases:
            self.skipTest("No human-reviewed gold cases have been approved yet.")

        for case_path, case in cases:
            with self.subTest(case_id=case.get("case_id")):
                self.assertEqual(validate_gold_case(case, base_dir=case_path.parent), [])
                source_path = case_path.parent / case["source_fragment_file"]
                parsed = parse_document(read_episode(EpisodeFile("gold", 0, 0, source_path)))
                for expected in case["expected_elements"]:
                    if expected.get("parser_element_type") == "missing":
                        self.assertFalse(any(
                            normalize(element["text"]) == normalize(expected["original_text"])
                            for element in parsed["elements"]
                        ), f"Expected parser omission for: {expected!r}")
                        continue
                    parser_kind = {
                        "shot_direction": "shot_heading",
                        "supplementary_material": "supplementary_metadata",
                    }.get(
                        expected.get("parser_element_type", expected["element_type"]),
                        expected.get("parser_element_type", expected["element_type"]),
                    )
                    self.assertTrue(any(
                        element["kind"] == parser_kind
                        and normalize(element["text"]) == normalize(expected["original_text"])
                        and (expected.get("parser_speaker", expected.get("speaker")) is None
                             or normalize(element.get("speaker") or "") == normalize(
                                 expected.get("parser_speaker", expected.get("speaker"))))
                        for element in parsed["elements"]
                    ), f"Missing reviewed structure: {expected!r}")
                for relation in case.get("reviewed_relations", []):
                    if relation.get("relation") in {"overlapping", "simultaneous"}:
                        speakers = set(relation["speakers"])
                        rows_by_speaker = {
                            speaker: {
                                turn["parallel_row"] for turn in parsed["dialogue_turns"]
                                if turn["speaker"] == speaker and turn["parallel_row"] is not None
                            }
                            for speaker in speakers
                        }
                        common_rows = set.intersection(*rows_by_speaker.values())
                        shared_cue = any(
                            set(turn["speaker"].split("/")) == speakers
                            for turn in parsed["dialogue_turns"]
                        )
                        self.assertTrue(
                            common_rows or (
                                relation["relation"] == "simultaneous" and shared_cue
                            ),
                            f"Reviewed simultaneous dialogue lacks parallel columns or a shared cue: {relation!r}",
                        )


if __name__ == "__main__":
    unittest.main()
