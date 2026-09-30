"""
SQLite + FTS5 Full-Text Search Store for Merlin Agent Sessions.
Configured with Write-Ahead Logging (WAL) for Tier-3 non-blocking concurrency.
Provides cross-session semantic and lexical recall matching Hermes Agent.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from merlin_constants import get_state_db_path


class SessionStore:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or get_state_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    from contextlib import contextmanager

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        # Hardware & OS optimized SQLite PRAGMAs (Tier 3)
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA temp_store = MEMORY;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Create schema with FTS5 search index."""
        with self._connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    metadata TEXT
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    tool_calls TEXT,
                    author TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                );

                CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
                CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at DESC);

                -- FTS5 Full-Text Search Virtual Table
                CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                    content,
                    role UNINDEXED,
                    session_id UNINDEXED,
                    content='messages',
                    content_rowid='id'
                );

                -- Triggers to synchronize FTS5 index automatically
                CREATE TRIGGER IF NOT EXISTS trg_messages_ai AFTER INSERT ON messages BEGIN
                    INSERT INTO messages_fts(rowid, content, role, session_id)
                    VALUES (new.id, new.content, new.role, new.session_id);
                END;

                CREATE TRIGGER IF NOT EXISTS trg_messages_ad AFTER DELETE ON messages BEGIN
                    INSERT INTO messages_fts(messages_fts, rowid, content, role, session_id)
                    VALUES('delete', old.id, old.content, old.role, old.session_id);
                END;

                CREATE TABLE IF NOT EXISTS trajectories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                """
            )

    def create_or_update_session(self, session_id: str, title: str = "New Session", metadata: Optional[Dict[str, Any]] = None) -> None:
        now = time.time()
        meta_str = json.dumps(metadata or {})
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions (session_id, title, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    updated_at = excluded.updated_at,
                    title = CASE WHEN excluded.title != 'New Session' THEN excluded.title ELSE sessions.title END,
                    metadata = excluded.metadata
                """,
                (session_id, title, now, now, meta_str),
            )

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        author: Optional[str] = None,
    ) -> int:
        now = time.time()
        tc_str = json.dumps(tool_calls) if tool_calls else None
        with self._connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO messages (session_id, role, content, timestamp, tool_calls, author)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, role, content, now, tc_str, author),
            )
            msg_id = cur.lastrowid
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                (now, session_id),
            )
            return msg_id

    def get_messages(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        with self._connection() as conn:
            cur = conn.execute(
                """
                SELECT id, role, content, timestamp, tool_calls, author
                FROM messages
                WHERE session_id = ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (session_id, limit),
            )
            rows = cur.fetchall()
            result = []
            for r in rows:
                item = dict(r)
                if item.get("tool_calls"):
                    try:
                        item["tool_calls"] = json.loads(item["tool_calls"])
                    except Exception:
                        pass
                result.append(item)
            return result

    def search_sessions(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        FTS5 BM25 ranked search across message history.
        Returns matching turn content and session metadata.
        """
        sanitized_query = "".join(c for c in query if c.isalnum() or c.isspace()).strip()
        if not sanitized_query:
            return []

        fts_query = " OR ".join(sanitized_query.split())
        with self._connection() as conn:
            cur = conn.execute(
                """
                SELECT m.id, m.session_id, m.role, m.content, m.timestamp, s.title, bm25(messages_fts) as rank
                FROM messages_fts
                JOIN messages m ON m.id = messages_fts.rowid
                JOIN sessions s ON s.session_id = m.session_id
                WHERE messages_fts MATCH ?
                ORDER BY rank ASC
                LIMIT ?
                """,
                (fts_query, limit),
            )
            return [dict(r) for r in cur.fetchall()]

    def list_sessions(self, limit: int = 30) -> List[Dict[str, Any]]:
        with self._connection() as conn:
            cur = conn.execute(
                """
                SELECT s.session_id, s.title, s.created_at, s.updated_at,
                       COUNT(m.id) as message_count
                FROM sessions s
                LEFT JOIN messages m ON s.session_id = m.session_id
                GROUP BY s.session_id
                ORDER BY s.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(r) for r in cur.fetchall()]

    def save_trajectory(self, session_id: str, trajectory_data: Dict[str, Any]) -> None:
        now = time.time()
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO trajectories (session_id, data, created_at) VALUES (?, ?, ?)",
                (session_id, json.dumps(trajectory_data), now),
            )
