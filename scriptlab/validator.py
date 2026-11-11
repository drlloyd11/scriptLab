"""Integrity checks are independent of LLMs and script-format heuristics."""
from __future__ import annotations

from collections import Counter
from .models import Issue

KINDS = {"metadata", "supplementary_metadata", "act_heading", "act_end", "scene_heading", "suspected_scene_heading", "shot_heading", "sound_effect", "musical_direction", "transition", "character_cue", "cue_modifier", "dialogue", "parenthetical", "action", "unknown"}


def validate_parsed(parsed: dict) -> list[dict]:
    issues: list[Issue] = []
    lines = {line["line"]: line for line in parsed["lines"]}
    counts = Counter(e["line"] for e in parsed["elements"])
    for line_num, line in lines.items():
        if line["text"].strip() and counts[line_num] != 1:
            issues.append(Issue("line_coverage", f"Nonblank line classified {counts[line_num]} times; expected exactly once",
                                line_num, severity="error"))
        if not line["text"].strip() and counts[line_num]:
            issues.append(Issue("blank_coverage", "Blank line unexpectedly classified", line_num, severity="error"))
    for element in parsed["elements"]:
        n = element["line"]
        if n not in lines:
            issues.append(Issue("out_of_range", f"Element points to missing normalized line {n}", n, severity="error"))
        elif element["text"] != lines[n]["text"].strip():
            issues.append(Issue("text_integrity", "Element text diverged from normalized source line", n, severity="error"))
        if element["kind"] not in KINDS:
            issues.append(Issue("invalid_kind", f"Unknown kind {element['kind']}", n, severity="error"))
        if element["kind"] == "dialogue" and not element["speaker"]:
            issues.append(Issue("unattributed_dialogue", "Dialogue has no speaker", n, severity="error"))
    # Dialogue turns are derived views. Ensure no spoken source line was lost,
    # duplicated, or reassigned to a different speaker during reconstruction.
    if "dialogue_turns" in parsed:
        dialogue = {e["line"]: e for e in parsed["elements"] if e["kind"] == "dialogue"}
        turn_lines = Counter()
        for turn in parsed["dialogue_turns"]:
            for part in turn["segments"]:
                if part["kind"] != "dialogue":
                    continue
                number = part["line"]
                turn_lines[number] += 1
                if number not in dialogue:
                    issues.append(Issue("turn_integrity", "Dialogue turn points to a non-dialogue line",
                                        number, severity="error"))
                elif dialogue[number]["speaker"] != turn["speaker"]:
                    issues.append(Issue("turn_speaker", "Reconstructed turn speaker differs from source label",
                                        number, severity="error"))
        for number in dialogue:
            if turn_lines[number] != 1:
                issues.append(Issue("turn_coverage", f"Dialogue appears in {turn_lines[number]} turns, expected 1",
                                    number, severity="error"))
    return [issue.to_dict() for issue in issues]
