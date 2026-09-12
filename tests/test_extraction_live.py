"""Optional: exercises the REAL extract_outcome() path against the actual
OpenAI API. Skips cleanly if no key is configured - never required for CI or
a teammate's machine.

    OPENAI_API_KEY=sk-... PYTHONPATH=server python3 tests/test_extraction_live.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "server"))

if not os.getenv("OPENAI_API_KEY"):
    print("SKIP: no OPENAI_API_KEY in the environment - set it in .env or export it, then rerun.")
    raise SystemExit(0)

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

ok = True


def check(label: str, cond: bool, detail: str = "") -> None:
    global ok
    print(("  \033[32mPASS\033[0m " if cond else "  \033[31mFAIL\033[0m ") + label + (f"  {detail}" if detail else ""))
    ok = ok and cond


async def run() -> None:
    oc = await calls.extract_outcome(TRANSCRIPT, ["is there a locker?"])
    print("  extracted:", oc.model_dump())
    check("available = True", oc.available is True)
    check("addons mention parking $180", any("180" in a for a in oc.addons))
    check("pets_allowed captured, not invented as something else",
          bool(oc.pets_allowed) and "no" in oc.pets_allowed.lower())
    check("source populated", bool(oc.source))
    check("raw_transcript preserved", oc.raw_transcript == TRANSCRIPT)


asyncio.run(run())
print("\n\033[32mlive extraction checks pass\033[0m\n" if ok else "\n\033[31mLIVE EXTRACTION CHECKS FAILING\033[0m\n")
raise SystemExit(0 if ok else 1)
