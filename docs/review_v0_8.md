# ScriptLab v0.8 integrity review

## Round 2 — CHANGES NEEDED

- **IR-007 — blocking — open — `scriptlab/html_verifier.py:557-561`:** Speaker agreement compares Python's normalized `speaker` value with Ollama's original-spelling `speaker` and ignores `normalized_speaker`. The prompt explicitly assigns those two Ollama fields different meanings, while `clean_speaker()` strips cue suffixes such as `(V.O.)` and `(V.0.)` from Python's value. Consequently valid readings of decorated cues are reported as disagreements, and an incorrect `normalized_speaker` can be counted as agreement. Compare Python's speaker with Ollama's `normalized_speaker` when supplied (with a deliberate fallback for absent normalization), while retaining the original spelling as evidence.
- **IR-008 — blocking — open — `scriptlab/html_verifier.py:487,557-562`:** A model element with a non-null/non-empty `uncertainty` value is still eligible to become an agreement and contribute to `model_agreement_rate`; uncertainty is considered only when overlapping responses conflict. Route explicitly uncertain model classifications to `uncertain_alignments` (and human review) rather than counting them as agreements.

Resolved: **IR-001, IR-002, IR-003, IR-004, IR-005, IR-006**.

Resolution evidence: gold cases accept inline or file-backed fragments and validate files against `base_dir`; fragment-relative spans are validated and disambiguate repeated evidence; conflicting overlap labels become uncertain; whole-source integrity scope is explicit in JSON and Markdown; fragments remain within `max_chars`; and zero uniquely aligned comparisons produce a null/unavailable agreement rate.

## Round 3 — CHANGES NEEDED

- **IR-009 — blocking — open — `MANIFEST.json:5,8,14,28,33,42`:** The package manifest no longer describes the delivered v0.8 package. It records 62 passing tests although the final suite has 63, and its SHA-256 values do not match the current `README.md`, `docs/LLM_VERIFICATION_GUIDE.md`, `scriptlab/html_verifier.py`, `scriptlab/reports.py`, or `tests/test_html_verifier.py`. Any consumer using the manifest for package-integrity verification will reject those files. Regenerate the test-count metadata and all affected hashes after the final files are fixed.

Resolved: **IR-001, IR-002, IR-003, IR-004, IR-005, IR-006, IR-007, IR-008**.

Resolution evidence: speaker identity comparison now prefers Ollama's `normalized_speaker` while retaining the original cue as evidence, and any explicitly nonempty uncertainty is routed to uncertain alignments before agreement classification.

## Round 4 — PASS

No open findings.

Resolved: **IR-009**.

Resolution evidence: `MANIFEST.json` now records 63 passing and 1 skipped offline unit test. All 42 files listed in the manifest exist, and every recorded SHA-256 hash matches its current package file.

## Round 5 — CHANGES NEEDED

- **IR-010 — blocking — open — `scriptlab/html_verifier.py:576-611,621-640`:** Repeated quotes are not actually required to resolve to distinct source occurrences. If the repair returns two identical elements with the same candidate span, both pass the per-item “exactly one occurrence” check; the later grouping then silently collapses them into one element. This permits a guessed/reused duplicate span to become a successful response while another occurrence is omitted, contrary to the required duplicate disambiguation. Track span claims within each fragment response and reject repeated-quote entries that reuse the same mapped occurrence (with a validation failure rather than deduplication); retain cross-fragment deduplication only for genuine overlap.

Resolved: **IR-001, IR-002, IR-003, IR-004, IR-005, IR-006, IR-007, IR-008, IR-009**.

## Round 6 — PASS

No open findings.

Resolved: **IR-010**.

Resolution evidence: `scriptlab/html_verifier.py` now tracks each accepted
`(start, end, quote)` occurrence within its fragment and records an explicit
validation failure when another element reuses it. The check occurs before
cross-fragment grouping, so genuine overlap remains deduplicated. The focused
regression exercises same-fragment reuse; the final pilot reports complete
validation with 11 elements and no failures, its source hash matches, and all
manifest file hashes match the delivered files.
