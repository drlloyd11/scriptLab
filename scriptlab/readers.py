"""Read TXT/HTML scripts preserving physical layout evidence and source provenance.

HTML <CENTER> plus <BR> is structural data, NOT cosmetic spacing. In the
School Hard HTML family a centered block starts with a speaker cue and each
subsequent <BR>-delimited line contains spoken words or a parenthetical.
"""
from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser
from .models import Document, EpisodeFile, ScriptLine


def decode_source(data: bytes) -> tuple[str, str, list[str]]:
    warnings = []
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            text = data.decode(encoding)
            if encoding == "cp1252":
                warnings.append("Source decoded as Windows-1252; verify unusual characters.")
            return text, encoding, warnings
        except UnicodeDecodeError:
            pass
    warnings.append("Source required Latin-1 fallback; character encoding may be wrong.")
    return data.decode("latin-1"), "latin-1", warnings


def malformed_html_warnings(source: str) -> list[str]:
    """Report malformed nested tag openers with their physical source lines."""
    warnings = []
    for match in re.finditer(r"<([A-Za-z][A-Za-z0-9]*)\s*<", source):
        source_line = source.count("\n", 0, match.start()) + 1
        warnings.append(
            f"Malformed HTML tag opener near source line {source_line}; review original markup."
        )
    return warnings


