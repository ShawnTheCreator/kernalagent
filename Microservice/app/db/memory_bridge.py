"""Memory Bridge.

Single import surface for episodic memory.
- Prefer local SQLite for persistence
- Optionally uses Firebase implementation when explicitly enabled via env var

The rest of the codebase imports from here to avoid coupling.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from .local_episodic_memory import TimelineEvent, get_local_episodic_memory

logger = logging.getLogger(__name__)


def _try_import_firebase_repo():
    if os.getenv("FIREBASE_EPISODIC_MEMORY", "false").lower() != "true":
        return None
    try:
        from . import episodic_memory_repo

        return episodic_memory_repo
    except Exception as exc:
        logger.warning(f"[MemoryBridge] Firebase episodic repo unavailable: {exc}")
        return None


async def log_event(user_id: str, event_type: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    local = get_local_episodic_memory()
    event_id = await local.log_event(user_id=user_id, event_type=event_type, content=content, metadata=metadata)

    fb = _try_import_firebase_repo()
    if fb is not None:
        try:
            await fb.log_event(user_id=user_id, event_type=event_type, content=content, metadata=metadata)
        except Exception as exc:
            logger.warning(f"[MemoryBridge] Firebase log_event failed: {exc}")

    return event_id


async def get_timeline(user_id: str, limit: int = 50, before_timestamp: Optional[str] = None) -> List[Dict[str, Any]]:
    local = get_local_episodic_memory()
    return await local.get_timeline(user_id=user_id, limit=limit, before_timestamp=before_timestamp)


async def search_memories(
    user_id: str,
    query: str,
    event_types: Optional[List[str]] = None,
    limit: int = 20,
    before_timestamp: Optional[str] = None,
) -> List[Dict[str, Any]]:
    local = get_local_episodic_memory()
    return await local.search_memories(
        user_id=user_id,
        query=query,
        event_types=event_types,
        limit=limit,
        before_timestamp=before_timestamp,
    )


async def clear_timeline(user_id: str) -> bool:
    ok = False
    local = get_local_episodic_memory()
    ok = bool(await local.clear_timeline(user_id=user_id)) or ok

    fb = _try_import_firebase_repo()
    if fb is not None:
        try:
            ok = bool(await fb.clear_timeline(user_id=user_id)) or ok
        except Exception as exc:
            logger.warning(f"[MemoryBridge] Firebase clear_timeline failed: {exc}")
    return ok


async def rebuild_memory_embeddings(user_id: str, limit: int = 500, force: bool = False) -> Dict[str, Any]:
    """If Firebase episodic repo exists, delegate. Otherwise no-op."""
    fb = _try_import_firebase_repo()
    if fb is None:
        return {"updated": 0, "skipped": 0, "errors": 0, "note": "local_memory_noop"}

    return await fb.rebuild_memory_embeddings(user_id=user_id, limit=limit, force=force)


async def get_memory_summary(
    user_id: str,
    limit: int = 50,
    include_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """If Firebase episodic repo exists, delegate. Otherwise compute a basic local summary."""
    fb = _try_import_firebase_repo()
    if fb is not None:
        try:
            return await fb.get_memory_summary(user_id=user_id, limit=limit, include_types=include_types)
        except Exception as exc:
            logger.warning(f"[MemoryBridge] Firebase get_memory_summary failed, using local: {exc}")

    local = get_local_episodic_memory()
    events = await local.get_timeline(user_id=user_id, limit=limit)
    if include_types:
        events = [e for e in events if e.get("type") in include_types]

    counts: Dict[str, int] = {}
    for e in events:
        t = e.get("type") or "unknown"
        counts[t] = counts.get(t, 0) + 1

    return {
        "user_id": user_id,
        "limit": limit,
        "counts": counts,
        "recent": events[: min(10, len(events))],
    }


def get_memory_stats() -> Dict[str, Any]:
    return get_local_episodic_memory().get_stats()


__all__ = [
    "TimelineEvent",
    "log_event",
    "get_timeline",
    "search_memories",
    "clear_timeline",
    "rebuild_memory_embeddings",
    "get_memory_summary",
    "get_memory_stats",
]
