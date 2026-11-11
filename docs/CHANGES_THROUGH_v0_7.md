# ScriptLab Python parser — v0.7 (Consequences fixes + TXT/HTML)

This revision extends **Buffy's vintage HTML parsing** to multi-speaker sections and side-by-side dialogue while preserving support for **plain-text screenplays** and `NAME: dialogue` transcripts. It is a **structural parser**, not a story-understanding model. No external Python packages are required; Python 3.10 or newer.

## Version 0.7 — *Consequences* (Buffy S03E15) fixes

- **Provisional scene boundaries:** `!NT. ... - NIGHT` (probable `INT.` typo) and all-caps location slugs like `HOUSE - LIVING ROOM - NIGHT` (missing `INT./EXT.`) are now `suspected_scene_heading`, with a `suspected_scene_heading` warning and source-line reference. The **original text is never altered**, and the provisional scene boundary increments the scene index to avoid attaching later dialogue to the preceding scene. Reports distinguish confirmed scene headings from provisional ones. The heuristic is conservative but is not proof that an inferred scene is real.
- **Transitions:** Recognizes `FADE UP`, `FLASH TO:`, `INTERCUT WITH:`, `TIME CUT TO:`, `FADE TO:`, and intercut directions such as `INTERCUT WITH WILLOW IN HER ROOM.`. Existing `BLACK OUT.` remains a normal transition, not an episode ending.
- **Shot vs. action/effects:** Classifies `WHOMP!` and `BOOM!` as `sound_effect`; a complete sentence like `A VOICE STOPS HER.` is `action`. Explicit camera cues such as `ANGLE: EVERYBODY ELSE.` remain `shot_heading`, even with a terminal period.
- **Terminal marker:** `THE END` is now an `act_end` and stops structural parsing; trailing website material becomes `supplementary_metadata` if present.
- **Quality gate:** `--fail-on-ambiguity` now exits nonzero for either `unknown` structural lines **or provisional scene headings**. Two provisional headings in *Consequences* will trigger this option until reviewed; ordinary parsing still writes JSON/SQLite/reports successfully.
- **Compatibility:** The optional independent LLM comparator knows about the two new kinds, and SQLite stores them without a schema migration. **47 automated tests pass** (including 10 new synthetic tests; no user episode files are bundled).

### S03E15 results

| Measurement | Result |
|---|---:|
| Confirmed scene headings | 47 |
| Suspected scene headings, flagged for review | 2 |
| Total scene boundaries, including provisional | 49 |
| Reconstructed dialogue turns | 371 |
| Unresolved `unknown` lines | 0 |
| Sound-effect markers | 3 |
| Transition markers | 11 |
| Mechanical coverage/integrity errors | 0 |

The two suspected boundaries are at **HTML source lines 794 and 816**. They are not automatically corrected to `INT.` in the saved source. The script ends with `THE END` at HTML source line 2199. The 371 dialogue turns are unchanged from v0.6; no speaker attribution changes occurred in the six tested episodes.

These measurements reflect deterministic parsing and a targeted source review, **not independent LLM validation**. A zero unknown count must not be mistaken for fully correct interpretation.

## Version 0.6 — *Restless* (Buffy S04E22) fixes

- Recognizes centered HTML cues ending in a colon, including `VOICE:`, as real character cues. It preserves the literal cue text (`VOICE:`), normalizes the speaker to `VOICE`, and correctly attributes the following dialogue lines.
- Treats content following the final `END OF SHOW` or `END OF EPISODE` marker as `supplementary_metadata`, instead of assigning it to an actor or flagging it as a malformed dialogue block. This covers links to other drafts, promotional material, and webpage footers. **Intermediate** `END OF TEASER` and `END OF ACT ONE` markers do **not** stop parsing.
- Passes the new element kind to the integrity validator and to the optional LLM comparison prompt; keeps this material in normalized lines and SQLite rather than discarding it.
- Adds seven synthetic regression tests; **37/37 tests pass**.

### Real-script structural regression check

