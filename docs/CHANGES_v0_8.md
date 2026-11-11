# ScriptLab v0.8.0

- Added `verify-html`, which sends bounded, overlapping fragments of original
  `.htm`/`.html` source to the existing local Ollama JSON client.
- The raw-HTML interpretation is isolated from Python-normalized text and
  parser decisions. It requests element type, exact source evidence, original
  and normalized speaker identities, source span, and uncertainty.
- Added conservative evidence/span alignment, human-review outcomes for
  uncertain or unmatched items, mechanical visible-text/BR/cue/parenthetical/
  parallel-table checks, and JSON plus Markdown reports.
- Added physical source-line and zero-based character-range pilot selection.
- Added a human-reviewed gold-case schema and test harness. The example remains
  pending review; no ground-truth accuracy is asserted.
- Preserved existing `parse`, `compare`, and `check-ollama` commands.
- Closed SQLite test connections explicitly so Windows temporary-directory
  cleanup is deterministic.
- No dependencies were added. Offline tests use simulated responses.
- Follow-up live-path fix: precise visible-text-only quotes and raw-fragment
  offset semantics, Ollama JSON schema output, rejection of tag-containing
  quotes, explicit failed/partial response status, and one bounded repair for
  repeated quotes with missing spans. The local `qwen3:8b` S02E04 pilot now
  produces 11 validated elements with no LLM failures (2026-11-10).
