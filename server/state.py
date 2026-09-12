"""THE session store. Single source of truth.

Voice writes it through webhook handlers; the page reads it by polling.
Nothing else talks to anything.

Read .claude/skills/session-state/ before changing anything here.
Do not change the shape after 12:30 - both other lanes import it.
"""
from __future__ import annotations

import asyncio
import time
from typing import Callable

from schemas import SessionState

_sessions: dict[str, SessionState] = {}
_lock = asyncio.Lock()


def get(session_id: str) -> SessionState | None:
    return _sessions.get(session_id)


def all_ids() -> list[str]:
    return list(_sessions)


async def mutate(session_id: str, fn: Callable[[SessionState], None]) -> SessionState:
    """Funnel EVERY write through here.

    Three calls land concurrently; two coroutines writing `listings` at the
    same time is a real bug in this project, not a theoretical one.
    """
    async with _lock:
        state = _sessions.get(session_id)
        if state is None:
            state = SessionState(session_id=session_id)
            _sessions[session_id] = state
        fn(state)
        state.updated_at = time.time()
        return state
