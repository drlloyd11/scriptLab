"""Deterministic structural parser for TXT and center/BR-based vintage HTML.

Every nonblank normalized source line receives exactly one classification.
The original bytes are never rewritten; each classification points to its source.
"""
from __future__ import annotations

import re
from collections import defaultdict

from .format_detector import (CUE_SUFFIX, INLINE, cue_like, cue_modifiers, detect_format,
                              is_act_end, is_act_heading, is_scene_heading, is_script_end,
                              is_musical_direction, is_shot_heading, is_sound_effect, is_transition,
                              suspected_scene_reason, next_content, unindented_cue_counts,
                              unindented_cue_name)
from .models import Document, Element, Issue, ScriptLine

PAREN = re.compile(r"^\(.*\)$")
CONTINUED = re.compile(r"^\(CONT['’]D\.?\)$", re.I)
EPISODE_CUE_SUFFIX = re.compile(r"\s+\(EP\.\s*\d+\)$", re.I)


def clean_speaker(text: str) -> str:
    name = CUE_SUFFIX.sub("", text.strip().removesuffix(":").rstrip()).upper()
    name = EPISODE_CUE_SUFFIX.sub("", name)
    name = name.replace("’", "'")
    name = re.sub(r"\s*[\\/]\s*", "/", name)
    if name == "BUFFY'S MOM":
        return "JOYCE"
    return re.sub(r"#L$", "#1", name)


def _html_cue_base(text: str) -> str:
    return re.sub(r"\s+\[hand written:[^\]]*\]\s*$", "", text.strip(), flags=re.I)


def _html_cue_like(text: str) -> bool:
    """Centered HTML speaker labels may have a terminal colon (VOICE:).

    Other parts of the document still use their existing conservative rules.
    """
    candidate = _html_cue_base(text).removesuffix(":").rstrip()
    if cue_like(candidate.replace("\\", "/").replace("’", "'")):
        return True
    if re.fullmatch(r"COLONEL\s+McNAMARA", candidate, re.I):
        return True
    if EPISODE_CUE_SUFFIX.search(candidate):
        return bool(cue_like(EPISODE_CUE_SUFFIX.sub("", candidate).strip()))
    cue_name = CUE_SUFFIX.sub("", candidate).strip()
    if cue_name != candidate and re.fullmatch(
        r"[0-9][A-Z0-9 '\-./#,&]*", cue_name, re.I
    ):
        return True
    normalized = candidate.replace("’", "'")
    if re.fullmatch(r"[A-Z][a-z]+", normalized):
        return True
    if re.fullmatch(r"[A-Z][A-Z0-9 '\-./#,&]*#[lI]", normalized):
        return True
    return bool(
        re.fullmatch(r"[0-9][A-Z0-9 '\-./#,&]*", normalized, re.I)
        and len(normalized) <= 55
        and 1 <= len(normalized.split()) <= 6
    )


def _html_cue_speaker(text: str, known_names: set[str]) -> str | None:
    """Recognize a known speaker followed by a descriptive cue parenthetical."""
    if _html_cue_like(text):
        return clean_speaker(_html_cue_base(text)).rstrip(".").strip()
    voice_over = re.fullmatch(
        r"(?P<name>[A-Za-z][A-Za-z0-9 ._'\-/]{0,36}?)\.?\s+"
        r"\(V\.\s*[O0]\.?\)",
        text.strip(),
        re.I,
    )
    if voice_over:
        speaker = voice_over.group("name").rstrip(".").strip().upper()
        if speaker in known_names:
            return speaker
    match = re.fullmatch(
        r"(?P<name>[A-Za-z][A-Za-z0-9 ._'\-/]{0,36}?)\s+\([^()]+\)",
        text.strip(),
    )
    if match:
        speaker = clean_speaker(match.group("name"))
        if speaker in known_names:
            return speaker
    return None


