"""SQLite session store for harness conversation resume.

tags: [harness, cli, session, sqlite, conversation]
routing_hints: [session, store, resume, chat, state.db]
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cli.auth.keyring_vault import _enforce_private_dir_permissions, _enforce_private_permissions

BUSY_MODES = ("interrupt", "queue", "steer")


def _utcnow_iso() -> str:
    # Include microseconds so same-second creates still order correctly.
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def default_state_db_path() -> Path:
    override = os.environ.get("HARNESS_STATE_DB")
    if override:
        return Path(override).expanduser().resolve()
    return Path.home() / ".harness" / "state.db"


class SessionStore:
    """Persist chat sessions and messages under ~/.harness/state.db (no API keys)."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else default_state_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        _enforce_private_dir_permissions(self.db_path.parent)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()
        _enforce_private_permissions(self.db_path)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> SessionStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT '',
                cwd TEXT NOT NULL DEFAULT '',
                provider TEXT NOT NULL DEFAULT '',
                model TEXT NOT NULL DEFAULT '',
                busy_mode TEXT NOT NULL DEFAULT 'interrupt',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                input_tokens INTEGER,
                output_tokens INTEGER,
                provider_data TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id, created_at);
            CREATE TABLE IF NOT EXISTS adapter_sessions (
                adapter TEXT NOT NULL,
                principal TEXT NOT NULL,
                route TEXT NOT NULL,
                external_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (adapter, principal, route, external_id),
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );
            """
        )
        # Keep databases created by slices 8-11 usable and make repeated startup safe.
        for table, column, declaration in (
            ("sessions", "busy_mode", "TEXT NOT NULL DEFAULT 'interrupt'"),
            ("messages", "input_tokens", "INTEGER"),
            ("messages", "output_tokens", "INTEGER"),
            ("messages", "provider_data", "TEXT"),
        ):
            existing = {
                row["name"]
                for row in self._conn.execute(f"PRAGMA table_info({table})").fetchall()
            }
            if column not in existing:
                self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")
        self._conn.commit()

    def get_adapter_session(
        self,
        adapter: str,
        principal: str,
        route: str,
        external_id: str,
    ) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            SELECT s.* FROM adapter_sessions AS a
            JOIN sessions AS s ON s.id = a.session_id
            WHERE a.adapter = ? AND a.principal = ? AND a.route = ? AND a.external_id = ?
            """,
            (adapter, principal, route, external_id),
        ).fetchone()
        return dict(row) if row is not None else None

    def bind_adapter_session(
        self,
        adapter: str,
        principal: str,
        route: str,
        external_id: str | None = None,
        *,
        title: str = "",
        cwd: str = "",
        provider: str = "",
        model: str = "",
        busy_mode: str = "interrupt",
        initial_messages: list[dict[str, Any]] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Resolve or create a stable external handle for a durable conversation."""
        if busy_mode not in BUSY_MODES:
            raise ValueError(f"busy mode must be one of: {', '.join(BUSY_MODES)}")
        handle = external_id or str(uuid.uuid4())
        if not handle or len(handle) > 256 or any(ord(char) < 32 or ord(char) == 127 for char in handle):
            raise ValueError("adapter session handle is invalid")
        existing = self.get_adapter_session(adapter, principal, route, handle)
        if existing is not None:
            return handle, existing

        now = _utcnow_iso()
        session_id = str(uuid.uuid4())
        try:
            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO sessions (id, title, cwd, provider, model, busy_mode, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (session_id, title or "", cwd or "", provider or "", model or "", busy_mode, now, now),
                )
                self._conn.execute(
                    """
                    INSERT INTO adapter_sessions
                        (adapter, principal, route, external_id, session_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (adapter, principal, route, handle, session_id, now, now),
                )
                for message in initial_messages or []:
                    provider_data = message.get("provider_data")
                    provider_data_json = (
                        json.dumps(provider_data, ensure_ascii=False, allow_nan=False)
                        if provider_data is not None
                        else None
                    )
                    self._conn.execute(
                        """
                        INSERT INTO messages
                            (id, session_id, role, content, input_tokens, output_tokens, provider_data, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(uuid.uuid4()),
                            session_id,
                            message["role"],
                            str(message.get("content", "")),
                            message.get("input_tokens"),
                            message.get("output_tokens"),
                            provider_data_json,
                            _utcnow_iso(),
                        ),
                    )
        except sqlite3.IntegrityError:
            # Another request may have claimed the same supplied handle first.
            existing = self.get_adapter_session(adapter, principal, route, handle)
            if existing is None:
                raise
            return handle, existing
        session = self.get_session(session_id)
        assert session is not None
        return handle, session

    def rebind_adapter_session(
        self,
        adapter: str,
        principal: str,
        route: str,
        external_id: str,
        session_id: str,
    ) -> bool:
        """Point an unchanged adapter handle at a compacted child session."""
        if self.get_session(session_id) is None:
            return False
        cur = self._conn.execute(
            """
            UPDATE adapter_sessions SET session_id = ?, updated_at = ?
            WHERE adapter = ? AND principal = ? AND route = ? AND external_id = ?
            """,
            (session_id, _utcnow_iso(), adapter, principal, route, external_id),
        )
        self._conn.commit()
        return cur.rowcount == 1

    def create_session(
        self,
        *,
        title: str = "",
        cwd: str = "",
        provider: str = "",
        model: str = "",
        busy_mode: str = "interrupt",
        session_id: str | None = None,
    ) -> dict[str, Any]:
        if busy_mode not in BUSY_MODES:
            raise ValueError(f"busy mode must be one of: {', '.join(BUSY_MODES)}")
        sid = session_id or str(uuid.uuid4())
        now = _utcnow_iso()
        self._conn.execute(
            """
            INSERT INTO sessions (id, title, cwd, provider, model, busy_mode, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (sid, title or "", cwd or "", provider or "", model or "", busy_mode, now, now),
        )
        self._conn.commit()
        row = self.get_session(sid)
        assert row is not None
        return row

    def create_session_with_messages(
        self,
        messages: list[dict[str, Any]],
        *,
        title: str = "",
        cwd: str = "",
        provider: str = "",
        model: str = "",
        busy_mode: str = "interrupt",
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a session and its initial history in one transaction."""
        if busy_mode not in BUSY_MODES:
            raise ValueError(f"busy mode must be one of: {', '.join(BUSY_MODES)}")
        sid = session_id or str(uuid.uuid4())
        now = _utcnow_iso()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO sessions (id, title, cwd, provider, model, busy_mode, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (sid, title or "", cwd or "", provider or "", model or "", busy_mode, now, now),
            )
            for message in messages:
                provider_data = message.get("provider_data")
                provider_data_json = (
                    json.dumps(provider_data, ensure_ascii=False, allow_nan=False)
                    if provider_data is not None
                    else None
                )
                self._conn.execute(
                    """
                    INSERT INTO messages
                        (id, session_id, role, content, input_tokens, output_tokens, provider_data, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        sid,
                        message["role"],
                        message["content"],
                        message.get("input_tokens"),
                        message.get("output_tokens"),
                        provider_data_json,
                        _utcnow_iso(),
                    ),
                )
        row = self.get_session(sid)
        assert row is not None
        return row

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        *,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        provider_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        mid = str(uuid.uuid4())
        now = _utcnow_iso()
        provider_data_json = (
            json.dumps(provider_data, ensure_ascii=False, allow_nan=False)
            if provider_data is not None
            else None
        )
        self._conn.execute(
            """
            INSERT INTO messages (id, session_id, role, content, input_tokens, output_tokens, provider_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (mid, session_id, role, content, input_tokens, output_tokens, provider_data_json, now),
        )
        self._conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (now, session_id),
        )
        self._conn.commit()
        return {
            "id": mid,
            "session_id": session_id,
            "role": role,
            "content": content,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "provider_data": provider_data,
            "created_at": now,
        }

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def append_messages(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Append a complete protocol batch atomically to preserve tool pairing."""
        if not messages:
            return []
        inserted: list[dict[str, Any]] = []
        with self._conn:
            for message in messages:
                message_id = str(uuid.uuid4())
                created_at = _utcnow_iso()
                provider_data = message.get("provider_data")
                provider_data_json = (
                    json.dumps(provider_data, ensure_ascii=False, allow_nan=False)
                    if provider_data is not None
                    else None
                )
                self._conn.execute(
                    """
                    INSERT INTO messages
                        (id, session_id, role, content, input_tokens, output_tokens, provider_data, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        message_id,
                        session_id,
                        message["role"],
                        message["content"],
                        message.get("input_tokens"),
                        message.get("output_tokens"),
                        provider_data_json,
                        created_at,
                    ),
                )
                inserted.append(
                    {
                        "id": message_id,
                        "session_id": session_id,
                        "role": message["role"],
                        "content": message["content"],
                        "input_tokens": message.get("input_tokens"),
                        "output_tokens": message.get("output_tokens"),
                        "provider_data": provider_data,
                        "created_at": created_at,
                    }
                )
            self._conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (_utcnow_iso(), session_id),
            )
        return inserted

    def list_messages(self, session_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM messages
            WHERE session_id = ?
            ORDER BY created_at ASC, rowid ASC
            """,
            (session_id,),
        ).fetchall()
        return [self._decode_message_row(r) for r in rows]

    @staticmethod
    def _decode_message_row(row: sqlite3.Row) -> dict[str, Any]:
        message = dict(row)
        raw_provider_data = message.get("provider_data")
        if isinstance(raw_provider_data, str):
            try:
                message["provider_data"] = json.loads(raw_provider_data)
            except json.JSONDecodeError:
                message["provider_data"] = None
        return message

    def list_sessions(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM sessions
            ORDER BY updated_at DESC, rowid DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def rename_session(self, session_id: str, title: str) -> dict[str, Any] | None:
        now = _utcnow_iso()
        cur = self._conn.execute(
            "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
            (title, now, session_id),
        )
        self._conn.commit()
        if cur.rowcount == 0:
            return None
        return self.get_session(session_id)

    def touch_session(
        self,
        session_id: str,
        *,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        now = _utcnow_iso()
        session = self.get_session(session_id)
        if session is None:
            return
        prov = provider if provider is not None else session["provider"]
        mod = model if model is not None else session["model"]
        self._conn.execute(
            "UPDATE sessions SET updated_at = ?, provider = ?, model = ? WHERE id = ?",
            (now, prov, mod, session_id),
        )
        self._conn.commit()

    def set_busy_mode(self, session_id: str, mode: str) -> dict[str, Any] | None:
        if mode not in BUSY_MODES:
            raise ValueError(f"busy mode must be one of: {', '.join(BUSY_MODES)}")
        now = _utcnow_iso()
        cur = self._conn.execute(
            "UPDATE sessions SET busy_mode = ?, updated_at = ? WHERE id = ?",
            (mode, now, session_id),
        )
        self._conn.commit()
        if cur.rowcount == 0:
            return None
        return self.get_session(session_id)

    def latest_session(self) -> dict[str, Any] | None:
        rows = self.list_sessions(limit=1)
        return rows[0] if rows else None

    def search_messages(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        pattern = f"%{query}%"
        rows = self._conn.execute(
            """
            SELECT m.*, s.title AS session_title
            FROM messages m
            JOIN sessions s ON s.id = m.session_id
            WHERE m.content LIKE ?
            ORDER BY m.created_at DESC
            LIMIT ?
            """,
            (pattern, limit),
        ).fetchall()
        return [self._decode_message_row(r) for r in rows]
