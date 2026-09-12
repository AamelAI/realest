"""Optional: exercises the REAL extract_outcome() path against whichever
provider server/chat.py picks up from the environment (OpenAI, OpenRouter, or
Gemini via its OpenAI-compatible endpoint). Skips cleanly if no key is
configured for any of them - never required for CI or a teammate's machine.

    uv run pytest tests/test_extraction_live.py -q
    GEMINI_API_KEY=... python3 tests/test_extraction_live.py    # also standalone
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "server"))

import calls  # noqa: E402

TRANSCRIPT = (
    "Agent: Hi, this is Dana.\n"
    "Us: Hi Dana, I'm an AI assistant calling on behalf of a client about "
    "700 Wellington St W. Is it still available?\n"
    "Agent: Yes, still available.\n"
    "Us: What does parking actually cost on top of the listed rent?\n"
    "Agent: Parking is an extra $180 a month, and there's a $40 locker fee too.\n"
    "Us: Got it. What's the pet policy?\n"
    "Agent: No pets, sorry.\n"
    "Us: Understood, thanks for your time."
)

_HAS_KEY = any(os.getenv(k, "").strip() for k in
               ("OPENAI_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY"))


@pytest.mark.skipif(not _HAS_KEY, reason="no OPENAI_API_KEY / OPENROUTER_API_KEY / "
                                          "GEMINI_API_KEY in the environment")
def test_extract_outcome_live() -> None:
    oc = asyncio.run(calls.extract_outcome(TRANSCRIPT, ["is there a locker?"]))
    print("  extracted:", oc.model_dump())

    assert oc.available is True
    assert any("180" in a for a in oc.addons), "expected the $180 parking add-on"
    assert oc.pets_allowed and "no" in oc.pets_allowed.lower(), \
        "pets_allowed should reflect what was actually said, not be invented"
    assert oc.source, "source must always be populated"
    assert oc.raw_transcript == TRANSCRIPT


if __name__ == "__main__":
    if not _HAS_KEY:
        print("SKIP: no OPENAI_API_KEY / OPENROUTER_API_KEY / GEMINI_API_KEY in the "
              "environment - set one in .env or export it, then rerun.")
        raise SystemExit(0)
    test_extract_outcome_live()
    print("\n\033[32mlive extraction checks pass\033[0m\n")