def _html_inline_speaker(text: str, known_names: set[str]) -> str | None:
    """Find an attested speaker cue run together with dialogue on one line."""
    for speaker in sorted(known_names, key=len, reverse=True):
        remainder = text.strip()[len(speaker):] if text.strip().upper().startswith(speaker) else ""
        if (re.match(rf"(?i:{re.escape(speaker)}),\s*br>\s*", text.strip())
                or re.match(rf"(?i:{re.escape(speaker)})\s+[A-Z\"'(]", text.strip())
                or (remainder.startswith(" ") and remainder.rstrip().endswith("-")
                    and remainder.strip()[:1].islower())):
            return speaker
    return None


def _html_dialogue_labels(lines: list[ScriptLine]) -> tuple[dict[int, tuple[str, str | None, list[str]]], list[Issue]]:
    """Classify within explicitly centered HTML blocks, not by indentation.

    A rare case in School Hard has BIG<BR>UGLY<BR>Slayer. Rather than silently
    inventing two speakers, we recognize split names already attested by other
    centered blocks. Unknown group shapes are flagged.
    """
    groups: dict[int, list[ScriptLine]] = defaultdict(list)
    for line in lines:
        if line.layout == "html_center" and line.group_id is not None:
            groups[line.group_id].append(line)

    known_names = set()
    for group in groups.values():
        text = group[0].stripped
        if (len(group) >= 2 and _html_cue_like(text)
                and (text == text.upper() or cue_modifiers(text))):
            known_names.add(clean_speaker(_html_cue_base(group[0].stripped)))

    result: dict[int, tuple[str, str | None, list[str]]] = {}
    issues: list[Issue] = []

    def speaker_with_evidence(text: str, line: ScriptLine) -> tuple[str, list[str]]:
        """Repair an obvious punctuation-only cue typo ONLY if its corrected
        form independently occurs as a speaker in this same document.

        Do not run general fuzzy matching or rewrite the original cue.
        Genuine names like O'BRIEN remain untouched unless OBRIEN is also
        independently attested; the alteration is always reported for review.
        """
        original = clean_speaker(text)
        without_internal_apostrophes = original.replace("'", "").replace("’", "")
        if (original != without_internal_apostrophes and
                without_internal_apostrophes in known_names):
            issues.append(Issue(
                "speaker_spelling_variant",
                f"Speaker cue {text!r} interpreted as {without_internal_apostrophes!r} "
                "because that character is independently attested in this episode; review if intentional.",
                line.line,
                candidates=[original, without_internal_apostrophes],
            ))
            return without_internal_apostrophes, ["Punctuation-only spelling variant of independently attested speaker"]
        return original, []

    pending_speaker: str | None = None
    ordered_groups = list(groups.values())
    for group_index, group in enumerate(ordered_groups):
        first = group[0]
        s = first.stripped
        if pending_speaker is not None:
            if (_html_cue_speaker(s, known_names) is None
                    and not is_scene_heading(s) and not is_transition(s)
                    and not is_act_heading(s) and not is_act_end(s)):
                for line in group:
                    result[line.line] = (
                        "dialogue", pending_speaker,
                        ["Follows a standalone speaker cue in the immediately preceding HTML paragraph"],
                    )
                pending_speaker = None
                continue
            pending_speaker = None
        # These may be centered for typography but are not speakers.
        if is_transition(s) or is_act_end(s) or is_act_heading(s):
            continue
        if is_scene_heading(s):
            continue
        if (any(is_transition(line.stripped) for line in group)
                and _html_cue_speaker(s, known_names) is None):
            for line in group:
                if not is_transition(line.stripped):
                    kind = "shot_heading" if is_shot_heading(line.stripped) else "action"
                    result[line.line] = (
                        kind, None,
                        ["Action or shot direction followed by a centered transition"],
                    )
            continue
        cue_speaker = _html_cue_speaker(s, known_names)
        if cue_speaker is not None and len(group) == 1:
            result[first.line] = (
                "character_cue", cue_speaker,
                ["Standalone known speaker cue in centered HTML paragraph"],
            )
            pending_speaker = cue_speaker
            continue
        if group_index > 0 and s[:1].islower():
            previous_group = ordered_groups[group_index - 1]
            previous_speaker = next(
                (
                    result[line.line][1]
                    for line in reversed(previous_group)
                    if line.line in result and result[line.line][0] == "dialogue"
                ),
                None,
            )
            previous_text = previous_group[-1].stripped.rstrip()
            if (previous_speaker and re.search(
                    r"(?:\b(?:a|an|the|and|but|or|to|of|for|with|is|was)|[-–—])$",
                    previous_text, re.I)):
                for line in group:
                    if PAREN.fullmatch(line.stripped):
                        result[line.line] = (
                            "parenthetical", previous_speaker,
                            ["Parenthetical within continued dialogue across centered HTML paragraphs"],
                        )
                    else:
                        result[line.line] = (
                            "dialogue", previous_speaker,
                            ["Continued dialogue across centered HTML paragraphs"],
                        )
                continue
        if s.casefold() == "(in latin)" and group_index > 0:
            previous_group = ordered_groups[group_index - 1]
            previous_speaker = _html_cue_speaker(
                previous_group[0].stripped, known_names
            )
            if previous_speaker == "ROBED FIGURES":
                result[first.line] = (
                    "parenthetical", previous_speaker,
                    ["Language/delivery direction for Latin chanting"],
                )
                for line in group[1:]:
                    result[line.line] = (
                        "dialogue", previous_speaker,
                        ["Latin chanting; original text preserved without translation"],
                    )
                continue
        if cue_speaker is None or len(group) < 2:
            if PAREN.fullmatch(s):
                result[first.line] = (
                    "parenthetical", None,
                    ["Standalone parenthetical annotation in centered HTML"],
                )
                for line in group[1:]:
                    if s.casefold() == "(translation)":
                        result[line.line] = (
                            "supplementary_metadata", None,
                            ["Reader-only translation of spoken dialogue; not spoken"],
                        )
                        continue
                    result[line.line] = (
                        "unknown", None,
                        ["Centered HTML text following a standalone parenthetical annotation remains unresolved"],
                    )
                if len(group) > 1 and s.casefold() != "(translation)":
                    issues.append(Issue(
                        "ambiguous_html_block",
                        "Unable to classify centered HTML text following a standalone parenthetical annotation.",
                        group[1].line,
                        candidates=["dialogue", "action"],
                    ))
                continue
            inline_speaker = _html_inline_speaker(s, known_names)
            if inline_speaker is not None:
                result[first.line] = (
                    "dialogue", inline_speaker,
                    ["Known speaker cue and dialogue run together on one HTML line"],
                )
                for line in group[1:]:
                    result[line.line] = (
                        "dialogue", inline_speaker,
                        ["Continues after a run-together speaker cue"],
                    )
                if re.search(r",\s*br>", s, re.I):
                    issues.append(Issue(
                        "malformed_html_cue",
                        "Speaker cue is followed by escaped or malformed BR markup; source text was preserved.",
                        first.line,
                        candidates=["dialogue", "source markup error"],
                    ))
                continue
            cue_index = next((
                index for index, line in enumerate(group[1:], 1)
                if line.br_run_before >= 2
                and _html_cue_speaker(line.stripped, known_names) is not None
            ), None)
            if cue_index is not None:
                for line in group[:cue_index]:
                    kind = "shot_heading" if line.stripped.upper().startswith(
                        ("PUSH IN", "CLOSE ON", "ANGLE", "WIDEN", "INSERT")
                    ) else "action"
                    result[line.line] = (
                        kind, None,
                        ["Camera or action direction preceding a new speaker in centered HTML"],
                    )
                inline_group = group[cue_index:]
                inline_result, inline_issues = _html_dialogue_labels(inline_group)
                result.update(inline_result)
                issues.extend(inline_issues)
                continue
            looks_like_run_together_dialogue = any(
                re.match(rf"^{re.escape(name)}\s+as\b", s)
                for name in known_names
            )
            if (len(group) == 1 and not _html_cue_like(s)
                    and not looks_like_run_together_dialogue):
                kind = "shot_heading" if is_shot_heading(s) else "action"
                evidence = (
                    ["Centered HTML camera direction"]
                    if kind == "shot_heading"
                    else ["Standalone action or stage direction in centered HTML"]
                )
                result[first.line] = (kind, None, evidence)
                continue
            if (len(group) > 1
                    and all(not _html_cue_like(line.stripped)
                            and not is_transition(line.stripped)
                            and not PAREN.fullmatch(line.stripped)
                            and any(char.islower() for char in line.stripped)
                            for line in group)):
                for line in group:
                    result[line.line] = (
                        "action", None,
                        ["Narrative prose in a centered HTML block"],
                    )
                continue
            for line in group:
                result[line.line] = ("unknown", None, ["Centered HTML block did not match a known dialogue pattern"])
            issues.append(Issue("ambiguous_html_block", f"Unable to classify centered HTML block: {s!r}",
                                first.line, candidates=["character_cue", "action", "transition"]))
            continue

        if re.fullmatch(
            r"[A-Za-z][A-Za-z0-9 ._'\-/]{0,36}\s+\([^()]+\)",
            s.strip(),
        ):
            speaker, spelling_evidence = cue_speaker, [
                "Known speaker cue followed by descriptive parenthetical"
            ]
        elif cue_speaker != clean_speaker(s):
            speaker, spelling_evidence = cue_speaker, [
                "Known speaker cue with a malformed or nonstandard modifier spelling"
            ]
        elif not _html_cue_like(s):
            speaker, spelling_evidence = cue_speaker, [
                "Known speaker cue followed by descriptive parenthetical"
            ]
        else:
            speaker, spelling_evidence = speaker_with_evidence(s, first)
        name_lines = 1
        if len(group) >= 3 and _html_cue_like(group[1].stripped):
            combined = speaker + " " + clean_speaker(group[1].stripped)
            if combined in known_names:
                speaker = combined
                name_lines = 2
        result[first.line] = ("character_cue", speaker, ["First line in <CENTER> dialogue block"] + spelling_evidence)
        if name_lines == 2:
            result[group[1].line] = ("cue_modifier", speaker, ["Speaker name wrapped across <BR>; verified by other cues"])

        paren_depth = 0
        for line in group[name_lines:]:
            text = line.stripped
            # A double <BR> is a paragraph-like separator in some older
            # Buffy HTML files. Only accept an inline speaker cue when the
            # text is a known speaker name; don't misread capitalized dialogue.
            # E.g. ANYA speech <BR><BR>WILLOW<BR>... inside one <CENTER>.
            if (line.br_run_before >= 2 and _html_cue_like(text)
                    and clean_speaker(text) in known_names):
                speaker, spelling_evidence = speaker_with_evidence(text, line)
                result[line.line] = (
                    "character_cue", speaker,
                    ["Known speaker after consecutive <BR> separators inside same centered block"] + spelling_evidence,
                )
                paren_depth = 0
                continue
            if CONTINUED.fullmatch(text):
                result[line.line] = ("cue_modifier", speaker, ["CONT'D modifier following speaker name"])
            elif paren_depth or text.startswith("("):
                # Delivery parentheticals may wrap across <BR> lines.
                result[line.line] = ("parenthetical", speaker, ["Parenthetical within centered dialogue block"])
                closing_parens = text.count(")")
                # This reviewed source uses a closing brace as a typo.
                if text.casefold() == "(taken aback}":
                    closing_parens = 1
                paren_depth = max(0, paren_depth + text.count("(") - closing_parens)
            else:
                result[line.line] = ("dialogue", speaker, ["Line inside <CENTER> block after speaker cue"])
        if paren_depth:
            issues.append(Issue("open_parenthetical", f"Unclosed parenthetical in centered block: {s!r}",
                                first.line, candidates=["parenthetical", "dialogue"]))
    return result, issues



