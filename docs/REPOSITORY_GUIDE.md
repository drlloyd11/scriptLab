# Repository and file guide

## What has been built

ScriptLab is a Python 3.10+ project for source-preserving parsing of television
screenplays in plain text and vintage HTML. The parser identifies scene
headings, speaker cues, dialogue, parentheticals, action, transitions, and
other structural elements while retaining source text and provenance.

The package also provides a command-line interface, parse reports, SQLite
storage, integrity validation, optional format-grammar proposals, and optional
independent verification of original HTML using a local Ollama model. Parsing
and the offline tests do not require Ollama or third-party Python packages.

Work completed to date includes:

- Buffy parser reviews and rule refinements across Seasons 1-7.
- Human-reviewed reference decisions and two separate holdout rounds. The
holdout samples were challenge-oriented, not representative accuracy studies.
The second round matched 59/60 reviewed element types and 18/18 explicitly
adjudicated speaker attributions; one action-versus-parenthetical disagreement
remains.
- Angel support as a separate series, including unindented screenplay TXT
layout detection and TXT-only catalog filtering.
- Local parsing of 36 Angel TXT files. The collection is incomplete, and the
generated parse still has unresolved lines and provisional scene headings
that require human review.

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for the current results,
limitations, and planned work; the version history documents implementation
details.

## Python implementation

The application package is `scriptlab/`:

| File | Purpose |
|---|---|
| `scriptlab/__init__.py` | Package metadata and version. |
| `scriptlab/__main__.py` | Enables `python -m scriptlab`. |
| `scriptlab/catalog.py` | Finds episode files, parses episode IDs, applies file-extension filters, detects duplicates, and reports gaps. |
| `scriptlab/cli.py` | Implements `scan`, `parse`, `compare`, `verify-html`, Ollama preflight, and format-inference commands. |
| `scriptlab/comparator.py` | Requests independent line labels from Ollama and compares them with saved parser output. |
| `scriptlab/format_detector.py` | Detects screenplay layout and recognizes structural formats without assigning plot meaning. |
| `scriptlab/grammar_inference.py` | Produces a proposed, non-executable description of observed script formatting. |
| `scriptlab/html_verifier.py` | Verifies bounded fragments of original HTML and checks evidence alignment and extraction integrity. |
| `scriptlab/llm.py` | Optional local Ollama JSON client; not required for offline parsing. |
| `scriptlab/models.py` | Shared source, line, element, and issue data models. |
| `scriptlab/parser.py` | Deterministic source-preserving structural parser. |
| `scriptlab/readers.py` | Reads TXT/HTML, detects encoding, and retains source/layout provenance. |
| `scriptlab/reports.py` | Produces human-readable parse, comparison, and verification reports. |
| `scriptlab/storage.py` | Saves parsed results to SQLite. |
| `scriptlab/validator.py` | Checks line coverage, source integrity, element shape, and related invariants. |

## Python tests

Run the repository's offline suite from the root with:

```powershell
python -m unittest discover -s tests -v
```

| File | Focus |
|---|---|
| `tests/test_catalog.py` | Filename parsing, series separation, duplicate handling, and extension filtering. |
| `tests/test_comparator.py` | Independent labels and parser comparison. |
| `tests/test_gold_cases.py` | Gold-case validation and parser regression checks when approved fixtures are available. |
| `tests/test_html_after_life_regressions.py` | Synthetic HTML layout and cue regressions. |
| `tests/test_html_center.py` | Centered HTML, cue modifiers, scene recognition, and dialogue turns. |
| `tests/test_html_consequences_regressions.py` | Synthetic scene, camera-direction, and malformed-heading cases. |
| `tests/test_html_musical.py` | Musical directions and overlapping/simultaneous dialogue layouts. |
| `tests/test_html_restless_regressions.py` | Synthetic edge cases for dialogue and script endings. |
| `tests/test_html_triangle_regressions.py` | Synthetic shared-center and cue-layout regressions. |
| `tests/test_html_verifier.py` | Offline raw-HTML verification, evidence matching, uncertainty, and validation. |
| `tests/test_parser.py` | TXT/HTML parsing, dialogue, parentheticals, and line-integrity checks. |
| `tests/test_s02e04_pilot_fixes.py` | Synthetic regressions for HTML verifier pilot fixes. |
| `tests/test_storage.py` | SQLite storage behavior. |
| `tests/test_verification_pilot.py` | Offline CLI/pilot behavior using simulated model responses. |

Tests and the two files under `tests/fixtures/gold_cases/` use synthetic
examples. Source-derived Buffy fixtures and a local-only holdout validation
test are intentionally excluded from Git. Therefore the holdout figures
documented in [HOLDOUT_REVIEW.md](HOLDOUT_REVIEW.md) are historical user-review
results, not checks rerun by the public repository test suite.

## Markdown documents

| File | Purpose |
|---|---|
| `README.md` | Project introduction, requirements, commands, and links to key docs. |
| `docs/CHANGES_THROUGH_v0_7.md` | Historical changes through the v0.7 parser work. |
| `docs/CHANGES_v0_8.md` | v0.8 raw-HTML verifier and validation changes. |
| `docs/CHANGES_v0_8_1.md` | v0.8.1 verification fixes and retest instructions. |
| `docs/GOLD_CASES.md` | Rules for human-reviewed reference cases and regression use. |
| `docs/HOLDOUT_REVIEW.md` | Holdout-review method and aggregate results; private source artifacts are omitted. |
| `docs/LLM_VERIFICATION_GUIDE.md` | Local Ollama verification workflow, limitations, and interpretation guidance. |
| `docs/PILOT_CASES.md` | Historical Buffy pilot ranges; requires the original scripts to use. |
| `docs/PROJECT_STATUS.md` | Current completed work, limitations, and planned work. |
| `docs/REPOSITORY_GUIDE.md` | This overview of architecture, tests, and documentation. |
| `docs/SIX_EPISODE_BASELINE.md` | Historical parser counts and their non-ground-truth caveat. |
| `docs/review_v0_8.md` | Integrity-review record for the v0.8 work. |

`docs/review_template.csv` is a review worksheet, not a Markdown document. The
PowerShell pilot helper is `tools/Verify_Buffy_Pilot.ps1`.

## Files deliberately kept local

The repository does not include episode scripts or source-derived dialogue
fixtures. `.gitignore` also excludes generated `output/` and
`verification_runs/`, local holdout artifacts, `MANIFEST.json`, and
`progress-details.md`. Parsed JSON, Markdown reports, and SQLite files can
contain copied source text and should remain outside the repository as well.
