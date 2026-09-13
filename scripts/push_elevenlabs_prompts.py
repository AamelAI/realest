#!/usr/bin/env python3
"""Push renter/listing prompt files and start_calls.availability to ElevenLabs.

    uv run python scripts/push_elevenlabs_prompts.py

Reads ELEVENLABS_API_KEY and agent ids from .env. Never prints the key.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.elevenlabs.io/v1/convai"
R, G, D, X = "\033[31m", "\033[32m", "\033[2m", "\033[0m"


def _headers(key: str) -> dict[str, str]:
    return {"xi-api-key": key, "content-type": "application/json"}


def _patch_prompt(client: httpx.Client, key: str, agent_id: str, prompt: str, label: str) -> int:
    r = client.patch(
        f"{API}/agents/{agent_id}",
        headers=_headers(key),
        json={
            "conversation_config": {"agent": {"prompt": {"prompt": prompt}}},
        },
        params={"version_description": f"update-{label}-prompt"},
        timeout=30,
    )
    if r.status_code >= 400:
        print(f"{R}✗{X} {label} prompt PATCH HTTP {r.status_code}: {r.text[:240]}")
        return 1
    check = client.get(f"{API}/agents/{agent_id}", headers=_headers(key), timeout=20)
    got = (((check.json().get("conversation_config") or {}).get("agent") or {})
           .get("prompt") or {}).get("prompt") or ""
    if prompt.strip() not in got:
        print(f"{R}✗{X} {label} prompt did not stick")
        return 1
    print(f"{G}✓{X} {label} system prompt updated ({len(got)} chars)")
    return 0


def _patch_start_calls(client: httpx.Client, key: str, renter_id: str) -> int:
    agent = client.get(f"{API}/agents/{renter_id}", headers=_headers(key), timeout=20)
    if agent.status_code >= 400:
        print(f"{R}✗{X} renter GET HTTP {agent.status_code}")
        return 1
    tool_ids = (((agent.json().get("conversation_config") or {}).get("agent") or {})
                .get("prompt") or {}).get("tool_ids") or []
    start = None
    for tid in tool_ids:
        t = client.get(f"{API}/tools/{tid}", headers=_headers(key), timeout=20)
        if t.status_code >= 400:
            continue
        body = t.json()
        name = (body.get("tool_config") or body).get("name") or body.get("name")
        if name == "start_calls":
            start = body
            start_id = tid
            break
    if start is None:
        print(f"{R}✗{X} start_calls tool not attached to renter agent — paste docs/elevenlabs-tools/start_calls.json")
        return 1

    cfg = start.get("tool_config") or start
    schema = ((cfg.get("api_schema") or {}).get("request_body_schema") or {})
    props = schema.get("properties")
    field = {
        "type": "string",
        "description": (
            "When the renter can view, as one short phrase, e.g. weeknights after 6 "
            "or Saturday morning. Empty if they did not say."
        ),
    }
    added = False
    if isinstance(props, list):
        if not any((p.get("id") or p.get("name")) == "availability" for p in props if isinstance(p, dict)):
            props.append({
                "id": "availability",
                "type": "string",
                "description": field["description"],
                "dynamic_variable": "",
                "constant_value": "",
                "value_type": "llm_prompt",
                "required": False,
                "enum": None,
            })
            added = True
    elif isinstance(props, dict):
        if "availability" not in props:
            props["availability"] = field
            added = True
    desc = cfg.get("description") or ""
    if "availability" not in desc.lower():
        cfg["description"] = (
            "Call this when the caller wants you to phone a listing agent. "
            "BEFORE calling it, ask when they are free for viewings and pass that as availability. "
            "The moment you call it, say: 'Wait until I gather all the information from the real estate agents.' "
            "Then stay silent until it returns and read the speak field aloud."
        )
        added = True
    if not added:
        print(f"{G}✓{X} start_calls already has availability")
        return 0

    payload = {"tool_config": cfg} if "tool_config" in start else cfg
    r = client.patch(f"{API}/tools/{start_id}", headers=_headers(key), json=payload, timeout=30)
    if r.status_code >= 400:
        print(f"{R}✗{X} start_calls PATCH HTTP {r.status_code}: {r.text[:240]}")
        return 1
    print(f"{G}✓{X} start_calls tool now includes availability")
    return 0


def main() -> int:
    load_dotenv(ROOT / ".env")
    key = (os.getenv("ELEVENLABS_API_KEY") or "").strip()
    renter = (os.getenv("ELEVENLABS_RENTER_AGENT_ID") or "").strip()
    listing = (os.getenv("ELEVENLABS_LISTING_AGENT_ID") or "").strip()
    if not key or not renter or not listing:
        print(f"{R}✗{X} need ELEVENLABS_API_KEY, ELEVENLABS_RENTER_AGENT_ID, ELEVENLABS_LISTING_AGENT_ID")
        return 1

    renter_prompt = (ROOT / "agent" / "renter-prompt.txt").read_text().strip()
    listing_prompt = (ROOT / "agent" / "listing-prompt.txt").read_text().strip()

    with httpx.Client() as client:
        failed = 0
        failed += _patch_prompt(client, key, renter, renter_prompt, "renter")
        failed += _patch_prompt(client, key, listing, listing_prompt, "listing")
        failed += _patch_start_calls(client, key, renter)
        return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
