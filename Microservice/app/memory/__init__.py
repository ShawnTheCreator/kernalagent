# Memory module
from .context import (
    get_session,
    update_session,
    get_context_for_llm,
    is_contextual_command,
    resolve_contextual_command,
)

# Episodic memory (timeline) functions
try:
    from app.db.episodic_memory_repo import (
        log_event,
        get_timeline,
        search_memories,
        clear_timeline,
        list_local_session_ids,
        rebuild_memory_embeddings,
    )
except ImportError:
    # Episodic memory not available (missing dependencies)
    log_event = None
    get_timeline = None
    search_memories = None
    clear_timeline = None
    list_local_session_ids = None
    rebuild_memory_embeddings = None
