"""Voice providers. Phase 0 only constructs ElevenLabs.

The OpenAI Realtime path still lives in calls.place_call / bridge.py.
Flip VOICE_PROVIDER=elevenlabs when you are ready to plumb this in.
"""
from __future__ import annotations

import os

from voice.elevenlabs import ElevenLabsError, ElevenLabsProvider
from voice.types import CallHandle, Role, VoiceProvider

__all__ = [
    "CallHandle",
    "ElevenLabsError",
    "ElevenLabsProvider",
    "Role",
    "VoiceProvider",
    "get_provider",
]


def get_provider() -> VoiceProvider:
    name = (os.getenv("VOICE_PROVIDER") or "openai_realtime").strip()
    if name == "elevenlabs":
        return ElevenLabsProvider()
    raise NotImplementedError(
        f"VOICE_PROVIDER={name!r} is not wired through voice.get_provider() yet. "
        "The OpenAI Realtime path still lives in calls.place_call / bridge.py. "
        "Set VOICE_PROVIDER=elevenlabs to use ElevenLabsProvider."
    )
