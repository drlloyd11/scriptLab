"""Offline tests for raw-HTML verification, source evidence, and gold-case validation."""
from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

from scriptlab.cli import run
from scriptlab.html_verifier import (
    HTML_RESPONSE_SCHEMA,
    _ask_html,
    compare_raw_html,
    select_html_fragments,
    validate_gold_case,
)
from scriptlab.models import EpisodeFile
from scriptlab.parser import parse_document
from scriptlab.readers import read_episode


FIXTURE_HTML = """<html>
<head><title>Fixture</title></head>
<body>
<center><font>
BUFFY<br>
Hello &amp; goodbye.
</font></center>
<center><font>
WILLOW<br>
I heard you.
</font></center>
<p>Buffy looks toward the door.</p>
</body>
</html>"""


class RawHtmlVerifierTests(unittest.TestCase):
    def parse_fixture(self, directory: str, html: str = FIXTURE_HTML) -> tuple[Path, dict]:
        path = Path(directory) / "S02E03.html"
        path.write_text(html, encoding="utf-8")
        parsed = parse_document(read_episode(EpisodeFile("buffy", 2, 3, path)))
        return path, parsed

    def test_fragment_selector_preserves_raw_markup_overlap_and_pilot_offsets(self):
        source = "<html>\n<body>\n<center>" + ("x" * 280) + "<br></center>\n</body>\n</html>"
        fragments = select_html_fragments(source, max_chars=256, overlap_chars=40)
        self.assertGreater(len(fragments), 1)
        self.assertTrue(all(len(fragment.html) <= 256 for fragment in fragments))
        self.assertTrue(any("<center>" in fragment.html for fragment in fragments))
        self.assertLess(fragments[1].start_offset, fragments[0].end_offset)
        pilot = select_html_fragments(source, 256, 40, start_offset=10, end_offset=80)
        self.assertEqual(len(pilot), 1)
        self.assertEqual(pilot[0].html, source[10:80])

    def test_raw_html_is_the_only_interpretation_input_and_aligns_with_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path, parsed = self.parse_fixture(directory)
            raw_html = path.read_text(encoding="utf-8")

            def fake(system, user, model, base_url):
                self.assertIn("<center><font>", user)
                self.assertIn("Hello &amp; goodbye.", user)
                self.assertNotIn("html_center", user)
                self.assertNotIn("python_kind", user)
                self.assertNotIn("character_cue / BUFFY", user)
                return {"elements": [
                    {"element_type": "character_cue", "original_text": "BUFFY", "speaker": "BUFFY"},
                    {"element_type": "dialogue", "original_text": "Hello & goodbye.", "speaker": "BUFFY"},
                    {"element_type": "character_cue", "original_text": "WILLOW", "speaker": "WILLOW"},
                    {"element_type": "dialogue", "original_text": "I heard you.", "speaker": "WILLOW"},
                ]}

            result = compare_raw_html(raw_html, parsed, path, parsed["episode"]["sha256"], ask=fake)
            self.assertEqual(result["elements_examined"], 4)
            self.assertEqual(result["agreement_count"], 4)
            self.assertEqual(result["classification_disagreements"], [])
            self.assertEqual(
                result["integrity_checks_scope"],
                "whole source document (independent of the selected Ollama pilot range)",
            )
            self.assertIsNone(result["accuracy_against_human_reviewed_cases"])
            self.assertTrue(all(item["ollama"]["original_html_evidence"] for item in result["agreements"]))

    def test_classification_disagreement_and_omissions_are_not_agreement(self):
        with tempfile.TemporaryDirectory() as directory:
            path, parsed = self.parse_fixture(directory)
            raw_html = path.read_text(encoding="utf-8")

            def fake(system, user, model, base_url):
                return {"elements": [
                    {"element_type": "action", "original_text": "Hello & goodbye.", "speaker": None},
                    {"element_type": "dialogue", "original_text": "not in source", "speaker": "BUFFY"},
                ]}

            result = compare_raw_html(raw_html, parsed, path, parsed["episode"]["sha256"], ask=fake)
            self.assertEqual(len(result["classification_disagreements"]), 1)
            self.assertTrue(result["llm_failures_or_omissions"])
            self.assertGreater(result["items_needing_human_review"], 0)

    def test_repeated_quote_can_be_aligned_by_valid_fragment_source_span(self):
        source = """<html>
<body>
<center><font>
BUFFY<br>
Hello.
</font></center>
<center><font>
BUFFY<br>
Goodbye.
</font></center>
</body>
</html>"""
        with tempfile.TemporaryDirectory() as directory:
            path, parsed = self.parse_fixture(directory, source)
            raw_html = path.read_text(encoding="utf-8")

            def fake(system, user, model, base_url):
                fragment = user.split("BEGIN ORIGINAL HTML\n", 1)[1].split("\nEND ORIGINAL HTML", 1)[0]
                entries = []
                cursor = 0
                while (cue_start := fragment.find("BUFFY", cursor)) >= 0:
                    entries.append({
                        "element_type": "character_cue",
                        "original_text": "BUFFY",
                        "speaker": "BUFFY",
                        "source_span": {"start": cue_start, "end": cue_start + len("BUFFY")},
                    })
                    cursor = cue_start + len("BUFFY")
                return {"elements": entries}

            result = compare_raw_html(raw_html, parsed, path, parsed["episode"]["sha256"], ask=fake)
            self.assertEqual(result["agreement_count"], 2)
            self.assertFalse(result["llm_failures_or_omissions"])

    def test_overlapping_conflicting_speakers_are_not_silently_deduplicated(self):
        source = "<html><body>" + ("x" * 170) + "<center><font>BUFFY<br>Hello.</font></center>" + ("y" * 350) + "</body></html>"
        with tempfile.TemporaryDirectory() as directory:
            path, parsed = self.parse_fixture(directory, source)
            raw_html = path.read_text(encoding="utf-8")
            model_labels = {"1": "BUFFY", "2": "WILLOW", "3": "BUFFY"}

            def fake(system, user, model, base_url):
                fragment_id = user.split("Fragment id: ", 1)[1].split(";", 1)[0]
                fragment = user.split("BEGIN ORIGINAL HTML\n", 1)[1].split("\nEND ORIGINAL HTML", 1)[0]
                if "BUFFY" not in fragment:
                    return {"elements": []}
                start = fragment.index("BUFFY")
                return {"elements": [{
                    "element_type": "character_cue",
                    "original_text": "BUFFY",
                    "speaker": model_labels.get(fragment_id, "BUFFY"),
                    "source_span": {"start": start, "end": start + len("BUFFY")},
                }]}

            result = compare_raw_html(
                raw_html, parsed, path, parsed["episode"]["sha256"],
                max_chars=256, overlap_chars=100, ask=fake,
            )
            self.assertTrue(result["uncertain_alignments"])
            self.assertFalse(result["agreements"])
            self.assertTrue(any("conflicting speaker" in item["reason"]
                                for item in result["uncertain_alignments"]))

    def test_zero_unique_alignments_have_no_agreement_rate(self):
        with tempfile.TemporaryDirectory() as directory:
            path, parsed = self.parse_fixture(directory)
            raw_html = path.read_text(encoding="utf-8")
            result = compare_raw_html(
                raw_html, parsed, path, parsed["episode"]["sha256"],
                ask=lambda *args: {"elements": []},
            )
            self.assertIsNone(result["model_agreement_rate"])

    def test_raw_client_sends_schema_and_legacy_client_keeps_json_mode(self):
        from scriptlab.llm import ask_ollama
        with patch("scriptlab.llm.request.urlopen") as transport:
            transport.return_value.__enter__.return_value.read.return_value = (
                b'{"message":{"content":"{\\"elements\\":[]}"}}'
            )
            _ask_html("system", "raw HTML", "fake", "http://127.0.0.1:11434")
            payload = json.loads(transport.call_args.args[0].data)
            self.assertEqual(payload["format"], HTML_RESPONSE_SCHEMA)
            ask_ollama("system", "legacy", "fake")
            self.assertEqual(json.loads(transport.call_args.args[0].data)["format"], "json")

    def test_tag_separated_cues_dialogue_and_duplicate_visible_quotes(self):
        source = (
            '<CENTER>VOICE (O.C.)<BR><I>Listen</I> &amp; look!</CENTER>\n'
            '<CENTER>VOICE (cont\'d; O.C.)<BR><B>Listen</B> &amp; look!</CENTER>'
        )
        entries = [
            {"element_type": "character_cue", "original_text": "VOICE (O.C.)", "speaker": "VOICE (O.C.)"},
            {"element_type": "character_cue", "original_text": "VOICE (cont'd; O.C.)", "speaker": "VOICE (cont'd; O.C.)"},
        ]
        line_start = 0
        for line in source.splitlines(keepends=True):
            entries.append({
                "element_type": "dialogue", "original_text": "Listen & look!",
                "speaker": "VOICE", "source_span": {"start": line_start, "end": line_start + len(line)},
            })
            line_start += len(line)
        with tempfile.TemporaryDirectory() as directory:
            path, parsed = self.parse_fixture(directory, source)

            def fake(system, user, model, base_url):
                self.assertIn("NO tags", system)
                self.assertIn("RAW HTML", system)
                self.assertIn("Raw-line ranges [start,end)", user)
                return {"elements": entries}

            result = compare_raw_html(source, parsed, path, parsed["episode"]["sha256"], ask=fake)
            self.assertEqual(result["elements_examined"], 4)
            self.assertEqual(result["llm_failures_or_omissions"], [])
            quotes = [item["ollama"] for item in
                      result["agreements"] + result["classification_disagreements"] + result["uncertain_alignments"]]
            dialogues = [item for item in quotes if item["element_type"] == "dialogue"]
            self.assertEqual(len(dialogues), 2)
            self.assertNotEqual(dialogues[0]["source_span"]["start_char"],
                                dialogues[1]["source_span"]["start_char"])

    def test_markup_quotes_bad_offsets_and_ambiguous_duplicates_fail_validation(self):
        source = "<center>VOICE<br>Listen!</center>\n<center>VOICE<br>Listen!</center>"
        responses = [
            {"element_type": "dialogue", "original_text": "VOICE<BR>Listen!"},
            {"element_type": "dialogue", "original_text": "Listen!"},
            {"element_type": "dialogue", "original_text": "Listen!",
             "source_span": {"start": 0, "end": len(source)}},
            {"element_type": "dialogue", "original_text": "Listen!",
             "source_span": {"start": source.index("Listen!"), "end": source.index("Listen!") + 3}},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path, parsed = self.parse_fixture(directory, source)
            result = compare_raw_html(source, parsed, path, parsed["episode"]["sha256"],
                                      ask=lambda *args: {"elements": responses})
            self.assertEqual(result["elements_examined"], 0)
            self.assertEqual(result["verification_status"], "failed")
            self.assertTrue(any("HTML markup" in failure for failure in result["llm_failures_or_omissions"]))
            self.assertTrue(any("all returned items" in failure for failure in result["llm_failures_or_omissions"]))

    def test_duplicate_null_spans_get_one_raw_location_only_repair(self):
        source = "<center>VOICE<br>Listen!</center>\n<center>VOICE<br>Listen!</center>"
        first = {"elements": [
            {"element_type": "dialogue", "original_text": "Listen!", "speaker": "VOICE", "source_span": None},
            {"element_type": "dialogue", "original_text": "Listen!", "speaker": "VOICE", "source_span": None},
        ]}
        repaired = {"elements": []}
        cursor = 0
        while (start := source.find("Listen!", cursor)) >= 0:
            repaired["elements"].append({
                "element_type": "dialogue", "original_text": "Listen!", "speaker": "VOICE",
                "source_span": {"start": start, "end": start + len("Listen!")},
            })
            cursor = start + len("Listen!")
        with tempfile.TemporaryDirectory() as directory:
            path, parsed = self.parse_fixture(directory, source)
            ask = unittest.mock.Mock(side_effect=[first, repaired])
            result = compare_raw_html(source, parsed, path, parsed["episode"]["sha256"], ask=ask)
            self.assertEqual(ask.call_count, 2)
            retry_prompt = ask.call_args.args[1]
            self.assertIn("candidate_raw_spans", retry_prompt)
            self.assertNotIn("python_kind", retry_prompt)
            self.assertNotIn("html_center", retry_prompt)
            self.assertEqual(result["elements_examined"], 2)
            self.assertFalse(result["llm_failures_or_omissions"])
            self.assertEqual(len(result["validation_retries"]), 1)

    def test_duplicate_elements_cannot_reuse_one_occurrence_in_same_fragment(self):
        source = "<center>VOICE<br>Listen!</center>\n<center>VOICE<br>Listen!</center>"
        start = source.index("Listen!")
        item = {"element_type": "dialogue", "original_text": "Listen!", "speaker": "VOICE",
                "source_span": {"start": start, "end": start + len("Listen!")}}
        with tempfile.TemporaryDirectory() as directory:
            path, parsed = self.parse_fixture(directory, source)
            result = compare_raw_html(source, parsed, path, parsed["episode"]["sha256"],
                                      ask=lambda *args: {"elements": [item, dict(item)]})
            self.assertEqual(result["verification_status"], "partial")
            self.assertTrue(any("reuses one source occurrence" in failure
                                for failure in result["llm_failures_or_omissions"]))

    def test_cli_rejected_markup_is_failure_not_zero_element_success(self):
        with tempfile.TemporaryDirectory() as directory:
            path, _ = self.parse_fixture(directory)
            from scriptlab.html_verifier import compare_raw_html as actual_compare

            def compare_with_invalid_response(*args):
                return actual_compare(*args, ask=lambda *a: {"elements": [
                    {"element_type": "dialogue", "original_text": "BUFFY<BR>Hello & goodbye."},
                ]})

            prefix = Path(directory) / "invalid"
            with patch("scriptlab.cli.compare_raw_html", side_effect=compare_with_invalid_response):
                code = run(["verify-html", "--script", str(path), "--out", str(prefix)])
            self.assertEqual(code, 2)
            result = json.loads(Path(str(prefix) + ".verification.json").read_text(encoding="utf-8"))
            self.assertEqual(result["verification_status"], "failed")
            self.assertEqual(result["elements_examined"], 0)

    def test_normalized_speaker_is_compared_and_explicit_uncertainty_never_agrees(self):
        source = "<html>\n<body>\n<center><font>\nBUFFY (V.0.)<br>\nI'm here.\n</font></center>\n</body>\n</html>"
        with tempfile.TemporaryDirectory() as directory:
            path, parsed = self.parse_fixture(directory, source)
            raw_html = path.read_text(encoding="utf-8")

            def response(normalized_speaker, uncertainty=None):
                return {"elements": [{
                    "element_type": "character_cue",
                    "original_text": "BUFFY (V.0.)",
                    "speaker": "BUFFY (V.0.)",
                    "normalized_speaker": normalized_speaker,
                    "uncertainty": uncertainty,
                }]}

            normalized = compare_raw_html(
                raw_html, parsed, path, parsed["episode"]["sha256"],
                ask=lambda *args: response("BUFFY"),
            )
            self.assertEqual(normalized["agreement_count"], 1)

            wrong_identity = compare_raw_html(
                raw_html, parsed, path, parsed["episode"]["sha256"],
                ask=lambda *args: response("WILLOW"),
            )
            self.assertEqual(len(wrong_identity["classification_disagreements"]), 1)

            uncertain = compare_raw_html(
                raw_html, parsed, path, parsed["episode"]["sha256"],
                ask=lambda *args: response("BUFFY", "cue identity uncertain"),
            )
            self.assertEqual(uncertain["agreement_count"], 0)
            self.assertTrue(any("explicitly marked" in item["reason"]
                                for item in uncertain["uncertain_alignments"]))

    def test_integrity_inventory_reports_lost_visible_text_and_retained_double_br(self):
        with tempfile.TemporaryDirectory() as directory:
            double_br_html = FIXTURE_HTML.replace(
                "BUFFY<br>\nHello", "BUFFY<br>\n<br>\nHello"
            )
            path, parsed = self.parse_fixture(directory, double_br_html)
            raw_html = path.read_text(encoding="utf-8")
            for line in parsed["lines"]:
                if line["text"] == "Hello & goodbye.":
                    line["br_run_before"] = 0  # simulate a lost meaningful source boundary
            parsed["lines"] = [line for line in parsed["lines"]
                               if line["text"] != "I heard you."]

            def empty(system, user, model, base_url):
                return {"elements": [{"element_type": "unknown", "original_text": "BUFFY"}]}

            result = compare_raw_html(raw_html, parsed, path, parsed["episode"]["sha256"], ask=empty)
            kinds = {finding["check"] for finding in result["extraction_disagreements"]}
            self.assertIn("visible_text_missing", kinds)
            self.assertIn("br_boundary_inventory", kinds)
            self.assertTrue(all(finding.get("original_html_evidence") for finding in result["extraction_disagreements"]))

    def test_human_reviewed_gold_case_requires_provenance_and_expected_structure(self):
        good = {
            "case_id": "synthetic-center-turn",
            "review_status": "human_reviewed",
            "reviewer": "reviewer",
            "reference_location": "synthetic fixture line 4",
            "source_fragment": "<center>BUFFY<br>Hello.</center>",
            "expected_elements": [
                {"element_type": "character_cue", "original_text": "BUFFY", "speaker": "BUFFY"},
                {"element_type": "dialogue", "original_text": "Hello.", "speaker": "BUFFY"},
            ],
        }
        self.assertEqual(validate_gold_case(good), [])
        good["review_status"] = "pending_review"
        self.assertIn("review_status must be 'human_reviewed'", validate_gold_case(good))

    def test_verify_html_cli_writes_both_report_formats(self):
        with tempfile.TemporaryDirectory() as directory:
            path, parsed = self.parse_fixture(directory)
            raw_html = path.read_text(encoding="utf-8")
            prefix = Path(directory) / "pilot"

            def fake(system, user, model, base_url):
                return {"elements": [
                    {"element_type": "character_cue", "original_text": "BUFFY", "speaker": "BUFFY"},
                    {"element_type": "dialogue", "original_text": "Hello & goodbye.", "speaker": "BUFFY"},
                ]}

            from scriptlab.html_verifier import compare_raw_html as actual_compare

            def compare_with_stub(*args):
                return actual_compare(*args, ask=fake)

            with patch("scriptlab.cli.compare_raw_html", side_effect=compare_with_stub):
                code = run(["verify-html", "--script", str(path), "--model", "offline-stub",
                            "--out", str(prefix), "--start-line", "5", "--end-line", "6"])
            self.assertEqual(code, 0)
            self.assertTrue(Path(str(prefix) + ".verification.json").exists())
            self.assertIn("Agreement is not proof of accuracy",
                          Path(str(prefix) + ".verification.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
