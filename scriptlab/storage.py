"""SQLite storage for normalized lines, HTML layout evidence, and parser decisions."""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY,
    series TEXT NOT NULL,
    season INTEGER NOT NULL,
    episode INTEGER NOT NULL,
    source_type TEXT NOT NULL,
    path TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    encoding TEXT NOT NULL,
    format_profile_json TEXT NOT NULL,
    UNIQUE(series, season, episode, source_type)
);
CREATE TABLE IF NOT EXISTS script_lines (
    episode_id INTEGER NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    line_no INTEGER NOT NULL,
    source_line INTEGER NOT NULL,
    raw_text TEXT NOT NULL,
    layout TEXT NOT NULL DEFAULT 'txt',
    group_id INTEGER,
    parallel_row INTEGER,
    parallel_column INTEGER,
    br_run_before INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (episode_id, line_no)
);
CREATE TABLE IF NOT EXISTS elements (
    episode_id INTEGER NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    line_no INTEGER NOT NULL,
    kind TEXT NOT NULL,
    text TEXT NOT NULL,
    scene_index INTEGER NOT NULL,
    speaker TEXT,
    evidence_json TEXT NOT NULL,
    act_index INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (episode_id, line_no)
);
CREATE TABLE IF NOT EXISTS dialogue_turns (
    id INTEGER PRIMARY KEY,
    episode_id INTEGER NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    speaker TEXT NOT NULL,
    cue TEXT,
    act_index INTEGER NOT NULL,
    scene_index INTEGER NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    dialogue_text TEXT NOT NULL,
    segments_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_turns_speaker ON dialogue_turns(speaker);
CREATE TABLE IF NOT EXISTS issues (
    id INTEGER PRIMARY KEY,
    episode_id INTEGER NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    severity TEXT NOT NULL,
    kind TEXT NOT NULL,
    line_no INTEGER,
    message TEXT NOT NULL,
    candidates_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_elements_kind ON elements(kind);
CREATE INDEX IF NOT EXISTS idx_elements_speaker ON elements(speaker);
"""


def _upgrade_schema(conn: sqlite3.Connection) -> None:
    """Upgrade an existing starter SQLite file without discarding saved episodes."""
    for table, column, definition in [
        ("script_lines", "layout", "TEXT NOT NULL DEFAULT 'txt'"),
        ("script_lines", "group_id", "INTEGER"),
        ("script_lines", "parallel_row", "INTEGER"),
        ("script_lines", "parallel_column", "INTEGER"),
        ("script_lines", "br_run_before", "INTEGER NOT NULL DEFAULT 0"),
        ("elements", "act_index", "INTEGER NOT NULL DEFAULT 0"),
    ]:
        present = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        if column not in present:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def save_parsed(db_path: str | Path, parsed: dict) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ep = parsed["episode"]
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.executescript(SCHEMA)
        _upgrade_schema(conn)
        conn.execute("PRAGMA foreign_keys=ON")
        row = conn.execute(
            "SELECT id, path FROM episodes WHERE series=? AND season=? AND episode=? AND source_type=?",
            (ep["series"], ep["season"], ep["episode"], ep["source_type"]),
        ).fetchone()
        if row is not None and Path(row[1]).resolve() != Path(ep["path"]).resolve():
            raise ValueError(f"Episode identity already belongs to another file: {row[1]}")
        if row is None:
            cur = conn.execute("INSERT INTO episodes "
                               "(series,season,episode,source_type,path,source_hash,encoding,format_profile_json) "
                               "VALUES (?,?,?,?,?,?,?,?)",
                               (ep["series"], ep["season"], ep["episode"], ep["source_type"], ep["path"],
                                ep["sha256"], ep["encoding"], json.dumps(parsed["profile"])))
            episode_id = cur.lastrowid
        else:
            episode_id = row[0]
            conn.execute("UPDATE episodes SET source_hash=?,encoding=?,format_profile_json=? WHERE id=?",
                         (ep["sha256"], ep["encoding"], json.dumps(parsed["profile"]), episode_id))
            for table in ("issues", "dialogue_turns", "elements", "script_lines"):
                conn.execute(f"DELETE FROM {table} WHERE episode_id=?", (episode_id,))
        conn.executemany("INSERT INTO script_lines "
                         "(episode_id,line_no,source_line,raw_text,layout,group_id,parallel_row,parallel_column,br_run_before) VALUES (?,?,?,?,?,?,?,?,?)", [
            (episode_id, l["line"], l["source_line"], l["text"], l.get("layout", "txt"), l.get("group_id"),
             l.get("parallel_row"), l.get("parallel_column"), l.get("br_run_before", 0))
            for l in parsed["lines"]
        ])
        conn.executemany("INSERT INTO elements "
                         "(episode_id,line_no,kind,text,scene_index,speaker,evidence_json,act_index) "
                         "VALUES (?,?,?,?,?,?,?,?)", [
            (episode_id, e["line"], e["kind"], e["text"], e["scene_index"],
             e["speaker"], json.dumps(e["evidence"]), e.get("act_index", 0))
            for e in parsed["elements"]
        ])
        conn.executemany("INSERT INTO dialogue_turns "
                         "(episode_id,speaker,cue,act_index,scene_index,start_line,end_line,dialogue_text,segments_json) "
                         "VALUES (?,?,?,?,?,?,?,?,?)", [
            (episode_id, t["speaker"], t["cue"], t["act_index"], t["scene_index"],
             t["start_line"], t["end_line"], t["text"], json.dumps(t["segments"]))
            for t in parsed.get("dialogue_turns", [])
        ])
        conn.executemany("INSERT INTO issues "
                         "(episode_id,severity,kind,line_no,message,candidates_json) VALUES (?,?,?,?,?,?)", [
            (episode_id, i["severity"], i["kind"], i["line"], i["message"], json.dumps(i.get("candidates", [])))
            for i in parsed["issues"]
        ])
