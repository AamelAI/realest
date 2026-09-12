"""THE session store. Single source of truth.

Voice writes it through webhook handlers; the page reads it by polling.
Nothing else talks to anything.

Read .claude/skills/session-state/ before changing anything here.
Do not change the shape after 12:30 - both other lanes import it.
"""
from __future__ import annotations

import asyncio
import time

from schemas import SessionState

_sessions: dict[str, SessionState] = {}
_lock = asyncio.Lock()


def get(session_id: str) -> SessionState | None:
    return _sessions.get(session_id)


async def mutate(session_id: str, fn) -> SessionState:
    """Funnel EVERY write through here.

    Three calls land concurrently; two coroutines writing `listings` at the
    same time is a real bug in this project, not a theoretical one.

    TODO(hackathon): create-if-missing, apply fn, bump updated_at, return state.
    """
    raise NotImplementedError
