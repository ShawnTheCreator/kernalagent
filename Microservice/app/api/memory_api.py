from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
import json
import os
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/memory", tags=["memory"])


def _ensure_logs_dir() -> None:
    try:
        os.makedirs("logs", exist_ok=True)
    except Exception:
        pass


def _gemma_examples_file() -> str:
    return "logs/gemma_examples.jsonl"


def _safe_load_json_line(line: str) -> Optional[Dict[str, Any]]:
    try:
        obj = json.loads(line)
        if isinstance(obj, dict):
            return obj
        return None
    except Exception:
        return None


def _normalize_example(obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    command = obj.get("command")
    output = obj.get("output")
    if not isinstance(command, str) or not command.strip():
        return None
    if not isinstance(output, dict):
        return None

    intent = output.get("intent")
    entities = output.get("entities")
    caps = output.get("capabilities_needed")
    confidence = output.get("confidence")
    risk = output.get("risk")

    if not isinstance(intent, str) or not intent.strip():
        return None
    if not isinstance(entities, dict):
        entities = {}
    if not isinstance(caps, list):
        caps = []
    if not isinstance(confidence, (int, float)):
        confidence = 0.0
    try:
        confidence = float(confidence)
    except Exception:
        confidence = 0.0

    if not isinstance(risk, str):
        risk = "low"
    risk = (risk or "low").strip().lower()
    if risk not in ["low", "medium", "high"]:
        risk = "low"

    example = {
        "command": command.strip(),
        "output": {
            "intent": intent.strip(),
            "entities": entities,
            "capabilities_needed": caps,
            "confidence": confidence,
            "risk": risk,
        },
    }

    if isinstance(obj.get("tags"), list):
        example["tags"] = obj.get("tags")
    if isinstance(obj.get("source"), str):
        example["source"] = obj.get("source")
    if isinstance(obj.get("score"), (int, float)):
        example["score"] = float(obj.get("score"))
    if isinstance(obj.get("created_at"), str):
        example["created_at"] = obj.get("created_at")
    else:
        example["created_at"] = datetime.utcnow().isoformat()

    return example


def _append_gemma_example(example: Dict[str, Any]) -> None:
    _ensure_logs_dir()
    path = _gemma_examples_file()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(example, ensure_ascii=False) + "\n")


def _read_gemma_examples(limit: int = 20) -> List[Dict[str, Any]]:
    path = _gemma_examples_file()
    if not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = [ln for ln in f.readlines() if ln.strip()]
        items = []
        for ln in reversed(lines):
            obj = _safe_load_json_line(ln)
            if not obj:
                continue
            norm = _normalize_example(obj)
            if norm:
                items.append(norm)
            if len(items) >= max(1, limit):
                break
        items.reverse()
        return items
    except Exception:
        return []


def _discover_trace_files(repo_root: str) -> List[str]:
    results: List[str] = []
    try:
        desktop_root = os.path.join(repo_root, "Desktop-App")
        if not os.path.exists(desktop_root):
            return results

        for root, dirs, files in os.walk(desktop_root):
            try:
                if "execution_traces.jsonl" in files and os.path.basename(root).lower() == "logs":
                    results.append(os.path.join(root, "execution_traces.jsonl"))
            except Exception:
                continue
    except Exception:
        return results

    results.sort(key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0, reverse=True)
    return results


