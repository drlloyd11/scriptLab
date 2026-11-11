# ScriptLab v0.8 HTML verification guide

## Goal and boundaries

The deterministic parser and the optional Ollama verifier interpret the same
original HTML independently. `verify-html` sends raw source fragments with
markup; it never sends the Python reader's normalized text, layout labels,
speaker guesses, or reconstructed turns. The model is an independent reviewer,
not the source of truth. This feature evaluates script structure and attribution,
not motives, plot, or emotional meaning.

The existing `compare` command remains available for normalized-text pilots.
It does not verify HTML extraction because it shares that upstream extraction.

## Run a raw-HTML pilot

1. Keep original TXT/HTML sources unchanged and keep canonical scripts separate
   from fanfiction.
2. Check the locally installed Ollama model:

   ```powershell
   python -m scriptlab check-ollama --model qwen3:8b
   ```

3. Select a modest physical source-line range:

   ```powershell
   python -m scriptlab verify-html --script "D:\scripts\buffy\3x15.htm" --model qwen3:8b --out output/verification/S03E15_pilot --start-line 525 --end-line 570
   ```

   For minified HTML, select a character range instead with
   `--start-offset N --end-offset M`. Fragments are bounded and overlapping;
   splitting is attempted at neutral HTML block-tag boundaries. The default
   model is `qwen3:8b`; fragment size, overlap, and endpoint are configurable.

4. Review both `.verification.json` and `.verification.md`. The JSON report
   includes original source hash and HTML evidence; uncertain or ambiguous
   source alignment is not forced into a match.
5. Check every extraction or classification discrepancy against the source
   HTML. Do not repair a script merely to make the two systems agree.
6. Only a person reviewing original source may approve a reference case. Follow
   `GOLD_CASES.md`; Ollama responses are never automatically promoted.

## Reports

The JSON and Markdown outputs report:

- source filename/hash and selected source range;
- whether checks concern the selected region or the whole source (the current
  mechanical integrity inventory covers the whole source even for a pilot);
- selected HTML fragments and number of elements examined;
- agreements and model agreement rate for uniquely aligned elements;
- visible-text inventory differences, double-`<BR>` boundary differences,
  potential missing cue/parenthetical/table material, and other review items;
- classification disagreements, uncertain alignments, unmatched elements,
  malformed/incomplete responses, and evidence from raw HTML.

An agreement is not proof of accuracy. Accuracy against human-reviewed cases is
`null` until approved gold cases are available. No overall accuracy percentage
is produced from model agreement.

## Existing normalized-text comparison

Legacy workflow remains:

```powershell
python -m scriptlab compare --parsed output/buffy/S03E15.json --model qwen3:8b --line-start 525 --line-end 570 --chunk-size 16 --out output/verification/S03E15_legacy
```

In this command, line numbers are normalized parser line numbers. Ollama sees
normalized text plus HTML-derived layout hints, but not Python classifications.
Because both paths share Python's HTML extraction, this mode can detect
classification differences but cannot independently detect upstream extraction
errors.

## Troubleshooting and limitations

- The raw verifier uses Ollama JSON schema mode. `original_text` must be a
  verbatim **visible-text** quote with no HTML tags. Entities are decoded and
  wrapping whitespace may become spaces. A cue and its dialogue are separate
  elements even if the raw source puts both on one line separated by `<BR>`.
- `source_span: null` is appropriate for a unique quote. Otherwise `start` and
  `end` are zero-based Unicode character offsets into the original raw fragment
  (not bytes, whole-file offsets, visible-text offsets, or prompt markers).
  `[start,end)` must enclose the entire mapped raw span of exactly one quote
  occurrence, including intervening tags/entities. Raw-line offset ranges are
  supplied as neutral location aids; no Python classifications are supplied.
- A null span on a repeated quote triggers at most one repair request, using the
  same original HTML and candidate raw locations. It never silently assigns
  occurrences by order. Invalid or still-ambiguous output remains a failure.
- JSON `verification_status` reports response validation as `failed`, `partial`,
  or `complete`, not correctness or exhaustive coverage. Zero valid elements
  or LLM validation failures produce exit code 2; reports are still written.
- Ollama must be running locally and the model installed. The program does not
  start the service or download models.
- Malformed JSON, omitted elements, invalid types, or quoted evidence not found
  in the source are failures, never agreements.
- Overlapping fragments may repeat evidence; exact duplicates are deduplicated.
  Repeated quotes within a fragment and ambiguous source spans require review.
- Physical source positions in vintage HTML are approximate, especially where
  markup and text share a line. Source quote and raw HTML evidence take priority.
- Mechanical inventories are independent checks, not a proof of extraction
  correctness. They can flag legitimate presentation/layout content.
- The raw path was tested against live local `qwen3:8b` on 2026-11-10:

  ```powershell
  python -m scriptlab verify-html --script "D:\scripts\buffy\2x04.htm" --model qwen3:8b --start-line 656 --end-line 678 --out output/verification/S02E04_live_fix
  ```

  Exit code 0; 11 validated elements, 8 agreements, 3 classification
  disagreements, 1 unmatched Python element, 0 LLM failures/omissions, and
  4 items requiring review. One bounded retry disambiguated duplicate dialogue
  quotes. The original source SHA-256 matched the report. JSON and Markdown
  reports are under `output/verification/`. These are pilot observations only;
  larger runs and human-reviewed gold cases remain necessary.