def _dialogue_turns(elements: list[Element]) -> list[dict]:
    """Reconstruct an utterance from consecutive dialogue/parenthetical lines.

    Keep ordered individual segments so delivery cues never masquerade as words.
    The full speech is a convenience view, not a replacement for source lines.
    """
    turns: list[dict] = []
    current: dict | None = None

    def flush() -> None:
        nonlocal current
        if current is not None and any(s["kind"] == "dialogue" for s in current["segments"]):
            current["text"] = " ".join(s["text"] for s in current["segments"] if s["kind"] == "dialogue")
            turns.append(current)
        current = None

    for element in elements:
        kind = element.kind
        if kind == "character_cue":
            flush()
            current = {
                "speaker": element.speaker,
                "cue": element.text,
                "modifiers": cue_modifiers(element.text),
                "act_index": element.act_index,
                "scene_index": element.scene_index,
                "start_line": element.line,
                "end_line": element.line,
                "segments": [],
            }
        elif kind in {"dialogue", "parenthetical", "cue_modifier"}:
            if current is None or element.speaker != current["speaker"]:
                if kind != "dialogue":
                    flush()
                    continue
                flush()
                current = {
                    "speaker": element.speaker, "cue": None, "modifiers": [],
                    "act_index": element.act_index, "scene_index": element.scene_index,
                    "start_line": element.line, "end_line": element.line, "segments": [],
                }
            current["end_line"] = element.line
            if kind != "cue_modifier":
                current["segments"].append({"kind": kind, "line": element.line,
                                             "source_line": element.source_line, "text": element.text})
            # Transcript NAME: text: exclude the cue prefix from the speech view.
            if kind == "dialogue" and element.text.count(":") and current["cue"] is None:
                prefix = INLINE.fullmatch(element.text)
                if prefix and clean_speaker(prefix.group("name")) == element.speaker:
                    current["segments"][-1]["text"] = prefix.group("words")
        else:
            flush()
    flush()
    return turns


