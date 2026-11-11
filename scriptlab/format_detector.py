"""Discover script layout without conflating dialogue, shot headings and scenes."""
from __future__ import annotations

import re
import statistics
from collections import Counter
from dataclasses import asdict, dataclass
from .models import ScriptLine

SCENE = re.compile(
    r"(?i)^(?:(?:INT|EXT)\s*(?:\.\s*|/\s*(?:INT|EXT)\s*\.?\s*|\s+)"
    r"|[A-Z]\d+\s+(?=(?:INT|EXT)\b)|I/E\.|EST\.|SCENE\s+\d+\b)"
)
ACT = re.compile(r"(?i)^(?:(?:ACT|PART)\s+(?:\d+|ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN)|TEASER|TAG)(?:\s*[:.-].*)?$")
TRANSITION = re.compile(
    r"(?i)^(?:CUT TO:|DISSOLVE TO:|QUICK DISSOLVE TO:|FADE (?:IN|OUT|TO)(?::|\.)?|"
    r"FADE UP\.?|FLASH TO:|INTERCUT WITH:|TIME CUT TO:|SMASH CUT TO:|BLACK ?OUT\.?|BACK TO SCENE)$"
)
SCRIPT_END = re.compile(r"(?i)^(?:END OF (?:SHOW|EPISODE)|THE END)$")
ACT_END = re.compile(r"(?i)^(?:END OF (?:TEASER|SHOW|EPISODE|ACT\s+(?:\d+|ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN))|THE END)$")
SHOT = re.compile(r"^[A-Z0-9][A-Z0-9 \x27\".,:()#&!/?-]*$")
SOUND_EFFECT = re.compile(r"^[A-Z][A-Z0-9 -]{0,17}!+$")
MUSICAL_DIRECTION = re.compile(
    r"\b(?:note|chord|pitch|key)\b.{0,80}\b(?:discordant|dissonant|off[- ]key|out of tune)\b"
    r"|\b(?:discordant|dissonant|off[- ]key|out of tune)\b.{0,80}\b(?:note|chord|pitch|key)\b",
    re.I,
)
MISTYPED_INTERIOR = re.compile(r"(?i)^!NT\s*\.\s+.+")
TIME_SUFFIX = re.compile(r"(?i)\b(?:NIGHT|DAY|MORNING|AFTERNOON|EVENING|DAWN|DUSK|CONTINUOUS)\s*$")
REVIEWED_SCENE_WITH_LOCATION_PREFIX = re.compile(
    r"(?i)^[A-Z0-9][A-Z0-9 '\-./#,&]*\s-\s(?:INT|EXT)\.\s+.+\s-\s"
    r"(?:NIGHT|DAY|MORNING|AFTERNOON|EVENING|DAWN|DUSK|CONTINUOUS)$"
)
REVIEWED_SCENE_HEADINGS = {
    "GNARL'S LAIR - DEEPER INSIDE THE CAVE - NIGHT",
    "40 INT SUMMMERS' HOME - DINING ROOM - NEAR DUSK",
    "!NT. BUFFY'S HOUSE - LIVING ROOM - NIGHT",
    "BUFFY'S HOUSE - LIVING ROOM - NIGHT",
}
REVIEWED_SHOT_DIRECTIONS = {"A REALLY LONG LENS SHOT - BINOC MATT - DAY"}
SHOT_PREFIXES = ("ANGLE", "CLOSE ON", "CLOSE UP", "EXTREME CLOSE", "ON ", "OFF ",
                 "REVERSE", "ANOTHER ANGLE", "WIDER ANGLE", "WIDEN", "INSERT",
                 "TILT", "PUSH IN", "LOW ANGLE", "REAR", "PAN TO", "POV", "BLACK")
