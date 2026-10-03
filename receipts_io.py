"""Offline, streaming readers and an on-disk index for the receipt checker."""

from __future__ import annotations

import datetime as dt
import gzip
import json
import math
import re
import sqlite3
import tempfile
from itertools import islice
from pathlib import Path
from typing import Any, Iterator, TextIO


DEFAULT_FIELD_MAP = {
    "chat_messages": {
        "agent": "speaker", "text": "content", "time": "timestamp",
        "session": None, "action": None, "output": None,
    },
    "agent_memories": {
        "agent": "agent", "text": "content", "time": "timestamp",
        "session": None, "action": None, "output": None,
    },
    "computer_use_sessions": {
        "agent": "agent", "text": "session_goal", "time": "timestamp",
        "session": "session_id", "action": None, "output": None,
    },
    "computer_use_turns": {
        "agent": "agent", "text": "agent_messages", "time": "timestamp",
        "session": "session_id", "action": "agent_action", "output": "tool_output",
    },
    "events": {
        "agent": "data.agent", "text": "data.content", "time": "timestamp",
        "session": "data.session_id", "action": "actionType", "output": "data.tool_output",
    },
    "summaries": {
        "agent": "agent", "text": "content", "time": "timestamp",
        "session": None, "action": None, "output": None,
    },
    "agent_goals": {
        "agent": "agent", "text": "content", "time": "timestamp",
        "session": None, "action": None, "output": None,
    },
}

_SENSITIVE_FIELDS = re.compile(
    r"^(?:api[_-]?key|access[_-]?token|refresh[_-]?token|auth[_-]?token|"
    r"token|password|passwd|secret|client[_-]?secret|private[_-]?key|"
    r"credentials?|authorization|cookies?|set-cookie)$", re.I,
)
_SENSITIVE_TEXT = re.compile(
    r"(?i)\b((?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|"
    r"passwd|client[_-]?secret|authorization|token)\s*[:=]\s*)"
    r"(?:\"[^\"]*\"|'[^']*'|[^\s,;}]+)",
)
_BEARER = re.compile(r"(?i)\bBearer\s+[^\s\"'<>]+")
_PRIVATE_KEY = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
    re.S,
)
_TOKEN_SHAPES = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,})\b")
_CONFIDENTIAL_MARKER = re.compile(
    r"(?im)^\s*(?:#+\s*)?\[?confidential\]?(?:\s*[:\-]|\s*$)"
)
_STOP_WORDS = frozenset(
    "a an the and or but for to of in on at by with from is are was were be been "
    "i me my we our you your he she it they their this that these those have has "
    "had do did done finish finished complete completed sent send posted post "
    "published publish deployed deploy fixed fix saved save submitted submit "
    "success successful successfully now just already session goal agent".split()
)


def normalize_source(source: str) -> str:
    """Accept a known source basename or either JSONL filename spelling."""
    name = Path(source).name
    if name.endswith(".gz"):
        name = name[:-3]
    if name.endswith(".jsonl"):
        name = name[:-6]
    return name


def load_field_map(path: str | Path | None = None) -> dict[str, dict[str, str | None]]:
    """Merge an optional JSON map into the published, provisional defaults."""
    result = {source: dict(mapping) for source, mapping in DEFAULT_FIELD_MAP.items()}
    if path is None:
        return result
    path = Path(path)
    if ".env" in path.name.lower() or "confidential" in path.name.lower():
        raise ValueError("Refusing to open a protected configuration filename")
    with path.open(encoding="utf-8") as handle:
        overrides = json.load(handle)
    if not isinstance(overrides, dict):
        raise ValueError("Field map must be a JSON object keyed by source basename")
    for source, mapping in overrides.items():
        name = normalize_source(source)
        if name not in result:
            raise ValueError("Unknown field-map source: " + name)
        if not isinstance(mapping, dict):
            raise ValueError("Field map for " + name + " must be an object")
        for logical, real in mapping.items():
            if logical not in result[name]:
                raise ValueError("Unknown logical field: " + str(logical))
            if real is not None and (not isinstance(real, str) or not real.strip()):
                raise ValueError("Field paths must be nonempty strings or null")
            result[name][logical] = real
    return result


def _field(row: dict[str, Any], path: str | None) -> Any:
    if path is None:
        return None
    # A literal key takes priority over dotted traversal.
    if path in row:
        return row[path]
    current: Any = row
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdecimal():
            index = int(part)
            current = current[index] if index < len(current) else None
        else:
            return None
    return current


