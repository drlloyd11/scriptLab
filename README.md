# ScriptLab

ScriptLab is a source-preserving parser for television screenplay text and
vintage HTML. It identifies scene headings, dialogue cues, dialogue, action,
and related structure, while retaining source text and provenance. An optional
verifier compares an HTML source with an independent local Ollama reading.

The project includes reusable code, documentation, synthetic examples, and
tests. Original episode scripts and generated parse/review outputs are not part
of this repository. See [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) for
completed work, current limitations, and next steps.

## Requirements

- Python 3.10 or later
- Standard library for parsing and tests
- Optional local Ollama installation for LLM verification

## Run tests

From the repository root:

```powershell
python -m unittest discover -s tests -v
```

## Parse scripts

Point ScriptLab at script directories on your machine; the source files are
read-only and output is written separately:

```powershell
python -m scriptlab scan --series angel "D:\scripts\angel" --extensions txt
python -m scriptlab parse --series angel "D:\scripts\angel" --extensions txt --out output\angel
```

Use `--extensions txt` to exclude HTML alternates before duplicate-episode
checks. Omit the option to scan supported TXT and HTML formats. Multiple series
can be supplied in the same command; series names are included in output and
database episode IDs.

## Optional local Ollama verification

```powershell
python -m scriptlab check-ollama --model qwen3:8b
python -m scriptlab verify-html --script "D:\scripts\buffy\3x15.htm" --model qwen3:8b --out output\verification\S03E15_pilot --start-line 525 --end-line 570
```

Verification is local. The verifier sends bounded fragments of original HTML
to Ollama, then records agreements, disagreements, source-alignment checks, and
uncertainty. Model agreement is not a measure of accuracy; unresolved results
require human review. See
[docs/LLM_VERIFICATION_GUIDE.md](docs/LLM_VERIFICATION_GUIDE.md).

## Project documents

- [Version history](docs/CHANGES_THROUGH_v0_7.md),
  [v0.8](docs/CHANGES_v0_8.md), and
  [v0.8.1](docs/CHANGES_v0_8_1.md)
- [Human-reviewed cases and review method](docs/GOLD_CASES.md)
- [Held-out review method and results](docs/HOLDOUT_REVIEW.md)
- [Project status and planned work](docs/PROJECT_STATUS.md)
- [Repository and file guide](docs/REPOSITORY_GUIDE.md)

Do not add episode scripts, source-derived fixtures, databases, or generated
reports to the repository. Those materials may contain copyrighted dialogue;
keep them in a local corpus and use synthetic fixtures for shared tests.