| Buffy episode | Reconstructed dialogue turns | Unknown lines | Supplementary lines | Coverage/integrity errors |
|---|---:|---:|---:|---:|
| S02E03 *School Hard* | 445 | 0 | 0 | 0 |
| S04E22 *Restless* | 380 | 0 | 1 | 0 |
| S05E11 *Triangle* | 455 | 0 | 0 | 0 |
| S06E03 *After Life* | 419 | 0 | 0 | 0 |
| S06E07 *Once More, With Feeling* | 381 | 0 | 0 | 0 |

*Restless* formerly yielded 378 turns and six unresolved lines. The differences are exactly the two previously rejected `VOICE:` speaker cues and their three lines of dialogue, plus one website link after the end marker. The other four scripts retain the same structural classifications and speaker attributions as v0.5. The `speaker_spelling_variant` warning for `XAN'DER` in *After Life* is still preserved.

The parser **does not** yet infer that a character is speaking as a representative of someone else. For the Tara/First Slayer exchange in *Restless*, structural speaker remains `TARA`; representing the First Slayer is a later, evidence-grounded semantic annotation. No live Ollama verification has been performed.

## Version 0.5 — fixes verified against Buffy S06E03 (*After Life*)

- Accepts `DAWN (cont'd.)` (period inside the parentheses) as a normal continued-speaker cue, retaining the exact original cue text and classifying the following speech correctly.
- Recognizes `END OF EPISODE` as an end-of-act/show marker, rather than an unresolved centered block.
- Spots the source typo `XAN'DER` when `XANDER` independently occurs elsewhere as a speaker in that document. Interprets its dialogue as Xander, preserves the original spelling, and **emits a `speaker_spelling_variant` review warning**. This is intentionally a narrow correction: general fuzzy speaker matching is NOT enabled.
- Added five synthetic regression tests. **30/30 tests pass** with standard `unittest`.

### Verified real-script structural outputs

| Episode | Dialogue turns | Scene headings | Unclassified lines | Mechanical validation errors |
|---|---:|---:|---:|---:|
| S02E03 *School Hard* | 445 | 59 | 0 | 0 |
| S05E11 *Triangle* | 455 | 23 | 0 | 0 |
| S06E03 *After Life* | 419 | 37 | 0 | 0 |
| S06E07 *Once More, With Feeling* | 381 | 32 | 0 | 0 |

Against the v0.4 run, *After Life* changed just **six normalized lines**: the continued Dawn cue and its dialogue (2), the misspelled Xander cue and two dialogue lines (3), and the end marker (1). The other three real episode files had **no changes in line classification or speaker attribution**.

**Important distinction:** `speaker_spelling_variant` remains a warning requesting review, and a Windows-1252 decoding advisory is not a structural error. Zero unknown lines does not prove perfect interpretation. This work has **not** been independently checked by a running LLM.

## What changed in v0.3

- Correctly splits a single `<CENTER>` containing several `<P>`-separated speakers into **distinct dialogue turns**. This is essential for Buffy season 6's *Once More, With Feeling*.
- Recognizes **two-column dialogue tables** as simultaneous/overlapping parts. Normalized lines and dialogue turns carry `parallel_row` and `parallel_column` identifiers. Reading order is HTML DOM order, not necessarily the temporal order of simultaneous voices.
- Accepts group speaker cues including `XANDER/ANYA`, `TARA/GILES`, `DEMON AND VAMPS`, and `BUFFY, SPIKE AND GROUP` without treating them as camera directions. Normalizes spaces around slashes.
- Keeps multi-`<BR>` parentheticals together as direction segments rather than incorrectly storing their continuation as dialogue.
- Recognizes `END OF SHOW` as a script end marker.
- Preserves compatibility with the previous *School Hard* example and the TXT parser. Adds two new regression tests (20 total).

### Real-script checks

| Measurement | v0.2 S06E07 | v0.3 S06E07 |
|---|---:|---:|
| Dialogue turns identified | 138 | 381 |
| Dialogue lines identified | 444 | 967 |
| Shot headings identified | 434 | 6 |
| Unresolved normalized lines | 31 | 0 |
| Scene headings | 32 | 32 |