EXPLICIT_SHOT_DIRECTION = re.compile(
    r"^(?:ANGLE|CLOSE ON|CLOSE UP|EXTREME CLOSE|REVERSE(?: ANGLE)?|"
    r"ANOTHER ANGLE|WIDER ANGLE|WIDEN|INSERT|TILT|PUSH IN|LOW ANGLE|"
    r"REAR|PAN TO|POV|BLACK)\s*:\s*\S",
    re.I,
)
INLINE = re.compile(r"^\s*(?P<name>[A-Za-z][A-Za-z0-9 ._'\-/]{0,36}?)(?:\s*\((?:V\.[O0]\.|O\.S\.|OFF|CONT'D|VOICE OVER)\))?\s*:\s*(?P<words>\S.*)$", re.I)
# Character cues can contain multiple production modifiers in one pair of
# parentheses, e.g. VOICE (cont'd; O.C.) or NARRATOR (V.O., cont'd).
# Restrict modifiers to the known vocabulary so we don't absorb prose.
_CUE_MODIFIER = r"(?:V\.\s*[O0]\.?|[O0]\.S\.?|[O0]\.C\.?|T\.V\.?|OFF|CONT['’]D\.?|VOICE OVER|ON TV)"
CUE_SUFFIX = re.compile(
    rf"\s*\((?P<modifiers>{_CUE_MODIFIER}(?:\s*[;,]\s*{_CUE_MODIFIER})*)\)$", re.I
)


def cue_modifiers(text: str) -> list[str]:
    """Preserve the exact modifier spellings on the original speaker cue."""
    match = CUE_SUFFIX.search(text.strip().removesuffix(":").rstrip())
    return [part.strip() for part in re.split(r"\s*[;,]\s*", match.group("modifiers"))] if match else []
CUE_BASE = re.compile(r"^[A-Z][A-Z0-9 '\-./#,&]*$")


def is_scene_heading(s: str) -> bool:
    reviewed_irregular_scene = (
        s in REVIEWED_SCENE_HEADINGS
        or REVIEWED_SCENE_WITH_LOCATION_PREFIX.fullmatch(s)
        or (s.startswith("FLASHBACK - ") and s == s.upper()
            and bool(TIME_SUFFIX.search(s)) and s.count(" - ") >= 2)
    )
    return bool(SCENE.match(s) or reviewed_irregular_scene)


def is_act_heading(s: str) -> bool:
    return bool(ACT.fullmatch(s))


def suspected_scene_reason(s: str) -> str | None:
    """Conservative review-only scene candidate; never correct the source cue.

    A malformed INT marker or an all-caps location with two '-' separators and
    a terminal time-of-day token can signal a missing slug prefix. These are
    provisional scene boundaries with explicit warnings, not verified scenes.
    """
    if is_scene_heading(s) or is_act_heading(s) or s in REVIEWED_SHOT_DIRECTIONS:
        return None
    if MISTYPED_INTERIOR.match(s) and TIME_SUFFIX.search(s):
        return "Possible INT. typo: leading !NT."
    if (s == s.upper() and len(s) <= 140 and s.count(" - ") >= 2
            and TIME_SUFFIX.search(s) and not s.startswith(("ANGLE", "ON ", "OFF ", "CLOSE ", "INSERT"))):
        return "Possible location heading missing INT./EXT. prefix"
    return None


def is_heading(s: str) -> bool:
    return is_scene_heading(s) or is_act_heading(s) or suspected_scene_reason(s) is not None


def is_act_end(s: str) -> bool:
    return bool(ACT_END.fullmatch(s))


def is_script_end(s: str) -> bool:
    """Final episode marker, not an intermediate teaser/act break."""
    return bool(SCRIPT_END.fullmatch(s))


def is_transition(s: str) -> bool:
    # Some shooting scripts spell out an intercut destination in prose rather
    # than using the conventional "INTERCUT WITH:" standalone marker.
    if s.startswith("INTERCUT WITH ") and s == s.upper() and len(s) <= 120:
        return True
    return bool(TRANSITION.fullmatch(s))


def is_sound_effect(s: str) -> bool:
    """Short, emphatic uppercase sound cues such as BOOM! and WHOMP!."""
    return bool(SOUND_EFFECT.fullmatch(s))


def is_musical_direction(s: str) -> bool:
    """Recognize explicit descriptions of dissonant musical notes or chords."""
    return bool(MUSICAL_DIRECTION.search(s))


