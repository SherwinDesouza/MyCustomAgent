# session_context.py
from contextvars import ContextVar

# Context variable to store the current session ID
session_id_var: ContextVar[str] = ContextVar('session_id', default='default')

def get_session_id() -> str:
    """Get the current session ID from context."""
    return session_id_var.get()

def set_session_id(session_id: str) -> None:
    """Set the session ID in context."""
    session_id_var.set(session_id)
