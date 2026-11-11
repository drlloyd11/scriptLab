"""Human-readable discrepancy and ambiguity reports."""
from __future__ import annotations

from collections import Counter


def parse_report(parsed: dict) -> str:
    ep = parsed["episode"]
    c = Counter(e["kind"] for e in parsed["elements"])
    findings = parsed["issues"]
    lines = [f"# Parse report: {ep['key']}", "",
             f"Source: `{ep['path']}`", f"SHA-256: `{ep['sha256']}`", "",
             f"Detected format: **{parsed['profile']['mode']}** ({parsed['profile']['reason']})", "",
             "## Structural totals", "",
             f"- Confirmed scene headings: {c['scene_heading']}; provisional scene headings: {c['suspected_scene_heading']}; total scene boundaries: {c['scene_heading'] + c['suspected_scene_heading']}",
             f"- Acts/teaser sections: {c['act_heading']}",
             f"- Unresolved lines: {c['unknown']}",
             f"- Reconstructed dialogue turns: {len(parsed.get('dialogue_turns', []))}",
             f"- Original normalized lines (including blanks): {len(parsed['lines'])}",
             f"- Nonblank lines classified: {len(parsed['elements'])}"]
    lines += [f"- {kind}: {c[kind]}" for kind in sorted(c)]
    lines += ["", "## Issues", ""]
    if findings:
        for issue in findings:
            place = f"line {issue['line']}" if issue.get("line") else "document"
            lines.append(f"- **{issue['severity']} — {issue['kind']} ({place}):** {issue['message']}")
    else:
        lines.append("No issues detected. This does not prove the classifications are correct.")
    return "\n".join(lines) + "\n"


def comparison_report(result: dict) -> str:
    lines = [f"# LLM / Python comparison: {result['episode_key']}", "",
             f"Model: `{result['model']}`", "",
             f"Requested lines: {result.get('requested_lines', result['compared_lines'])}",
             f"Compared lines: {result['compared_lines']}",
             f"Unreviewed lines: {result.get('unreviewed_lines', 0)}",
             f"Scope (normalized lines): {result.get('target_line_start', '?')}–{result.get('target_line_end', '?')}",
             f"Original source SHA-256: `{result.get('source_sha256') or 'unavailable'}`",
             f"Agreements: {result['agreements']}",
             f"Disagreements: {len(result['disagreements'])}",
             f"LLM failures or omissions: {len(result['llm_failures'])}",
             f"Agreement rate on compared lines: {(100 * result['agreements'] / result['compared_lines']):.1f}%" if result['compared_lines'] else "Agreement rate: unavailable (no valid LLM labels)", "",
             "**Agreement is not proof of correctness. Review disagreements against the original source.**", "",
             "## Disagreements", ""]
    for d in result["disagreements"]:
        lines.extend([f"- **Line {d['line']}**: `{d['source_text']}`",
                      f"  - Python: {d['python_kind']} / {d.get('python_speaker') or '—'}",
                      f"  - LLM: {d['llm_kind']} / {d.get('llm_speaker') or '—'}"])
    if not result["disagreements"]:
        lines.append("None reported.")
    if result["llm_failures"]:
        lines.extend(["", "## LLM failures / omitted lines", ""])
        lines.extend(f"- {x}" for x in result["llm_failures"])
    return "\n".join(lines) + "\n"