S06E07 (`6x07.htm`) has 1,655 normalized logical lines, including a "no teaser" section, 5 act/teaser headings, 32 scene headings, 198 action paragraphs, 381 speech cues, 967 spoken/lyric lines and 48 parenthetical segments. 9 parallel HTML table rows were found. The results have **zero mechanical validation issues**, but these are outputs from one deterministic parser, **not independent LLM validation** or manually established ground truth. Song lyrics remain structurally labeled `dialogue`; identifying performance mode, dramatic intent, or all overlapping timing would need a semantic pass.

S02E03 (`2x03.htm`) still produces 445 reconstructed dialogue turns and the same structural totals as v0.2. The Windows-1252 decode notice remains expected.

## Features inherited from v0.2

- HTML `<CENTER>` and `<BR>` are interpreted as **speaker/dialogue structure**, not lost during text conversion. The page-wide centered table wrapper is ignored as a dialogue indicator.
- Handles `.htm` / `.html` pages and Windows-1252 encodings, with source hashes and approximate original HTML line references.
- Recognizes `CHARACTER (cont'd)`, `(V.O.)`, `(O.S.)`, speaker modifiers, and parentheticals within dialogue, including parentheticals appearing halfway through a speech.
- Recognizes uncommon wrapped speaker labels (such as `BIG<BR>UGLY`) when the full speaker name appears elsewhere in the same script.
- Distinguishes **Teaser/Act headings**, **scene headings**, **uppercase shot/subject labels**, **action**, and **transitions**. A bare uppercase paragraph such as `SPIKE` is not treated as a dialogue cue.
- Produces both fine-grained **per-line elements** and **reconstructed dialogue turns** with speaker, text, parentheticals, act/scene, and line references.
- Preserves HTML layout tags (`layout` and `group_id`) in JSON/SQLite and sends those input-layout hints to the optional independent Ollama comparator.
- Adds integrity tests for every nonblank normalized line and for dialogue-turn coverage. Old SQLite files are upgraded in place with new columns.

## Quick start — Windows PowerShell

Open PowerShell in the directory containing this README, then run:

```powershell
python -m scriptlab scan --series buffy "D:\scripts\buffy" --series angel "D:\scripts\angel"
python -m scriptlab parse --series buffy "D:\scripts\buffy" --series angel "D:\scripts\angel" --out output
```

You can give **as many `--series NAME DIRECTORY` pairs** as needed. The scanner recursively finds `.txt`, `.htm`, and `.html` files. It detects `2x03.htm`, `S02E03.html`, and `Season_2_Episode_3.txt` naming patterns. Buffy may be all HTML; the script format is auto-detected **per file**, not per show. If there is no recognizable HTML-centered or `<pre>` layout, check the warning and do not assume dialogue was parsed correctly.

To stop with a nonzero exit status when **unresolved structural lines or provisional scene-heading warnings** remain:

```powershell
python -m scriptlab parse --series buffy "D:\scripts\buffy" --out output --fail-on-ambiguity
```

Try the included invented examples:

```powershell
python -m scriptlab parse --series buffy sample_corpus/buffy --series angel sample_corpus/angel --out demo_output
python -m unittest discover -s tests -v
```

## Output files

For each episode:

- `output/buffy/S02E03.json`: per-line classifications, HTML provenance, source SHA-256, a list of `dialogue_turns`, and ambiguity findings.
- `output/buffy/S02E03.report.md`: human-readable counts, detected format, and diagnostic issues.
- `output/scriptlab.sqlite`: stored episodes, script lines, elements, dialogue turns, and issues.

The original input files are **never edited**. Their exact bytes remain in their original directories. Each JSON file points to its source path and includes its SHA-256.

The parser **does not** canonicalize character aliases yet: `MR. SNYDER` and `SNYDER` may appear as two speakers pending the planned character-resolution stage. It also does not infer intentions, truthfulness, or events from dialogue.

