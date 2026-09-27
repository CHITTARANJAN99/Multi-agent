from typing import Dict, Tuple, Any, List

class SessionStateManager:
    """
    In-memory state manager to persist active TaskManager states, recent contexts,
    and credentials when agent workflows are suspended waiting for Human-in-the-Loop confirmations.
    """
    def __init__(self):
        # Maps session_id -> (task_manager, context_text, short_term_history_log)
        self.active_sessions: Dict[str, Tuple[Any, str, List[Dict[str, str]]]] = {}

    def save_session(self, session_id: str, task_manager: Any, context_text: str, history: List[Dict[str, str]]) -> None:
        self.active_sessions[session_id] = (task_manager, context_text, history)

    def load_session(self, session_id: str) -> Tuple[Any, str, List[Dict[str, str]]]:
        return self.active_sessions.get(session_id, (None, "", []))

    def clear_session(self, session_id: str) -> None:
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]

session_state_manager = SessionStateManager()