def raw_html_verification_report(result: dict) -> str:
    """Render a source-evidence-first report; agreement is never called accuracy."""
    agreement_rate = result["model_agreement_rate"]
    rate_text = (
        f"{100 * agreement_rate:.1f}%" if agreement_rate is not None
        else "unavailable (no uniquely aligned elements)"
    )
    lines = [
        f"# Independent raw-HTML verification: {result['source_filename']}", "",
        f"Source: `{result['source_path']}`",
        f"SHA-256: `{result['source_sha256']}`",
        f"Model: `{result['model']}`",
        f"Response validation: {result.get('verification_status', 'unspecified')} (not an accuracy verdict)",
        f"Selected source lines: {result['selected_source_lines']['start']}–{result['selected_source_lines']['end']}",
        f"Fragments examined: {result['fragments_examined']}",
        f"LLM elements examined: {result['elements_examined']}",
        f"Agreements: {result['agreement_count']}",
        f"Model agreement rate among uniquely aligned elements: {rate_text}",
        f"Integrity-check scope: {result.get('integrity_checks_scope', 'unspecified')}",
        "Accuracy against human-reviewed reference cases: not measured",
        f"Extraction-integrity findings: {len(result['extraction_disagreements'])}",
        f"Classification disagreements: {len(result['classification_disagreements'])}",
        f"Uncertain alignments: {len(result['uncertain_alignments'])}",
        f"Unmatched Ollama elements: {len(result['unmatched_ollama_elements'])}",
        f"Unmatched Python elements: {len(result['unmatched_python_elements'])}",
        f"LLM failures or omitted responses: {len(result['llm_failures_or_omissions'])}",
        f"Items needing human review: {result['items_needing_human_review']}", "",
        "**Agreement is not proof of accuracy.** Source alignment is conservative; ambiguous matches are left for review.", "",
        "## Extraction-integrity findings", "",
    ]
    if result["extraction_disagreements"]:
        for finding in result["extraction_disagreements"]:
            lines.extend([
                f"- **{finding['check']}** — {finding['message']}",
                f"  - Original HTML: `{finding.get('original_html_evidence', '')}`",
                f"  - Python normalized text (sample): `{finding.get('python_normalized_text_sample', '')}`",
            ])
    else:
        lines.append("No mechanical inventory discrepancy detected. This is not proof that extraction is correct.")

    lines.extend(["", "## Classification disagreements", ""])
    if result["classification_disagreements"]:
        for item in result["classification_disagreements"]:
            llm = item["ollama"]
            python = item["python"]
            lines.extend([
                f"- **Source line {llm['source_span']['source_line_start']}** — {item['reason']}",
                f"  - Original HTML: `{item['original_html_evidence']}`",
                f"  - Python: `{python.get('kind')} / {python.get('speaker') or '—'} — {python.get('text', '')}`",
                f"  - Ollama: `{llm['element_type']} / original={llm.get('speaker') or '—'} / normalized={llm.get('normalized_speaker') or '—'} — {llm['original_text']}`",
            ])
    else:
        lines.append("None reported.")

    for title, key in (
        ("Uncertain alignments", "uncertain_alignments"),
        ("Unmatched Ollama elements", "unmatched_ollama_elements"),
        ("Unmatched Python elements", "unmatched_python_elements"),
    ):
        lines.extend(["", f"## {title}", ""])
        entries = result[key]
        if not entries:
            lines.append("None.")
        else:
            for entry in entries[:100]:
                if key == "unmatched_python_elements":
                    lines.extend([
                        f"- Python line {entry.get('line')} / source line {entry.get('source_line')}: `{entry.get('kind')} — {entry.get('text', '')}`",
                        f"  - Ollama: no uniquely aligned element returned ({entry.get('alignment_reason', 'review required')})",
                        f"  - Original HTML: `{entry.get('original_html_evidence', '')}`",
                    ])
                else:
                    llm = entry.get("ollama", entry)
                    lines.append(f"- `{llm.get('element_type')} — {llm.get('original_text', '')}`; {entry.get('reason', '')}")
                    if llm.get("original_html_evidence"):
                        lines.append(f"  - Original HTML: `{llm['original_html_evidence']}`")
                    for candidate in entry.get("python_candidates", []):
                        lines.append(f"  - Python candidate: `{candidate.get('kind')} / {candidate.get('speaker') or '—'} — {candidate.get('text', '')}`")
                    for conflict in entry.get("conflicting_ollama", []):
                        lines.append(f"  - Conflicting Ollama label: `{conflict.get('speaker') or '—'} / {conflict.get('normalized_speaker') or '—'}; uncertainty={conflict.get('uncertainty')!r}`")

    lines.extend(["", "## Ollama failures or omitted responses", ""])
    if result["llm_failures_or_omissions"]:
        lines.extend(f"- {failure}" for failure in result["llm_failures_or_omissions"])
    else:
        lines.append("None.")
    return "\n".join(lines) + "\n"
