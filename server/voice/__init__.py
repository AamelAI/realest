"""Voice providers.

TRANSPORT=stub|voice decides whether we dial at all.
VOICE_PROVIDER=elevenlabs|openai_realtime decides who owns the audio when we do.
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
    "is_elevenlabs",
    "provider_name",
]


def provider_name() -> str:
    return (os.getenv("VOICE_PROVIDER") or "openai_realtime").strip()


def is_elevenlabs() -> bool:
    return provider_name() == "elevenlabs"


def get_provider() -> VoiceProvider:
    name = provider_name()
    if name == "elevenlabs":
        return ElevenLabsProvider()
    raise NotImplementedError(
        f"VOICE_PROVIDER={name!r} is not wired through voice.get_provider() yet. "
        "The OpenAI Realtime path still lives in calls.place_call / bridge.py. "
        "Set VOICE_PROVIDER=elevenlabs to use ElevenLabsProvider."
    )