def parse_document(document: Document) -> dict:
    lines = document.lines
    profile = detect_format(lines)
    flat_speakers = (
        {name for name, count in unindented_cue_counts(lines).items() if count >= 2}
        if profile.mode == "screenplay_unindented" else set()
    )
    elements: list[Element] = []
    issues: list[Issue] = []
    # Do not treat promotional links or other website material appended after
    # END OF SHOW / END OF EPISODE as dialogue, regardless of CENTER markup.
    # The source lines remain intact and explicitly classified below.
    end_position = next((idx for idx, line in enumerate(lines)
                         if is_script_end(line.stripped)), None)
    active_lines = lines if end_position is None else lines[:end_position + 1]
    html_labels, html_issues = _html_dialogue_labels(active_lines) if profile.mode == "html_center" else ({}, [])
    front_matter_end = next(
        (index for index, line in enumerate(active_lines)
         if is_act_heading(line.stripped) or is_scene_heading(line.stripped)),
        None,
    )
    front_matter_lines = (
        {line.line for line in active_lines[:front_matter_end]}
        if front_matter_end is not None else set()
    )
    html_issues = [
        issue for issue in html_issues
        if not (issue.kind == "ambiguous_html_block" and issue.line in front_matter_lines)
    ]
    issues.extend(html_issues)
    current_speaker: str | None = None
    scene = 0
    act = 0
    in_dialogue = False
    script_finished = False

    for i, line in enumerate(lines):
        s = line.stripped
        if not s:
            if profile.mode == "screenplay_unindented":
                current_speaker = None
                in_dialogue = False
            continue

        def append(kind: str, speaker: str | None = None, evidence: list[str] | None = None) -> None:
            elements.append(Element(line.line, line.source_line, kind, s, scene, speaker, evidence or [], act))

        if script_finished:
            append("supplementary_metadata", evidence=["Content follows final episode marker"])
            continue

        if is_act_heading(s):
            act += 1
            append("act_heading", evidence=["Explicit teaser/act heading"])
            current_speaker = None
            in_dialogue = False
            continue
        if is_act_end(s):
            append("act_end", evidence=["Explicit episode ending" if is_script_end(s) else "Explicit end-of-act heading"])
            if is_script_end(s):
                script_finished = True
            current_speaker = None
            in_dialogue = False
            continue
        if is_scene_heading(s):
            scene += 1
            append("scene_heading", evidence=["Matches scene heading syntax"])
            current_speaker = None
            in_dialogue = False
            continue
        suspected_reason = suspected_scene_reason(s)
        if suspected_reason is not None:
            # A provisional boundary prevents subsequent dialogue from being
            # silently attached to the preceding scene. Do not rewrite the
            # heading or present it as a confirmed scene.
            scene += 1
            append("suspected_scene_heading", evidence=[suspected_reason, "Provisional boundary; requires source review"])
            issues.append(Issue("suspected_scene_heading", f"{suspected_reason}: {s!r}", line.line,
                                candidates=["scene_heading", "action", "shot_heading"]))
            current_speaker = None
            in_dialogue = False
            continue
        if is_transition(s):
            append("transition", evidence=["Matches explicit transition syntax"])
            current_speaker = None
            in_dialogue = False
            continue

        if profile.mode == "screenplay_unindented" and line.line in front_matter_lines:
            append("metadata", evidence=["Title, date, or credit text before first act/scene"])
            continue

        if line.line in html_labels:
            kind, speaker, evidence = html_labels[line.line]
            if kind == "unknown" and line.line in front_matter_lines:
                append("metadata", evidence=["Title, date, or credit text before first act/scene"])
                current_speaker = None
                in_dialogue = False
                continue
            append(kind, speaker, evidence)
            current_speaker = None
            in_dialogue = False
            continue

        # Vintage HTML: <P> contains shot descriptions and action; do not
        # mistake a left-aligned character name for a speaker cue.
        if line.layout in {"html_paragraph", "html_text"} and profile.mode == "html_center":
            if is_sound_effect(s):
                append("sound_effect", evidence=["Standalone emphatic sound cue outside centered dialogue"])
            elif is_shot_heading(s):
                append("shot_heading", evidence=["All-caps shot/subject line outside centered dialogue"])
            elif is_musical_direction(s):
                append("musical_direction", evidence=["Explicitly discordant musical note or chord description"])
            elif scene == 0 and act == 0:
                append("metadata", evidence=["Title, date, or credit text before first act/scene"])
            else:
                append("action", evidence=["Left-aligned HTML prose outside centered dialogue"])
            continue

        # TXT or <PRE> with ASCII indentation, or transcript-style NAME: text.
        inline = INLINE.fullmatch(s)
        if inline and (profile.mode == "transcript" or inline.group("name").isupper()):
            speaker = clean_speaker(inline.group("name"))
            append("dialogue", speaker, ["Inline NAME: dialogue structure"])
            current_speaker = None
            in_dialogue = False
            continue

        nxt = next_content(lines, i + 1)
        looks_cue = bool(cue_like(s) and nxt is not None and
                         not is_scene_heading(nxt.stripped) and not is_transition(nxt.stripped))
        flat_name = unindented_cue_name(s) if profile.mode == "screenplay_unindented" else None
        flat_cue = bool(flat_name and flat_name in flat_speakers and looks_cue)
        strong_cue = bool(looks_cue and line.indent >= 6 and
                          nxt.indent <= line.indent - 2 and
                          (nxt.indent >= 3 or PAREN.fullmatch(nxt.stripped)))
        profile_cue = bool(looks_cue and profile.cue_indent is not None and
                           abs(line.indent - profile.cue_indent) <= 3 and
                           nxt.indent < line.indent and
                           (nxt.indent >= 3 or PAREN.fullmatch(nxt.stripped)))
        if strong_cue or profile_cue or flat_cue:
            current_speaker = clean_speaker(s)
            in_dialogue = True
            evidence = (
                ["Repeated uppercase speaker cue in an unindented screenplay"]
                if flat_cue else ["Indented uppercase name followed by dialogue"]
            )
            append("character_cue", current_speaker, evidence)
            continue

        if profile.mode == "screenplay_unindented" and flat_name:
            append("unknown", evidence=["Unrepeated uppercase cue candidate in unindented screenplay"])
            issues.append(Issue("ambiguous_cue", f"Unconfirmed speaker cue? {s!r}", line.line,
                                candidates=["character_cue", "action"]))
            current_speaker = None
            in_dialogue = False
            continue

        if current_speaker is not None and PAREN.fullmatch(s) and in_dialogue:
            append("parenthetical", current_speaker, ["Parenthetical inside speaker block"])
            continue

        if profile.mode == "screenplay_unindented" and current_speaker is not None and in_dialogue:
            append("dialogue", current_speaker, ["Follows an unindented speaker cue"])
            continue

        if current_speaker is not None and in_dialogue:
            indent_threshold = max(3, (profile.dialogue_indent or 4) - 3)
            if line.indent >= indent_threshold and not looks_cue:
                append("dialogue", current_speaker, ["Follows an indented character cue"])
                continue
            current_speaker = None
            in_dialogue = False

        if is_sound_effect(s):
            append("sound_effect", evidence=["Standalone emphatic sound cue"])
            continue

        if is_musical_direction(s):
            append("musical_direction", evidence=["Explicitly discordant musical note or chord description"])
            continue

        if looks_cue and line.indent <= 5 and nxt and not cue_like(nxt.stripped):
            append("unknown", evidence=["Cue-like text without reliable speaker indentation"])
            issues.append(Issue("ambiguous_cue", f"Speaker cue or action? {s!r}", line.line,
                                candidates=["character_cue", "action"]))
        elif looks_cue and line.indent > 5 and not strong_cue:
            append("unknown", evidence=["Cue-like line does not match detected indentation"])
            issues.append(Issue("ambiguous_cue", f"Nonstandard speaker cue? {s!r}", line.line,
                                candidates=["character_cue", "action"]))
        else:
            append("action", evidence=["Not recognized as heading, transition or dialogue"])

    turns = _dialogue_turns(elements)
    for turn in turns:
        origin = lines[turn["start_line"] - 1]
        turn["parallel_row"] = origin.parallel_row
        turn["parallel_column"] = origin.parallel_column

    return {
        "schema_version": 3,
        "episode": {
            "series": document.episode.series, "season": document.episode.season,
            "episode": document.episode.episode, "key": document.episode.key,
            "source_type": document.episode.source_type,
            "path": str(document.episode.path), "sha256": document.source_hash,
            "encoding": document.encoding,
        },
        "profile": profile.to_dict(),
        "lines": [{"line": l.line, "source_line": l.source_line, "text": l.text,
                   "layout": l.layout, "group_id": l.group_id,
                   "parallel_row": l.parallel_row, "parallel_column": l.parallel_column,
                   "br_run_before": l.br_run_before} for l in lines],
        "elements": [e.to_dict() for e in elements],
        "dialogue_turns": turns,
        "issues": [issue.to_dict() for issue in issues] + [
            Issue("reader_warning", w).to_dict() for w in document.reader_warnings
        ],
    }
