"""Local Episodic Memory - SQLite-based conversation/task timeline.

Local replacement backend for episodic memory events:
- chat_user, chat_agent
- action_tool
- memory_thought
- system_alert

Persists to SQLite under Microservice/data/episodic_memory.db by default.
"""

import json
import logging
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

logger = logging.getLogger(__name__)

EventType = Literal["chat_user", "chat_agent", "action_tool", "memory_thought", "system_alert"]


class TimelineEvent:
    def __init__(
        self,
        event_type: EventType,
        content: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.event_id = event_id or str(uuid.uuid4())
        self.event_type = event_type
        self.content = content
        self.user_id = user_id
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.embedding = embedding or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.event_id,
            "type": self.event_type,
            "content": self.content,
            "metadata": self.metadata,
            "embedding": self.embedding,
            "timestamp": self.timestamp.isoformat(),
            "created_at": self.timestamp,  # kept for compatibility
        }


class LocalEpisodicMemory:
    def __init__(self, db_path: str = "data/episodic_memory.db"):
        # Resolve relative paths from Microservice/ working directory.
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS timeline_events (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    metadata TEXT,
                    embedding TEXT,
                    timestamp TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_timeline_user_id ON timeline_events(user_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_timeline_created_at ON timeline_events(created_at)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_timeline_type ON timeline_events(type)")
            conn.commit()

    async def log_event(
        self,
        user_id: str,
        event_type: EventType,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ) -> str:
        try:
            event = TimelineEvent(
                event_type=event_type,
                content=content,
                user_id=user_id,
                metadata=metadata,
                embedding=embedding,
            )

            with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cur = conn.cursor()
                    cur.execute(
                        """
                        INSERT INTO timeline_events
                        (id, type, content, user_id, metadata, embedding, timestamp, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            event.event_id,
                            event.event_type,
                            event.content,
                            event.user_id,
                            json.dumps(event.metadata) if event.metadata else None,
                            json.dumps(event.embedding) if event.embedding else None,
                            event.timestamp.isoformat(),
                            event.timestamp.isoformat(),
                        ),
                    )
                    conn.commit()

            return event.event_id
        except Exception as exc:
            logger.error(f"[LocalEpisodicMemory] log_event failed: {exc}")
            return ""

    async def get_timeline(
        self, user_id: str, limit: int = 50, before_timestamp: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()

                q = (
                    "SELECT id, type, content, user_id, metadata, embedding, timestamp, created_at "
                    "FROM timeline_events WHERE user_id = ?"
                )
                params: List[Any] = [user_id]

                if before_timestamp:
                    q += " AND created_at < ?"
                    params.append(before_timestamp)

                q += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)

                cur.execute(q, params)
                rows = cur.fetchall()

            events: List[Dict[str, Any]] = []
            for r in rows:
                events.append(
                    {
                        "id": r[0],
                        "type": r[1],
                        "content": r[2],
                        "user_id": r[3],
                        "metadata": json.loads(r[4]) if r[4] else {},
                        "embedding": json.loads(r[5]) if r[5] else [],
                        "timestamp": r[6],
                        "created_at": r[7],
                    }
                )
            return events
        except Exception as exc:
            logger.error(f"[LocalEpisodicMemory] get_timeline failed: {exc}")
            return []

    async def clear_timeline(self, user_id: str) -> bool:
        try:
            with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cur = conn.cursor()
                    cur.execute("DELETE FROM timeline_events WHERE user_id = ?", (user_id,))
                    conn.commit()
            return True
        except Exception as exc:
            logger.error(f"[LocalEpisodicMemory] clear_timeline failed: {exc}")
            return False

    async def search_memories(
        self,
        user_id: str,
        query: str,
        event_types: Optional[List[str]] = None,
        limit: int = 20,
        before_timestamp: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        try:
            # Simple text search over recent events.
            events = await self.get_timeline(user_id=user_id, limit=200, before_timestamp=before_timestamp)
            if event_types:
                events = [e for e in events if e.get("type") in event_types]

            ql = query.lower().strip()
            if not ql:
                return events[:limit]

            matches: List[Dict[str, Any]] = []
            for e in events:
                c = (e.get("content") or "").lower()
                m = json.dumps(e.get("metadata") or {}).lower()
                score = 0
                if ql in c:
                    score += 10
                if ql in m:
                    score += 5
                if score:
                    ec = dict(e)
                    ec["relevance_score"] = score
                    matches.append(ec)

            matches.sort(key=lambda x: (x.get("relevance_score", 0), x.get("timestamp", "")), reverse=True)
            return matches[:limit]
        except Exception as exc:
            logger.error(f"[LocalEpisodicMemory] search_memories failed: {exc}")
            return []

    def get_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                stats: Dict[str, Any] = {}
                if user_id:
                    cur.execute("SELECT COUNT(*) FROM timeline_events WHERE user_id = ?", (user_id,))
                    stats["total_events"] = cur.fetchone()[0]
                else:
                    cur.execute("SELECT COUNT(*) FROM timeline_events")
                    stats["total_events"] = cur.fetchone()[0]
                stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)
                return stats
        except Exception as exc:
            logger.error(f"[LocalEpisodicMemory] get_stats failed: {exc}")
            return {}


_LOCAL: Optional[LocalEpisodicMemory] = None


def get_local_episodic_memory() -> LocalEpisodicMemory:
    global _LOCAL
    if _LOCAL is None:
        _LOCAL = LocalEpisodicMemory()
    return _LOCAL
