"""Discover episode files; never guess at duplicate or unrecognized IDs."""
from __future__ import annotations

import re
from pathlib import Path
from .models import EpisodeFile, Issue

PATTERNS = [
    re.compile(r"(?i)(?<![a-z0-9])s(?P<season>\d{1,2})\s*e(?P<episode>\d{1,3})(?![0-9])"),
    re.compile(r"(?i)(?<![0-9])(?P<season>\d{1,2})\s*x\s*(?P<episode>\d{1,3})(?![0-9])"),
    re.compile(r"(?i)season[_\s-]*(?P<season>\d{1,2})[_\s-]*episode[_\s-]*(?P<episode>\d{1,3})"),
]


def parse_episode_filename(filename: str) -> tuple[int, int] | None:
    stem = Path(filename).stem
    matches = {(int(m.group("season")), int(m.group("episode")))
               for pattern in PATTERNS for m in pattern.finditer(stem)}
    if len(matches) != 1:
        return None
    season, episode = next(iter(matches))
    return (season, episode) if 0 <= season <= 99 and 1 <= episode <= 999 else None


def scan_sources(
    series_directories: list[tuple[str, str]],
    source_type: str = "canonical",
    extensions: list[str] | None = None,
) -> tuple[list[EpisodeFile], list[Issue]]:
    episodes: list[EpisodeFile] = []
    issues: list[Issue] = []
    seen: dict[tuple[str, int, int], Path] = {}
    allowed_extensions = {
        extension.lower().lstrip(".")
        for extension in (extensions or ["txt", "html", "htm"])
    }
    for series, directory in series_directories:
        path = Path(directory).expanduser()
        if not path.is_dir():
            issues.append(Issue("missing_directory", f"Directory not found: {path}", severity="error"))
            continue
        for file in sorted(path.rglob("*")):
            if not file.is_file() or file.suffix.lower().lstrip(".") not in allowed_extensions:
                continue
            identity = parse_episode_filename(file.name)
            if identity is None:
                issues.append(Issue("ambiguous_filename", f"No unique season/episode in: {file}"))
                continue
            season, ep = identity
            key = (series.lower(), season, ep)
            if key in seen:
                issues.append(Issue("duplicate_episode", f"Collision {series} S{season:02}E{ep:02}: {seen[key]} AND {file}", severity="error"))
                # Do not process either file: a collision must be resolved by a human.
                episodes = [existing for existing in episodes if (existing.series.lower(), existing.season, existing.episode) != key]
                continue
            seen[key] = file
            episodes.append(EpisodeFile(series.lower(), season, ep, file, source_type))
    episodes.sort(key=lambda e: (e.series, e.season, e.episode))
    return episodes, issues


def gaps_within_discovered_ranges(episodes: list[EpisodeFile]) -> list[str]:
    """Not a broadcast checklist: only identifies holes between supplied episode numbers."""
    seasons: dict[tuple[str, int], set[int]] = {}
    for ep in episodes:
        seasons.setdefault((ep.series, ep.season), set()).add(ep.episode)
    result = []
    for (series, season), numbers in sorted(seasons.items()):
        missing = sorted(set(range(min(numbers), max(numbers) + 1)) - numbers)
        if missing:
            result.append(f"{series} S{season:02}: gaps within discovered range: {missing}")
    return result