@router.get("/gemma-examples")
async def list_gemma_examples(limit: int = 20) -> Dict[str, Any]:
    try:
        examples = _read_gemma_examples(limit=limit)
        return {"examples": examples, "total": len(examples)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list gemma examples: {str(e)}")


@router.post("/gemma-examples")
async def add_gemma_example(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        norm = _normalize_example(payload)
        if not norm:
            raise HTTPException(status_code=400, detail="Invalid example payload")
        _append_gemma_example(norm)
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add gemma example: {str(e)}")


@router.post("/gemma-examples/import-traces")
async def import_gemma_examples_from_traces(limit: int = 200, min_confidence: float = 0.6, only_success: bool = True) -> Dict[str, Any]:
    try:
        traces_file_candidates: List[str] = []

        traces_file_candidates.append("logs/execution_traces.jsonl")

        try:
            microservice_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            repo_root = os.path.abspath(os.path.join(microservice_root, ".."))
            traces_file_candidates.append(os.path.join(microservice_root, "logs", "execution_traces.jsonl"))
            traces_file_candidates.append(
                os.path.join(repo_root, "Desktop-App", "Kernel Agent", "logs", "execution_traces.jsonl")
            )

            for p in _discover_trace_files(repo_root):
                traces_file_candidates.append(p)
        except Exception:
            pass

        traces_file = None
        for candidate in traces_file_candidates:
            try:
                if candidate and os.path.exists(candidate):
                    traces_file = candidate
                    break
            except Exception:
                continue

        if not traces_file:
            return {"imported": 0, "skipped": 0, "source": None}

        with open(traces_file, "r", encoding="utf-8") as f:
            lines = [ln for ln in f.readlines() if ln.strip()]

        imported = 0
        skipped = 0

        for ln in reversed(lines):
            if imported >= max(1, limit):
                break

            trace = _safe_load_json_line(ln)
            if not trace:
                skipped += 1
                continue

            if only_success and not bool(trace.get("success", False)):
                skipped += 1
                continue

            cmd = trace.get("command")
            interp_raw = trace.get("interpretation")
            if not isinstance(cmd, str) or not cmd.strip():
                skipped += 1
                continue
            if not isinstance(interp_raw, str) or not interp_raw.strip():
                skipped += 1
                continue

            try:
                interp_obj = json.loads(interp_raw)
            except Exception:
                skipped += 1
                continue

            if not isinstance(interp_obj, dict):
                skipped += 1
                continue

            conf = interp_obj.get("confidence")
            try:
                conf_f = float(conf) if conf is not None else 0.0
            except Exception:
                conf_f = 0.0

            if conf_f < float(min_confidence):
                skipped += 1
                continue

            candidate = {
                "command": cmd,
                "output": interp_obj,
                "source": "execution_traces",
                "score": conf_f,
            }
            norm = _normalize_example(candidate)
            if not norm:
                skipped += 1
                continue

            _append_gemma_example(norm)
            imported += 1

        return {"imported": imported, "skipped": skipped, "source": traces_file}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import gemma examples: {str(e)}")

@router.get("/patterns")
async def get_capability_patterns(
    intent: Optional[str] = None,
    min_success_rate: float = 0.7,
    min_usage_count: int = 2,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Get capability patterns from memory for intelligent routing.
    Returns patterns that match the intent and meet success criteria.
    """
    try:
        patterns_file = "logs/capability_patterns.json"
        
        if not os.path.exists(patterns_file):
            return {"patterns": [], "total": 0}
        
        with open(patterns_file, 'r') as f:
            patterns = json.load(f)
        
        # Filter patterns based on criteria
        filtered_patterns = []
        for pattern in patterns:
            # Success rate filter
            if pattern.get("successRate", 0) < min_success_rate:
                continue
                
            # Usage count filter
            if pattern.get("usageCount", 0) < min_usage_count:
                continue
                
            # Intent filter (if specified)
            if intent and not pattern.get("intent", "").lower() == intent.lower():
                continue
                
            # Recency filter (only patterns used in last 30 days)
            last_used = datetime.fromisoformat(pattern.get("lastUsed", "1970-01-01"))
            if datetime.now() - last_used > timedelta(days=30):
                continue
            
            filtered_patterns.append(pattern)
        
        # Sort by success rate and recency
        filtered_patterns.sort(key=lambda p: (
            p.get("successRate", 0),
            datetime.fromisoformat(p.get("lastUsed", "1970-01-01"))
        ), reverse=True)
        
        return {
            "patterns": filtered_patterns[:limit],
            "total": len(filtered_patterns)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get patterns: {str(e)}")

@router.get("/stats")
async def get_memory_stats() -> Dict[str, Any]:
    """
    Get memory statistics including success rates and pattern usage.
    """
    try:
        traces_file = "logs/execution_traces.jsonl"
        patterns_file = "logs/capability_patterns.json"
        
        stats = {
            "total_traces": 0,
            "recent_traces_7days": 0,
            "success_rate_7days": 0.0,
            "unique_patterns": 0,
            "high_confidence_patterns": 0,
            "top_intents": [],
            "top_capabilities": []
        }
        
        # Analyze traces
        if os.path.exists(traces_file):
            with open(traces_file, 'r') as f:
                lines = f.readlines()
                
            stats["total_traces"] = len(lines)
            
            # Count recent traces and success rate
            cutoff_date = datetime.now() - timedelta(days=7)
            recent_traces = []
            intent_counts = {}
            capability_counts = {}
            
            for line in lines:
                if not line.strip():
                    continue
                    
                try:
                    trace = json.loads(line)
                    trace_date = datetime.fromisoformat(trace.get("timestamp", "1970-01-01"))
                    
                    if trace_date > cutoff_date:
                        recent_traces.append(trace)
                        
                        # Count intents
                        intent = trace.get("intent", "unknown")
                        intent_counts[intent] = intent_counts.get(intent, 0) + 1
                        
                        # Count capabilities
                        for cap in trace.get("capabilities", []):
                            capability_counts[cap] = capability_counts.get(cap, 0) + 1
                            
                except json.JSONDecodeError:
                    continue
            
            stats["recent_traces_7days"] = len(recent_traces)
            
            if recent_traces:
                successful = sum(1 for t in recent_traces if t.get("success", False))
                stats["success_rate_7days"] = successful / len(recent_traces)
            
            # Get top intents and capabilities
            stats["top_intents"] = sorted(
                intent_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]
            
            stats["top_capabilities"] = sorted(
                capability_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]
        
        # Analyze patterns
        if os.path.exists(patterns_file):
            with open(patterns_file, 'r') as f:
                patterns = json.load(f)
                
            stats["unique_patterns"] = len(patterns)
            stats["high_confidence_patterns"] = sum(
                1 for p in patterns 
                if p.get("successRate", 0) >= 0.8
            )
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@router.delete("/cleanup")
async def cleanup_old_memory(days_to_keep: int = 30) -> Dict[str, Any]:
    """
    Clean up old memory data beyond specified days.
    """
    try:
        # This would trigger cleanup in the C# SafeMemoryLogger
        # For now, just return success
        return {
            "message": f"Cleanup scheduled for data older than {days_to_keep} days",
            "days_to_keep": days_to_keep
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup: {str(e)}")


# ==================== TIMELINE / EPISODIC MEMORY ENDPOINTS ====================

@router.get("/timeline/{session_id}")
async def get_timeline(
    session_id: str,
    limit: int = 50,
    before_timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get timeline events for a session.
    
    Args:
        session_id: Session/user identifier
        limit: Maximum number of events to return
        before_timestamp: Get events before this timestamp (ISO format)
    """
    try:
        from app.db.episodic_memory_repo import get_timeline as repo_get_timeline
        events = await repo_get_timeline(session_id, limit=limit, before_timestamp=before_timestamp)
        return {
            "session_id": session_id,
            "events": events,
            "count": len(events)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get timeline: {str(e)}")


@router.post("/timeline/{session_id}")
async def log_timeline_event(
    session_id: str,
    event_type: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Log a new event to the timeline.
    
    Args:
        session_id: Session/user identifier
        event_type: Type of event (chat_user, chat_agent, action_tool, memory_thought, system_alert)
        content: Event content/description
        metadata: Additional metadata for the event
    """
    try:
        from app.db.episodic_memory_repo import log_event
        event_id = await log_event(session_id, event_type, content, metadata)
        return {
            "success": True,
            "event_id": event_id,
            "session_id": session_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log event: {str(e)}")


@router.get("/search/{session_id}")
async def search_memories(
    session_id: str,
    query: str,
    event_types: Optional[str] = None,
    limit: int = 20,
    before_timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search through memories using semantic similarity.
    
    Args:
        session_id: Session/user identifier
        query: Search query string
        event_types: Comma-separated list of event types to filter by
        limit: Maximum results to return
        before_timestamp: Search only before this timestamp
    """
    try:
        from app.db.episodic_memory_repo import search_memories as repo_search
        
        # Parse event types if provided
        types_list = None
        if event_types:
            types_list = [t.strip() for t in event_types.split(",") if t.strip()]
        
        results = await repo_search(
            session_id, 
            query, 
            event_types=types_list, 
            limit=limit,
            before_timestamp=before_timestamp
        )
        return {
            "session_id": session_id,
            "query": query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search memories: {str(e)}")


@router.delete("/timeline/{session_id}")
async def clear_timeline(session_id: str) -> Dict[str, Any]:
    """
    Clear all timeline events for a session.
    """
    try:
        from app.db.episodic_memory_repo import clear_timeline as repo_clear
        success = await repo_clear(session_id)
        return {
            "success": success,
            "session_id": session_id,
            "message": "Timeline cleared" if success else "Failed to clear timeline"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear timeline: {str(e)}")


@router.get("/sessions")
async def list_sessions() -> Dict[str, Any]:
    """
    List all available session IDs from local storage.
    """
    try:
        from app.db.episodic_memory_repo import list_local_session_ids
        sessions = list_local_session_ids()
        return {
            "sessions": sessions,
            "count": len(sessions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


@router.post("/embeddings/rebuild/{session_id}")
async def rebuild_embeddings(
    session_id: str,
    limit: int = 500,
    force: bool = False
) -> Dict[str, Any]:
    """
    Rebuild embeddings for existing memories to enable semantic search.
    
    Args:
        session_id: Session/user identifier
        limit: Maximum number of events to process
        force: If True, recompute embeddings even if they exist
    """
    try:
        from app.db.episodic_memory_repo import rebuild_memory_embeddings
        result = await rebuild_memory_embeddings(session_id, limit=limit, force=force)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rebuild embeddings: {str(e)}")
