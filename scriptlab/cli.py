"""`python -m scriptlab` command-line interface."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .catalog import gaps_within_discovered_ranges, scan_sources
from .comparator import compare_labels, independent_llm_labels
from .llm import OllamaError, list_ollama_models
from .grammar_inference import infer_grammar
from .html_verifier import DEFAULT_MODEL, compare_raw_html
from .models import EpisodeFile
from .parser import parse_document
from .readers import decode_source, read_episode
from .reports import comparison_report, parse_report, raw_html_verification_report
from .storage import save_parsed
from .validator import validate_parsed


def json_file(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def text_file(path: Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")


def options() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python -m scriptlab", description="Source-preserving script parsing and optional LLM audit")
    commands = ap.add_subparsers(dest="command", required=True)

    scan = commands.add_parser("scan", help="Inventory input files before parsing")
    scan.add_argument("--series", nargs=2, action="append", required=True, metavar=("NAME", "DIRECTORY"))
    scan.add_argument("--source-type", choices=["canonical", "fanfiction"], default="canonical")
    scan.add_argument("--extensions", nargs="+", choices=["txt", "html", "htm"])

    parse = commands.add_parser("parse", help="Parse a corpus to JSON, Markdown reports, and SQLite")
    parse.add_argument("--series", nargs=2, action="append", required=True, metavar=("NAME", "DIRECTORY"))
    parse.add_argument("--source-type", choices=["canonical", "fanfiction"], default="canonical")
    parse.add_argument("--extensions", nargs="+", choices=["txt", "html", "htm"])
    parse.add_argument("--out", default="output")
    parse.add_argument("--fail-on-ambiguity", action="store_true", help="Exit nonzero when unknown lines or provisional scene-heading warnings remain")

    compare = commands.add_parser("compare", help="Independent Ollama structural read vs saved Python parse")
    compare.add_argument("--parsed", required=True, help="Path to a .json file from `parse`")
    compare.add_argument("--model", required=True, help="Installed Ollama model, e.g. qwen3:8b")
    compare.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    compare.add_argument("--chunk-size", type=int, default=45)
    compare.add_argument("--out", help="Output report prefix (without extension)")
    compare.add_argument("--line-start", type=int, help="First normalized line to verify, inclusive")
    compare.add_argument("--line-end", type=int, help="Last normalized line to verify, inclusive")

    verify_html = commands.add_parser(
        "verify-html", help="Compare deterministic parsing with an independent Ollama reading of original HTML"
    )
    verify_html.add_argument("--script", required=True, help="Original .html/.htm source file")
    verify_html.add_argument("--model", default=DEFAULT_MODEL, help=f"Installed local Ollama model (default: {DEFAULT_MODEL})")
    verify_html.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    verify_html.add_argument("--out", required=True, help="Output prefix for .verification.json and .verification.md")
    verify_html.add_argument("--max-fragment-chars", type=int, default=5000)
    verify_html.add_argument("--overlap-chars", type=int, default=400)
    verify_html.add_argument("--start-line", type=int, help="Pilot: first physical source line, inclusive")
    verify_html.add_argument("--end-line", type=int, help="Pilot: last physical source line, inclusive")
    verify_html.add_argument("--start-offset", type=int, help="Pilot: first zero-based source character offset, inclusive")
    verify_html.add_argument("--end-offset", type=int, help="Pilot: last zero-based source character offset, exclusive")

    preflight = commands.add_parser("check-ollama", help="Check local Ollama and confirm a model is installed")
    preflight.add_argument("--model", required=True, help="Model name as shown by ollama list")
    preflight.add_argument("--ollama-url", default="http://127.0.0.1:11434")

    infer = commands.add_parser("infer-format", help="Have Ollama propose an evidence-backed format grammar")
    infer.add_argument("--series", nargs=2, action="append", required=True, metavar=("NAME", "DIRECTORY"))
    infer.add_argument("--extensions", nargs="+", choices=["txt", "html", "htm"])
    infer.add_argument("--model", required=True)
    infer.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    infer.add_argument("--sample-limit", type=int, default=4)
    infer.add_argument("--max-lines", type=int, default=180)
    infer.add_argument("--out", default="output/inferred_format.json")
    return ap


def run(argv: list[str] | None = None) -> int:
    opts = options().parse_args(argv)
    if opts.command == "verify-html":
        path = Path(opts.script)
        if path.suffix.lower() not in {".htm", ".html"}:
            print("[error] verify-html accepts only original .htm/.html sources.", file=sys.stderr)
            return 2
        if opts.max_fragment_chars < 256 or opts.overlap_chars < 0 or opts.overlap_chars >= opts.max_fragment_chars:
            raise SystemExit("--max-fragment-chars must be >=256 and --overlap-chars must be smaller and nonnegative")
        if (opts.start_line is None) != (opts.end_line is None):
            raise SystemExit("--start-line and --end-line must be supplied together")
        if (opts.start_offset is None) != (opts.end_offset is None):
            raise SystemExit("--start-offset and --end-offset must be supplied together")
        if opts.start_line is not None and opts.start_offset is not None:
            raise SystemExit("Use either physical-line or character-offset pilot selection, not both")
        if opts.start_line is not None and (opts.start_line < 1 or opts.end_line < opts.start_line):
            raise SystemExit("Source line range must be positive and ordered")
        if opts.start_offset is not None and (opts.start_offset < 0 or opts.end_offset <= opts.start_offset):
            raise SystemExit("Character offset range must be nonnegative and ordered")
        try:
            raw_bytes = path.read_bytes()
            raw_html, _, _ = decode_source(raw_bytes)
            parsed = parse_document(read_episode(EpisodeFile("source", 0, 0, path)))
            result = compare_raw_html(
                raw_html, parsed, path, parsed["episode"]["sha256"], opts.model,
                opts.ollama_url, opts.max_fragment_chars, opts.overlap_chars,
                opts.start_line, opts.end_line, opts.start_offset, opts.end_offset,
            )
        except (OSError, ValueError) as error:
            print(f"[error] HTML verification failed: {error}", file=sys.stderr)
            return 2
        prefix = Path(opts.out)
        json_file(Path(str(prefix) + ".verification.json"), result)
        text_file(Path(str(prefix) + ".verification.md"), raw_html_verification_report(result))
        print(
            f"Verified {result['source_filename']}: {result['elements_examined']} independent elements; "
            f"{result['agreement_count']} agreements, "
            f"{len(result['classification_disagreements'])} classification disagreements, "
            f"{result['items_needing_human_review']} items need human review."
        )
        print(f"Wrote {prefix}.verification.json and {prefix}.verification.md")
        return 2 if result["llm_failures_or_omissions"] or not result["elements_examined"] else 0

    if opts.command in {"scan", "parse", "infer-format"}:
        episode_files, inventory_issues = scan_sources(
            opts.series,
            getattr(opts, "source_type", "canonical"),
            getattr(opts, "extensions", None),
        )
        for issue in inventory_issues:
            print(f"[{issue.severity}] {issue.kind}: {issue.message}", file=sys.stderr)
        print(f"Discovered {len(episode_files)} unambiguous episode files.")
        for warning in gaps_within_discovered_ranges(episode_files):
            print("[gap]", warning)
        if opts.command == "scan":
            for ep in episode_files:
                print(f"{ep.key:<20} {ep.path}")
            return 2 if any(i.severity == "error" for i in inventory_issues) else 0
        if not episode_files:
            print("No usable episode files found.", file=sys.stderr)
            return 2
        if opts.command == "infer-format":
            if opts.sample_limit <= 0 or opts.max_lines <= 0:
                raise SystemExit("--sample-limit and --max-lines must be positive")
            docs = [read_episode(ep) for ep in episode_files[:opts.sample_limit]]
            grammar = infer_grammar(docs, opts.model, opts.ollama_url, opts.max_lines)
            json_file(Path(opts.out), grammar)
            print(f"Wrote proposed (unverified) grammar: {opts.out}")
            return 2 if any(i.severity == "error" for i in inventory_issues) else 0
        out = Path(opts.out)
        failed = bool(any(i.severity == "error" for i in inventory_issues))
        unresolved = 0
        provisional = 0
        for ep in episode_files:
            try:
                parsed = parse_document(read_episode(ep))
                parsed["issues"].extend(validate_parsed(parsed))
                if any(i["severity"] == "error" for i in parsed["issues"]):
                    failed = True
                unresolved += sum(e["kind"] == "unknown" for e in parsed["elements"])
                provisional += sum(e["kind"] == "suspected_scene_heading" for e in parsed["elements"])
                base = out / ep.series / f"S{ep.season:02}E{ep.episode:02}"
                json_file(base.with_suffix(".json"), parsed)
                text_file(base.with_suffix(".report.md"), parse_report(parsed))
                save_parsed(out / "scriptlab.sqlite", parsed)
                print(f"Parsed {ep.key}: {len(parsed['elements'])} elements; {len(parsed['issues'])} issues")
            except (OSError, ValueError) as error:
                failed = True
                print(f"[error] Failed {ep.key}: {error}", file=sys.stderr)
        print(f"Output directory: {out.resolve()}")
        if unresolved:
            print(f"Unresolved structural lines: {unresolved}")
        if provisional:
            print(f"Provisional scene headings needing review: {provisional}")
        if opts.fail_on_ambiguity and (unresolved or provisional):
            failed = True
        return 2 if failed else 0
    if opts.command == "check-ollama":
        try:
            models = list_ollama_models(opts.ollama_url)
        except OllamaError as error:
            print(f"[error] {error}", file=sys.stderr)
            print("Start Ollama locally, then retry.", file=sys.stderr)
            return 2
        if opts.model not in models:
            print(f"[error] Requested model {opts.model!r} is not installed.", file=sys.stderr)
            print("Installed models: " + (", ".join(models) if models else "(none)"), file=sys.stderr)
            print(f"To install the requested model, run: ollama pull {opts.model}", file=sys.stderr)
            return 2
        print(f"Ollama is reachable; model {opts.model!r} is installed.")
        return 0
    if opts.command == "compare":
        if opts.chunk_size <= 0:
            raise SystemExit("--chunk-size must be positive")
        if opts.line_start is not None and opts.line_start < 1:
            raise SystemExit("--line-start must be positive")
        if opts.line_end is not None and opts.line_end < 1:
            raise SystemExit("--line-end must be positive")
        if (opts.line_start is not None and opts.line_end is not None
                and opts.line_start > opts.line_end):
            raise SystemExit("--line-start must not exceed --line-end")
        path = Path(opts.parsed)
        parsed = json.loads(path.read_text(encoding="utf-8"))
        targets = {e["line"] for e in parsed["elements"]
                   if (opts.line_start is None or e["line"] >= opts.line_start)
                   and (opts.line_end is None or e["line"] <= opts.line_end)}
        if not targets:
            print("[error] No parsed nonblank lines in requested range", file=sys.stderr)
            return 2
        labels, failures = independent_llm_labels(
            parsed, opts.model, opts.ollama_url, opts.chunk_size,
            line_start=opts.line_start, line_end=opts.line_end)
        comparison = compare_labels(parsed, labels, opts.model, failures, target_lines=targets)
        prefix = Path(opts.out) if opts.out else path.with_suffix("")
        json_file(Path(str(prefix) + ".comparison.json"), comparison)
        json_file(Path(str(prefix) + ".llm_labels.json"), {
            "episode_key": comparison["episode_key"],
            "source_sha256": comparison["source_sha256"],
            "model": opts.model,
            "line_start": comparison["target_line_start"],
            "line_end": comparison["target_line_end"],
            "labels": [{"line": line, **label} for line, label in sorted(labels.items())],
            "failures": failures,
        })
        text_file(Path(str(prefix) + ".comparison.md"), comparison_report(comparison))
        print(f"Requested {comparison['requested_lines']} lines, obtained {comparison['compared_lines']} labels: "
              f"{comparison['agreements']} agree, {len(comparison['disagreements'])} disagree, "
              f"{comparison['unreviewed_lines']} unreviewed")
        return 2 if comparison["llm_failures"] else 0
    return 1
