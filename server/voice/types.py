"""Shared types for voice providers.

calls.place_call() will later call VoiceProvider.place_outbound() and get a
CallHandle back. Nothing in this package imports listings or SessionState.
"""
from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel

Role = Literal["renter", "listing"]


class CallHandle(BaseModel):
    """What place_outbound returns. Enough to poll or match a post-call webhook."""

    conversation_id: str | None = None
    call_sid: str | None = None
    provider: str


class VoiceProvider(Protocol):
    def configured(self) -> bool:
        """True when every env var this provider needs is set."""
        ...

    async def health(self) -> dict:
        """Reach the vendor and report what the key unlocks."""
        ...

    async def place_outbound(
        self,
        to_number: str,
        role: Role,
        dynamic_variables: dict[str, str] | None = None,
    ) -> CallHandle:
        """Place one outbound call. dynamic_variables stay a plain string dict."""
        ...

    async def get_conversation(self, conversation_id: str) -> dict:
        """Fetch a conversation (transcript / status). Used after Phase 0."""
        ...
