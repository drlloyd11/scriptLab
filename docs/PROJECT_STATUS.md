# Project status and next steps

Last updated: 2026-11-11

## Completed

- Built a source-preserving parser for TXT and vintage HTML screenplay layouts,
  with scene, dialogue, action, cue, and uncertainty classifications.
- Added offline parsing, reporting, SQLite storage, source hashing, and
  optional local Ollama verification of original HTML.
- Reviewed Buffy parsing across Seasons 1-7; the previously maintained
  seasonal queues had no remaining actionable warnings at the time of review.
- Completed two independent, challenge-oriented holdout rounds. Round 2
  matched 59 of 60 reviewed element types and all 18 explicitly adjudicated
  speaker attributions. The one remaining type disagreement was an actor
  direction classified by the user as action and by the parser as a
  parenthetical. These samples are not a representative accuracy estimate.
- Added support for Angel scripts as a separate series, including a detector
  for their unindented screenplay layout.
- Parsed 36 Angel TXT files into local JSON, Markdown, and SQLite outputs.
  Angel HTML alternates were intentionally excluded. The generated output is
  local and is not tracked in this repository.
- Added extension filtering so TXT-only scans ignore HTML alternates before
  duplicate-episode checks.

## Current limitations

- Angel coverage is incomplete: only 36 TXT episodes were found, with large
  gaps, especially in Season 4.
- The Angel parse reported 1,955 unresolved structural lines and 30
  provisional scene headings across those files. These need review before
  treating the output as reliable classifications.
- One Angel TXT file produced an encoding warning. Verify its source bytes and
  encoding before relying on its extracted text.
- Buffy holdout reviews and source-derived gold cases depend on original
  episode files and local review artifacts. They are intentionally not
  included in this repository; shared tests should use synthetic fixtures.
- Ollama agreement is not ground truth. Human review against the original
  source remains necessary.

## Planned work

1. Review the Angel parser's unclassified lines and provisional scene
   headings, starting with representative episodes from each supplied season.
2. Verify the warned Angel file's encoding and check that its text is intact.
3. Keep Angel source and output files outside Git; record only non-sensitive
   aggregate progress and synthetic regression cases here.
4. Continue recording Buffy and Angel parser corrections as small, synthetic
   tests or documented human decisions without distributing episode text.
5. Re-run the complete offline test suite after parser changes and refresh
   project documentation when results or limitations change.

## Repository boundary

This repository is for ScriptLab code, synthetic examples, tests, and
documentation. Episode scripts, source-derived fixtures, parsed JSON/reports,
review excerpts, SQLite databases, and local progress logs are excluded.
Keep original corpora and generated outputs in local directories.
