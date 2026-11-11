"""Verifier-pilot checks run fully offline; no Ollama service required."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scriptlab.cli import run
from scriptlab.comparator import compare_labels, independent_llm_labels
from scriptlab.llm import OllamaError


class VerificationPilotTests(unittest.TestCase):
    def setUp(self):
        self.parsed = {
            "episode": {"key": "buffy/S03E15", "sha256": "abcdef123"},
            "lines": [
                {"line": 1, "text": "INT. ROOM - NIGHT", "layout": "html_paragraph", "group_id": 2},
                {"line": 2, "text": "BUFFY", "layout": "html_center", "group_id": 3},
                {"line": 3, "text": "Hello", "layout": "html_center", "group_id": 3},
                {"line": 4, "text": "WILLOW", "layout": "html_center", "group_id": 4},
                {"line": 5, "text": "Hey", "layout": "html_center", "group_id": 4},
            ],
            "elements": [
                {"line": 1, "kind": "scene_heading", "speaker": None},
                {"line": 2, "kind": "character_cue", "speaker": "BUFFY"},
                {"line": 3, "kind": "dialogue", "speaker": "BUFFY"},
                {"line": 4, "kind": "character_cue", "speaker": "WILLOW"},
                {"line": 5, "kind": "dialogue", "speaker": "WILLOW"},
            ],
        }

    def test_scoped_targets_dont_create_false_omission_errors(self):
        result = compare_labels(self.parsed, {3: {"kind": "dialogue", "speaker": "BUFFY"}},
                                "fake", target_lines={3})
        self.assertEqual(result["requested_lines"], 1)
        self.assertEqual(result["compared_lines"], 1)
        self.assertEqual(result["unreviewed_lines"], 0)
        self.assertEqual(result["llm_failures"], [])
        self.assertEqual(result["source_sha256"], "abcdef123")

    def test_llm_only_receives_selected_targets_not_python_labels(self):
        def stub(system, user, model, base_url):
            self.assertIn("exactly these target line numbers: [3]", user)
            self.assertIn("[2] html_center", user)  # context only
            self.assertNotIn("python_kind", user)
            self.assertNotIn('"kind": "dialogue"', user)
            return {"labels": [{"line": 3, "kind": "dialogue", "speaker": "BUFFY"}]}

        labels, failures = independent_llm_labels(self.parsed, "fake", ask=stub,
                                                   line_start=3, line_end=3)
        self.assertEqual(labels, {3: {"kind": "dialogue", "speaker": "BUFFY"}})
        self.assertEqual(failures, [])

    def test_cli_writes_scoped_audit_and_preserves_model_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            parsed_path = Path(tmp) / "episode.json"
            parsed_path.write_text(json.dumps(self.parsed), encoding="utf-8")
            prefix = Path(tmp) / "pilot"
            with patch("scriptlab.cli.independent_llm_labels", return_value=(
                    {3: {"kind": "dialogue", "speaker": "WILLOW"}}, [])) as method:
                code = run(["compare", "--parsed", str(parsed_path), "--model", "fake",
                            "--line-start", "3", "--line-end", "3", "--out", str(prefix)])
            self.assertEqual(code, 0)
            self.assertEqual(method.call_args.kwargs["line_start"], 3)
            data = json.loads(Path(str(prefix) + ".comparison.json").read_text())
            labels = json.loads(Path(str(prefix) + ".llm_labels.json").read_text())
            self.assertEqual(data["requested_lines"], 1)
            self.assertEqual(len(data["disagreements"]), 1)
            self.assertEqual(labels["labels"][0]["speaker"], "WILLOW")
            self.assertTrue(Path(str(prefix) + ".comparison.md").exists())

    def test_check_ollama_preflight_success_and_missing_model(self):
        with patch("scriptlab.cli.list_ollama_models", return_value=["qwen3:8b"]):
            self.assertEqual(run(["check-ollama", "--model", "qwen3:8b"]), 0)
            self.assertEqual(run(["check-ollama", "--model", "missing"]), 2)

    def test_check_ollama_preflight_handles_unreachable_service(self):
        with patch("scriptlab.cli.list_ollama_models", side_effect=OllamaError("not running")):
            self.assertEqual(run(["check-ollama", "--model", "qwen3:8b"]), 2)


if __name__ == "__main__":
    unittest.main()