def safe_value(value: Any) -> Any:
    """Remove credential values before retaining or displaying record content."""
    if isinstance(value, dict):
        return {
            key: "[redacted]" if _SENSITIVE_FIELDS.fullmatch(str(key)) else safe_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [safe_value(item) for item in value]
    if isinstance(value, str):
        value = _PRIVATE_KEY.sub("[redacted]", value)
        value = _BEARER.sub("Bearer [redacted]", value)
        value = _SENSITIVE_TEXT.sub(lambda match: match.group(1) + "[redacted]", value)
        return _TOKEN_SHAPES.sub("[redacted]", value)
    return value


def _is_confidential(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            name = str(key).lower().replace("_", "").replace("-", "")
            if name in {"confidential", "isconfidential"} and item not in (False, None, "", 0):
                return True
            if name in {"classification", "confidentiality", "sensitivity"} and isinstance(item, str):
                if item.strip().lower() == "confidential":
                    return True
            if _is_confidential(item):
                return True
    elif isinstance(value, list):
        return any(_is_confidential(item) for item in value)
    elif isinstance(value, str):
        return bool(_CONFIDENTIAL_MARKER.search(value))
    return False


def source_path(data_dir: str | Path, source: str) -> Path | None:
    name = normalize_source(source)
    if name not in DEFAULT_FIELD_MAP:
        raise ValueError("Unknown source: " + name)
    directory = Path(data_dir)
    for suffix in (".jsonl.gz", ".jsonl"):
        path = directory / (name + suffix)
        if path.is_file():
            return path
    return None


def _raw_rows(path: Path, limit: int | None = None) -> Iterator[tuple[int, dict[str, Any]]]:
    if limit is not None and limit < 0:
        raise ValueError("limit must be nonnegative")
    opener = gzip.open if path.name.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as handle:
        lines = islice(handle, limit) if limit is not None else handle
        for line_number, line in enumerate(lines, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Malformed JSON at {path.name}:{line_number}: {error.msg}") from None
            if not isinstance(row, dict):
                raise ValueError(f"Expected a JSON object at {path.name}:{line_number}")
            if _is_confidential(row):
                continue
            yield line_number, safe_value(row)


def iter_source(
    data_dir: str | Path,
    source_name: str,
    field_map: dict[str, dict[str, str | None]] | None = None,
    limit: int | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield mapped rows without loading a source into memory."""
    source = normalize_source(source_name)
    path = source_path(data_dir, source)
    if path is None:
        return
    mapping = (field_map or DEFAULT_FIELD_MAP)[source]
    for line_number, row in _raw_rows(path, limit):
        mapped = {logical: _field(row, real) for logical, real in mapping.items()}
        mapped.update(source=path.name, row_id=f"{path.name}:{line_number}")
        yield mapped


def parse_timestamp(value: Any) -> float | None:
    """Parse ISO 8601 or epoch seconds/milliseconds; naive ISO times mean UTC."""
    if value is None or isinstance(value, bool):
        return None
    try:
        if isinstance(value, (int, float)) or (
            isinstance(value, str) and re.fullmatch(r"[+-]?\d+(?:\.\d+)?", value.strip())
        ):
            stamp = float(value)
            if abs(stamp) >= 100_000_000_000:
                stamp /= 1000
            if not math.isfinite(stamp):
                return None
            dt.datetime.fromtimestamp(stamp, dt.timezone.utc)
            return stamp
        if not isinstance(value, str):
            return None
        text = value.strip()
        if text.endswith(("Z", "z")):
            text = text[:-1] + "+00:00"
        parsed = dt.datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        stamp = parsed.timestamp()
        return stamp if math.isfinite(stamp) else None
    except (ValueError, OverflowError, OSError):
        return None


def flatten_text(value: Any) -> str:
    """Display a JSON value with its meaningful labels intact."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return "\n".join(f"{key}: {flatten_text(item)}" for key, item in value.items())
    if isinstance(value, list):
        return "\n".join(flatten_text(item) for item in value)
    return str(value)


def meaningful_keywords(text: Any) -> set[str]:
    return {
        word for word in re.findall(r"[a-z0-9]+", flatten_text(text).lower())
        if len(word) >= 2 and word not in _STOP_WORDS
    }


def _truncate(value: Any, length: int = 200) -> Any:
    if isinstance(value, str):
        return value[:length]
    if isinstance(value, list):
        return [_truncate(item, length) for item in value]
    if isinstance(value, dict):
        return {key: _truncate(item, length) for key, item in value.items()}
    return value


def inspect_data(
    data_dir: str | Path,
    field_map: dict[str, dict[str, str | None]] | None = None,
    limit: int | None = None,
    stream: TextIO | None = None,
) -> dict[str, Any]:
    """Print first-row keys and three safe samples for each known present source."""
    result: dict[str, Any] = {}
    if limit is not None and limit < 0:
        raise ValueError("limit must be nonnegative")
    for source in DEFAULT_FIELD_MAP:
        path = source_path(data_dir, source)
        if path is None:
            continue
        rows = _raw_rows(path, limit)
        try:
            samples = [row for _, row in islice(rows, 3)]
        finally:
            rows.close()
        keys = sorted({key for row in samples for key in row})
        result[path.name] = {"keys": keys, "samples": [_truncate(row) for row in samples]}
    if stream is not None:
        for filename, item in result.items():
            print(filename, file=stream)
            print("  keys: " + ", ".join(item["keys"]), file=stream)
            for index, row in enumerate(item["samples"], 1):
                print(f"  sample {index}: " + json.dumps(row, ensure_ascii=False), file=stream)
        if not result:
            print("No known JSONL sources found.", file=stream)
    return result


class TurnIndex:
    """Stream turns into SQLite; return a cursor-backed evidence iterator."""

    def __init__(
        self,
        data_dir: str | Path,
        field_map: dict[str, dict[str, str | None]] | None = None,
        work_dir: str | Path | None = None,
        limit: int | None = None,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.field_map = field_map or load_field_map()
        self.limit = limit
        directory = Path(work_dir) if work_dir is not None else self.data_dir
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix=".turn-index-", suffix=".sqlite", dir=directory) as handle:
            self.path = Path(handle.name)
        self.connection = sqlite3.connect(self.path)
        self.connection.execute("PRAGMA temp_store=FILE")
        self.connection.execute("PRAGMA cache_size=-4096")
        self.connection.executescript("""
            CREATE TABLE participants (
                agent TEXT PRIMARY KEY COLLATE NOCASE
            );
            CREATE TABLE sessions (
                session TEXT NOT NULL, agent TEXT NOT NULL, goal TEXT NOT NULL,
                PRIMARY KEY (session, agent)
            );
            CREATE TABLE session_keywords (
                session TEXT NOT NULL, agent TEXT NOT NULL, keyword TEXT NOT NULL,
                PRIMARY KEY (session, agent, keyword)
            );
            CREATE INDEX session_keywords_lookup ON session_keywords (agent, keyword, session);
            CREATE TABLE turns (
                sequence INTEGER PRIMARY KEY, agent TEXT NOT NULL,
                stamp REAL, session TEXT, payload TEXT NOT NULL
            );
            CREATE INDEX turns_agent_time ON turns (agent, stamp);
            CREATE INDEX turns_agent_session ON turns (agent, session, stamp);
        """)
        self.counts = {
            "sessions": 0, "turns": 0, "indexed_turns": 0,
            "unassigned_turns": 0, "untimed_turns": 0, "enriched_turns": 0,
        }
        self.diagnostics: list[str] = []
        self._built = False
        self._closed = False

    def _diagnose(self, message: str) -> None:
        if len(self.diagnostics) < 50:
            self.diagnostics.append(message)

    @staticmethod
    def _identifier(value: Any) -> str | None:
        if isinstance(value, (str, int)) and not isinstance(value, bool):
            text = str(value).strip()
            return text or None
        return None

    def build(self) -> "TurnIndex":
        if self._built:
            return self
        for row in iter_source(self.data_dir, "computer_use_sessions", self.field_map, self.limit):
            self.counts["sessions"] += 1
            session, agent = self._identifier(row["session"]), self._identifier(row["agent"])
            if session is None or agent is None:
                self._diagnose(row["row_id"] + ": session missing its id or agent")
                continue
            goal = flatten_text(row["text"])
            self.connection.execute(
                "INSERT OR IGNORE INTO sessions VALUES (?, ?, ?)", (session, agent, goal)
            )
            self.connection.executemany(
                "INSERT OR IGNORE INTO session_keywords VALUES (?, ?, ?)",
                ((session, agent, keyword) for keyword in meaningful_keywords(goal)),
            )
        self.connection.commit()
        for row in iter_source(self.data_dir, "computer_use_turns", self.field_map, self.limit):
            self.counts["turns"] += 1
            session = self._identifier(row["session"])
            agent = self._identifier(row["agent"])
            if agent is None and session is not None:
                owners = self.connection.execute(
                    "SELECT agent FROM sessions WHERE session=? LIMIT 2", (session,)
                ).fetchall()
                if len(owners) == 1:
                    agent = owners[0][0]
                    row["agent"] = agent
                    self.counts["enriched_turns"] += 1
            if agent is None:
                self.counts["unassigned_turns"] += 1
                self._diagnose(row["row_id"] + ": turn has no unambiguous agent")
                continue
            stamp = parse_timestamp(row["time"])
            if stamp is None:
                self.counts["untimed_turns"] += 1
                self._diagnose(row["row_id"] + ": missing or malformed turn timestamp")
            # Narration is neither evidence nor useful index content. Retain
            # only the permitted record fields, even when messages are huge.
            payload = {name: row[name] for name in (
                "agent", "time", "session", "action", "output", "source", "row_id"
            )}
            self.connection.execute(
                "INSERT INTO turns (agent, stamp, session, payload) VALUES (?, ?, ?, ?)",
                (agent, stamp, session, json.dumps(payload, ensure_ascii=False)),
            )
            self.counts["indexed_turns"] += 1
            if self.counts["indexed_turns"] % 1000 == 0:
                self.connection.commit()
        self.connection.commit()
        # Retain only distinct names, on disk, for detecting other-agent state
        # assertions. The turns agent index streams this grouping in order.
        self.connection.execute("INSERT OR IGNORE INTO participants SELECT agent FROM sessions")
        self.connection.execute("INSERT OR IGNORE INTO participants SELECT agent FROM turns GROUP BY agent")
        self.connection.commit()
        self._built = True
        return self

    def is_agent(self, name: str) -> bool:
        """Look up a participant name without holding a roster in memory."""
        return self.connection.execute(
            "SELECT 1 FROM participants WHERE agent=? LIMIT 1", (name,)
        ).fetchone() is not None

    def candidates(
        self,
        agent: Any,
        claim_time: Any,
        keywords: Any = (),
        window_hours: float = 24,
    ) -> Iterator[dict[str, Any]]:
        if not math.isfinite(window_hours) or window_hours < 0:
            raise ValueError("window_hours must be a finite nonnegative number")
        self.build()
        identity = self._identifier(agent)
        stamp = parse_timestamp(claim_time)
        if identity is None or stamp is None:
            return
        if isinstance(keywords, str):
            keyword_set = meaningful_keywords(keywords)
        else:
            keyword_set = meaningful_keywords(" ".join(str(keyword) for keyword in keywords))
        # Bound SQL placeholders even for unusually long claims. This limits only
        # additional session matching; all turns within the time window remain.
        keyword_list = sorted(keyword_set)[:100]
        window_start = stamp - window_hours * 3600
        parameters: list[Any] = [identity, stamp, window_start]
        session_clause = ""
        if keyword_list:
            placeholders = ",".join("?" for _ in keyword_list)
            session_clause = f""" OR EXISTS (
                SELECT 1 FROM session_keywords sk
                WHERE sk.agent=t.agent AND sk.session=t.session
                  AND sk.keyword IN ({placeholders})
            )"""
            parameters.extend(keyword_list)
        query = f"""
            SELECT t.payload, t.stamp, s.goal FROM turns t INDEXED BY turns_agent_time
            LEFT JOIN sessions s ON s.session=t.session AND s.agent=t.agent
            WHERE t.agent=? AND t.stamp < ?
              AND (t.stamp >= ? {session_clause})
            ORDER BY t.stamp, t.sequence
        """
        cursor = self.connection.execute(query, parameters)
        try:
            for payload, turn_stamp, session_goal in cursor:
                row = json.loads(payload)
                # Attach context only from this turn's own agent/session. These
                # derived fields never enter the persisted evidence payload.
                row["session_goal"] = session_goal or ""
                row["within_window"] = turn_stamp >= window_start
                yield row
        finally:
            cursor.close()

    def close(self) -> None:
        if self._closed:
            return
        try:
            self.connection.close()
        finally:
            self.path.unlink(missing_ok=True)
            self._closed = True

    def __enter__(self) -> "TurnIndex":
        try:
            return self.build()
        except BaseException:
            self.close()
            raise

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()
