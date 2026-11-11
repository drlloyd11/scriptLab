"""Small, serializable data models shared by the pipeline."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class EpisodeFile:
    series: str
    season: int
    episode: int
    path: Path
    source_type: str = "canonical"

    @property
    def key(self) -> str:
        return f"{self.series}/S{self.season:02d}E{self.episode:02d}"


@dataclass(frozen=True)
class ScriptLine:
    line: int                 # 1-based normalized line number
    text: str                 # whitespace preserved
    source_line: int          # original file line (best effort for HTML)
    layout: str = "txt"       # txt, pre, html_center, html_paragraph, html_text
    group_id: int | None = None  # <BR> lines belonging to one HTML dialogue turn
    parallel_row: int | None = None  # HTML table row with simultaneous speakers
    parallel_column: int | None = None  # cell position within that row
    br_run_before: int = 0  # consecutive <BR> tags preceding text; 2+ may introduce a new speaker

    @property
    def indent(self) -> int:
        return len(self.text.expandtabs(8)) - len(self.text.expandtabs(8).lstrip(" "))

    @property
    def stripped(self) -> str:
        return self.text.strip()


@dataclass
class Document:
    episode: EpisodeFile
    source_hash: str
    encoding: str
    lines: list[ScriptLine]
    reader_warnings: list[str] = field(default_factory=list)


@dataclass
class Element:
    line: int
    source_line: int
    kind: str
    text: str
    scene_index: int
    speaker: str | None = None
    evidence: list[str] = field(default_factory=list)
    act_index: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Issue:
    kind: str
    message: str
    line: int | None = None
    severity: str = "warning"
    candidates: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