def is_shot_heading(s: str) -> bool:
    # Broad uppercase heuristics used to mistake punctuation and narrative
    # sentences for camera directions. Keep the original useful camera/subject
    # recognition, but screen out exclamations and complete sentences.
    if s in REVIEWED_SHOT_DIRECTIONS:
        return True
    if not (1 <= len(s) <= 160 and not is_heading(s)
            and not is_act_end(s) and not is_transition(s) and not is_sound_effect(s)):
        return False
    if EXPLICIT_SHOT_DIRECTION.match(s):
        return True
    if not SHOT.fullmatch(s):
        return False
    # Explicit camera directions remain such even with a final full stop.
    if s.startswith(SHOT_PREFIXES):
        return True
    return not s.endswith(".")


def cue_like(s: str) -> bool:
    """A likely speaker *name* (without assuming it is a character cue)."""
    if not (1 <= len(s) <= 55) or is_heading(s) or is_transition(s) or is_act_end(s):
        return False
    name = CUE_SUFFIX.sub("", s.strip())
    return bool(CUE_BASE.fullmatch(name) and 1 <= len(name.split()) <= 6)


def unindented_cue_name(s: str) -> str | None:
    """Return a conservative name candidate from a flat, uppercase TXT cue."""
    if not cue_like(s) or s != s.upper():
        return None
    name = CUE_SUFFIX.sub("", s.strip()).replace("’", "'")
    if any(mark in name for mark in ("-", "/", "&", ":", ";")):
        return None
    if len(name.split()) > 3 or name.startswith(
        ("ANGLE ", "CLOSE ", "CLOSER ", "INSERT ", "ON ", "OFF ", "REVERSE ", "WIDE ")
    ):
        return None
    return name


def next_content(lines: list[ScriptLine], start: int) -> ScriptLine | None:
    for line in lines[start:]:
        if line.stripped:
            return line
    return None


def unindented_cue_counts(lines: list[ScriptLine]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for i, line in enumerate(lines):
        nxt = next_content(lines, i + 1)
        name = unindented_cue_name(line.stripped)
        if (name and line.indent <= 5 and nxt and nxt.indent <= 5
                and not is_heading(nxt.stripped) and not is_transition(nxt.stripped)):
            counts[name] += 1
    return counts


@dataclass
class FormatProfile:
    mode: str
    cue_indent: int | None
    dialogue_indent: int | None
    samples: int
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def detect_format(lines: list[ScriptLine]) -> FormatProfile:
    html_groups = {l.group_id for l in lines if l.layout == "html_center"}
    if html_groups:
        return FormatProfile("html_center", None, None, len(html_groups),
                             "HTML <CENTER> blocks with <BR>-separated speaker cues/dialogue")
    strong = []
    inline = 0
    for i, line in enumerate(lines):
        s = line.stripped
        if INLINE.match(s) and not is_heading(s) and not is_transition(s):
            inline += 1
        nxt = next_content(lines, i + 1)
        if not nxt or not cue_like(s) or is_heading(nxt.stripped):
            continue
        if line.indent >= 6 and nxt.indent <= line.indent - 2 and (
            nxt.indent >= 3 or nxt.stripped.startswith("(")
        ):
            strong.append((line.indent, nxt.indent))
    flat_cues = unindented_cue_counts(lines)
    recurring_flat_cues = {name: count for name, count in flat_cues.items() if count >= 2}
    if (sum(recurring_flat_cues.values()) >= 10
            and len(recurring_flat_cues) >= 5):
        return FormatProfile(
            "screenplay_unindented", None, None, sum(recurring_flat_cues.values()),
            "Repeated standalone uppercase speaker cues without indentation",
        )
    if inline >= 3 and inline >= len(strong) * 2:
        return FormatProfile("transcript", None, None, inline, "Recurring NAME: dialogue format")
    if strong:
        return FormatProfile(
            "screenplay",
            round(statistics.median(x for x, _ in strong)),
            round(statistics.median(x for _, x in strong)),
            len(strong),
            "Cue/dialogue indentation observed in document",
        )
    return FormatProfile("uncertain", None, None, 0, "Not enough evidence to establish cue indentation")