## Optional: infer a grammar from representative scripts

With Ollama running locally and `qwen3:8b` installed:

```powershell
python -m scriptlab infer-format --series buffy "D:\scripts\buffy" --model qwen3:8b --sample-limit 6 --out output/proposed_grammar.json
```

The LLM's output is a **proposal**, not automatically executed Python. Review cited examples before accepting a new grammar rule.

## Optional: independently compare Python vs an LLM

```powershell
python -m scriptlab compare --parsed output/buffy/S02E03.json --model qwen3:8b --chunk-size 30
```

The LLM sees normalized script lines with original HTML layout hints, **not** the Python parser's classifications. It is instructed to classify them independently. Results are saved as `.comparison.json` and `.comparison.md`. For a full-length episode this may involve many model requests and can be slow. The comparator has unit tests with a stub model but **has not been tested against a live Ollama model in this environment**.

A disagreement is not proof that Python is wrong; an agreement does not prove accuracy either. For confidence, manually verify a reference subset from each distinct HTML/TXT formatting family.

## “School Hard” (Buffy S02E03) regression test

The supplied `2x03.htm` sample was processed on this revision and matches its v0.2 classification totals. Its normalized content contained **1,725 nonblank logical lines**: 445 character cues, 831 dialogue segments grouped into 445 turns, 272 action paragraphs, 59 scene headings, 31 shot headings, 61 parentheticals, 5 act/teaser headings, 4 end-of-act markers, 13 transitions, and 4 metadata items. **Zero lines were left unclassified and no mechanical coverage errors occurred.** There was one expected advisory message because the source uses **Windows-1252**. These counts are *parser outputs*, not independent ground truth. Inspect the report and a few selected scenes before treating them as verified facts.

## Current limitations

- The HTML reader supports the observed `<CENTER><BR>` family, `<pre>` formatting and some other basic HTML. Unseen Buffy pages with radically different markup may need another reader profile.
- HTML source-line references are approximate; normalized line numbers are precise. The original HTML must remain available for auditing.
- No automatic semantic interpretation, sung-versus-spoken performance labels, scene-beat analysis, speaker alias resolution, or correction UI yet.
- `parallel_row` captures which utterances share an HTML table row, not precise lyric synchronization or who starts first.
- The character identity resolver will eventually distinguish individual voices inside composite cues such as `GROUP` or `XANDER/ANYA`.
- Unrecognized centered blocks are classified as `unknown`, and unknown TXT cues remain explicit. **Zero unknowns is not equivalent to 100% accuracy.**
- The LLM comparison is an optional validation aid, not a completed independent validation of this actual episode.

## Version 0.4 — fixes verified against Buffy S05E11 (*Triangle*)

- Accepted the source-document typo `BUFFY (V.0.)` (zero) alongside `BUFFY (V.O.)` (letter O). Both become `speaker="BUFFY"` while the original cue remains available verbatim.
- Preserved the count of consecutive `<BR>` separators before each logical HTML line as `br_run_before` in JSON. Within a centered block, **two or more `<BR>` tags followed by an already established speaker cue** now start a distinct dialogue turn. This fixes the Anya-to-Willow speaker switch inside one centered HTML paragraph. It does **not** blindly treat every uppercase word after a blank line as a new character.
- Added three minimal regression tests for these patterns. No Buffy episode files are bundled; users retain their original source files.

### Real-file sanity checks in the development environment

| Episode | Dialogue turns | Structural unknowns | Mechanical validation errors |
|---|---:|---:|---:|
| S02E03 *School Hard* | 445 | 0 | 0 |
| S05E11 *Triangle* | 455 | 0 | 0 |
| S06E07 *Once More, With Feeling* | 381 | 0 | 0 |

These are deterministic parsing results, not human-labelled ground truth or independent LLM verification. `Triangle` gains two turns versus v0.3 because one previously unidentified voiceover cue is recognized and one previously merged speech is split into two. The original Windows-1252 decoding advisory on older files remains informational, not an unresolved classification.