class HTMLScriptExtractor(HTMLParser):
    """Create logical lines annotated with HTML provenance.

    Blocks share a group_id across their <BR> lines, which lets the parser
    distinguish a dialogue block from left-aligned shot headings. Source
    line positions point near the original text, not to fabricated layout.
    The original HTML remains on disk and is identified by a source hash.
    """
    BLOCKS = {"p", "div", "section", "article", "tr", "td", "li",
              "h1", "h2", "h3", "h4", "blockquote", "center", "pre"}
    SKIP = {"head", "script", "style", "nav", "footer"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.records: list[tuple[str, int, str, int | None, int | None, int | None, int]] = []
        self.parts: list[str] = []
        self.current_origin: int | None = None
        self.current_layout: str | None = None
        self.current_group: int | None = None
        self.current_parallel_row: int | None = None
        self.current_parallel_column: int | None = None
        self.current_br_run_before = 0
        self.br_run = 0
        self.stack: list[dict] = []
        self.next_group = 0
        self.skip_depth = 0
        self.pre_depth = 0
        self.warnings: list[str] = []

    def _context(self) -> tuple[str, int | None, int | None, int | None]:
        if self.pre_depth:
            item = next((s for s in reversed(self.stack) if s["tag"] == "pre"), None)
            return "pre", item["id"] if item else None, None, None
        # All text inside a genuine dialogue <CENTER> is dialogue-oriented.
        # New <P> inside that center starts a new speaker turn, even though
        # vintage HTML frequently omits closing </P> tags.
        dialogue_centers = [
            i for i, item in enumerate(self.stack)
            if ((item["tag"] == "center" and not item.get("wrapper"))
                or (item["tag"] == "p" and item.get("align") in {"center", "middle"}))
        ]
        if dialogue_centers:
            center_pos = dialogue_centers[-1]
            group = self.stack[center_pos]["id"]
            for item in self.stack[center_pos + 1:]:
                if item["tag"] in {"td", "p"}:
                    group = item["id"]
            # Concurrent dialogue often appears as a two-column table.
            # Track a shared row ID and column; don't confuse DOM order with
            # actual utterance timing.
            row = None
            col = None
            for item in self.stack[center_pos + 1:]:
                if item["tag"] == "tr" and item.get("dialogue_table"):
                    row = item["id"]
                if item["tag"] == "td" and row is not None:
                    col = item.get("column", 1)
            return "html_center", group, row, col
        for item in reversed(self.stack):
            if item["tag"] in {"p", "td", "div", "blockquote", "h1", "h2", "h3", "h4"}:
                return "html_paragraph", item["id"], None, None
        return "html_text", None, None, None

    def _emit(self) -> None:
        if not self.parts:
            return
        text = "".join(self.parts)
        if text.strip():
            self.records.append((text.strip() if self.current_layout != "pre" else text,
                                 self.current_origin or 1,
                                 self.current_layout or "html_text", self.current_group,
                                 self.current_parallel_row, self.current_parallel_column, self.current_br_run_before))
        self.parts = []
        self.current_origin = None
        self.current_layout = None
        self.current_group = None
        self.current_parallel_row = None
        self.current_parallel_column = None
        self.current_br_run_before = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag in self.SKIP:
            self.skip_depth += 1
        if self.skip_depth:
            return
        if tag == "table":
            width = next((str(v) for (k, v) in attrs if k.lower() == "width"), "")
            # An outer 85%-wide page table uses a center for page layout;
            # narrow nested tables in the dialogue are parallel speakers.
            width_value = width.rstrip("%")
            in_dialogue_center = any(
                x["tag"] == "center" and not x.get("wrapper") for x in self.stack
            )
            has_cell_ancestor = any(x["tag"] == "td" for x in self.stack)
            is_narrow = width_value.isdigit() and int(width_value) < 80
            is_outer = ((width_value.isdigit() and int(width_value) >= 80) or
                        (not has_cell_ancestor and not (in_dialogue_center and is_narrow)))
            if is_outer:
                for item in self.stack:
                    if item["tag"] == "center":
                        item["wrapper"] = True
            self._emit()
            self.next_group += 1
            self.stack.append({"tag": "table", "id": self.next_group,
                               "dialogue_table": not is_outer and any(
                                   x["tag"] == "center" and not x.get("wrapper")
                                   for x in self.stack)})
        if tag == "tr":
            dialogue_table = any(x["tag"] == "table" and x.get("dialogue_table") for x in self.stack)
            self._emit()
            self.next_group += 1
            self.stack.append({"tag": "tr", "id": self.next_group,
                               "dialogue_table": dialogue_table, "td_count": 0})
        elif tag in self.BLOCKS:
            self._emit()
            self.next_group += 1
            item = {"tag": tag, "id": self.next_group, "wrapper": False}
            alignment = next((str(value).lower() for key, value in attrs
                              if key.lower() == "align"), None)
            if alignment in {"center", "middle"}:
                item["align"] = alignment
            if tag == "td":
                row = next((x for x in reversed(self.stack) if x["tag"] == "tr"), None)
                if row:
                    row["td_count"] += 1
                    item["column"] = row["td_count"]
            self.stack.append(item)
        if tag == "pre":
            self.pre_depth += 1
        if tag == "br":
            self._emit()
            self.br_run += 1
        elif tag in self.BLOCKS or tag == "table":
            self.br_run = 0

    def handle_startendtag(self, tag: str, attrs) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() != "br":
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.SKIP:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.skip_depth:
            return
        if tag in self.BLOCKS or tag == "table":
            self._emit()
            self.br_run = 0
            # Some vintage HTML has misnested tags: close only matching blocks.
            for pos in range(len(self.stack) - 1, -1, -1):
                if self.stack[pos]["tag"] == tag:
                    self.stack.pop(pos)
                    break
        if tag == "pre":
            self.pre_depth = max(0, self.pre_depth - 1)

    def handle_data(self, data: str) -> None:
        if self.skip_depth or not data:
            return
        line_number = self.getpos()[0]
        if self.pre_depth:
            cleaned = data.replace("\r\n", "\n").replace("\r", "\n")
            for i, part in enumerate(cleaned.split("\n")):
                if i:
                    self._emit()
                if part:
                    self._append(part, line_number + i)
            return
        # Spaces inside markup are just HTML source formatting, not dialogue
        # indentation. <BR>, paragraph and CENTER boundaries carry layout.
        cleaned = re.sub(r"\s+", " ", data)
        if cleaned.strip():
            self._append(cleaned, line_number)

    def _append(self, text: str, origin: int) -> None:
        if self.current_origin is None:
            self.current_origin = origin
            (self.current_layout, self.current_group, self.current_parallel_row,
             self.current_parallel_column) = self._context()
        if not self.parts:
            self.current_br_run_before = self.br_run
            self.br_run = 0
        self.parts.append(text)

    def lines(self) -> list[ScriptLine]:
        self._emit()
        return [ScriptLine(n, text, origin, layout, group, row, column, br_run)
                for n, (text, origin, layout, group, row, column, br_run) in enumerate(self.records, 1)]


def read_episode(episode: EpisodeFile) -> Document:
    raw = episode.path.read_bytes()
    source_hash = hashlib.sha256(raw).hexdigest()
    decoded, encoding, warnings = decode_source(raw)
    if episode.path.suffix.lower() in {".html", ".htm"}:
        warnings.extend(malformed_html_warnings(decoded))
        extractor = HTMLScriptExtractor()
        extractor.feed(decoded)
        extractor.close()
        lines = extractor.lines()
        warnings.extend(extractor.warnings)
        if not any(l.layout == "html_center" for l in lines) and "<pre" not in decoded.lower():
            warnings.append("HTML has no recognized centered dialogue or <pre>: validate this format family.")
    else:
        lines = [ScriptLine(i, text, i, "txt", None) for i, text in enumerate(decoded.splitlines(), 1)]
    return Document(episode, source_hash, encoding, lines, warnings)
