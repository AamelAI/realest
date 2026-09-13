#!/usr/bin/env python3
"""Push renter/listing prompt files and start_calls.availability to ElevenLabs.

    uv run python scripts/push_elevenlabs_prompts.py

Reads ELEVENLABS_API_KEY and agent ids from .env. Never prints the key.
"""
from __future__ import annotations

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
        params={
            "version_description": f"update-{label}-prompt",
            "enable_versioning_if_not_enabled": "true",
        },
        timeout=30,
    )
    if r.status_code >= 400:
        print(f"{R}✗{X} {label} prompt PATCH HTTP {r.status_code}: {r.text[:240]}")
        return 1
    check = client.get(f"{API}/agents/{agent_id}", headers=_headers(key), timeout=20)
    got = (((check.json().get("conversation_config") or {}).get("agent") or {})
           .get("prompt") or {}).get("prompt") or ""
    if prompt.strip() not in got:
        print(f"{R}✗{X} {label} prompt did not stick", flush=True)
        return 1
    ver = check.json().get("version_id") or r.json().get("version_id") or ""
    print(f"{G}✓{X} {label} system prompt updated ({len(got)} chars) version={ver}", flush=True)
    return 0


def _tool_name(body: dict) -> str:
    return str((body.get("tool_config") or body).get("name") or body.get("name") or "")


def _props(cfg: dict):
    return ((cfg.get("api_schema") or {}).get("request_body_schema") or {}).get("properties")


def _ensure_prop(
    props,
    field_id: str,
    description: str,
    required: bool = False,
    dynamic_variable: str = "",
) -> bool:
    """Add or refresh a string body field. Returns True when mutated."""
    value_type = "dynamic_variable" if dynamic_variable else "llm_prompt"
    if isinstance(props, list):
        for p in props:
            if isinstance(p, dict) and (p.get("id") or p.get("name")) == field_id:
                changed = False
                if p.get("description") != description:
                    p["description"] = description
                    changed = True
                if dynamic_variable and p.get("dynamic_variable") != dynamic_variable:
                    p["dynamic_variable"] = dynamic_variable
                    p["value_type"] = "dynamic_variable"
                    changed = True
                return changed
        props.append({
            "id": field_id,
            "type": "string",
            "description": description,
            "dynamic_variable": dynamic_variable,
            "constant_value": "",
            "value_type": value_type,
            "required": required,
            "enum": None,
        })
        return True
    if isinstance(props, dict):
        cur = props.get(field_id)
        if isinstance(cur, dict):
            changed = False
            if cur.get("description") != description:
                cur["description"] = description
                changed = True
            if dynamic_variable:
                if cur.get("dynamic_variable") != dynamic_variable:
                    cur["dynamic_variable"] = dynamic_variable
                    changed = True
            return changed
        props[field_id] = {"type": "string", "description": description}
        if dynamic_variable:
            props[field_id]["dynamic_variable"] = dynamic_variable
        return True
    return False


def _patch_renter_tools(client: httpx.Client, key: str, renter_id: str) -> int:
    agent = client.get(f"{API}/agents/{renter_id}", headers=_headers(key), timeout=20)
    if agent.status_code >= 400:
        print(f"{R}✗{X} renter GET HTTP {agent.status_code}")
        return 1
    tool_ids = (((agent.json().get("conversation_config") or {}).get("agent") or {})
                .get("prompt") or {}).get("tool_ids") or []
    by_name: dict[str, tuple[str, dict]] = {}
    for tid in tool_ids:
        t = client.get(f"{API}/tools/{tid}", headers=_headers(key), timeout=20)
        if t.status_code >= 400:
            continue
        body = t.json()
        by_name[_tool_name(body)] = (tid, body)

    failed = 0
    start_desc = (
        "Call this when the caller wants you to phone a listing agent. "
        "BEFORE calling it, ask when they are free for viewings and pass that as availability. "
        "The moment you call it, say: 'Wait until I gather all the information from the real estate agents.' "
        "Then stay silent until it returns — that can take a minute while listing calls finish — "
        "and read the speak field aloud. Do not book or call book_viewing until it returns."
    )
    book_desc = (
        "Call this when the caller confirms or rejects a viewing, and only after "
        "start_calls has returned with the listing results. decision is confirm or reject. "
        "That texts the renter and the listing agent. After it returns, read the speak field aloud."
    )
    failed += _write_tool(
        client, key, by_name, "start_calls", start_desc,
        [("availability",
          "When the renter can view, as one short phrase, e.g. weeknights after 6 "
          "or Saturday morning. Empty if they did not say.")],
    )
    failed += _write_tool(
        client, key, by_name, "book_viewing", book_desc,
        [("decision",
          "confirm to book and text the landlord and renter a confirmation. "
          "reject to text the landlord that the renter is passing. Default confirm."),
         ("caller_phone",
          "Inbound caller from system__caller_id. Do not invent it.",
          "system__caller_id")],
    )
    return failed


def _patch_listing_tools(client: httpx.Client, key: str, listing_id: str) -> int:
    agent = client.get(f"{API}/agents/{listing_id}", headers=_headers(key), timeout=20)
    if agent.status_code >= 400:
        print(f"{R}✗{X} listing GET HTTP {agent.status_code}")
        return 1
    tool_ids = (((agent.json().get("conversation_config") or {}).get("agent") or {})
                .get("prompt") or {}).get("tool_ids") or []
    by_name: dict[str, tuple[str, dict]] = {}
    for tid in tool_ids:
        t = client.get(f"{API}/tools/{tid}", headers=_headers(key), timeout=20)
        if t.status_code >= 400:
            continue
        body = t.json()
        by_name[_tool_name(body)] = (tid, body)
    outcome_desc = (
        "Call this at the end of the call with everything the listing agent actually said. "
        "Only fill a field if they said it. Never guess. After it returns, say goodbye "
        "and that we will be in touch, then hang up."
    )
    return _write_tool(client, key, by_name, "record_outcome", outcome_desc, [])


def _write_tool(
    client: httpx.Client,
    key: str,
    by_name: dict[str, tuple[str, dict]],
    name: str,
    description: str,
    fields: list[tuple[str, str]],
) -> int:
    if name not in by_name:
        print(f"{R}✗{X} {name} not attached to renter agent")
        return 1
    tid, body = by_name[name]
    cfg = body.get("tool_config") or body
    cfg["description"] = description
    props = _props(cfg)
    for item in fields:
        if len(item) == 3:
            field_id, desc, dyn = item
            _ensure_prop(props, field_id, desc, dynamic_variable=dyn)
        else:
            field_id, desc = item
            _ensure_prop(props, field_id, desc)
    payload = {"tool_config": cfg} if "tool_config" in body else cfg
    r = client.patch(f"{API}/tools/{tid}", headers=_headers(key), json=payload, timeout=30)
    if r.status_code >= 400:
        print(f"{R}✗{X} {name} PATCH HTTP {r.status_code}: {r.text[:240]}")
        return 1
    check = client.get(f"{API}/tools/{tid}", headers=_headers(key), timeout=20).json()
    got = _tool_name(check)
    print(f"{G}✓{X} {got} tool updated")
    return 0


def main() -> int:
    print("loading .env", flush=True)
    load_dotenv(ROOT / ".env")
    key = (os.getenv("ELEVENLABS_API_KEY") or "").strip()
    renter = (os.getenv("ELEVENLABS_RENTER_AGENT_ID") or "").strip()
    listing = (os.getenv("ELEVENLABS_LISTING_AGENT_ID") or "").strip()
    if not key or not renter or not listing:
        print(f"{R}✗{X} need ELEVENLABS_API_KEY, ELEVENLABS_RENTER_AGENT_ID, ELEVENLABS_LISTING_AGENT_ID")
        return 1

    renter_prompt = (ROOT / "agent" / "renter-prompt.txt").read_text().strip()
    listing_prompt = (ROOT / "agent" / "listing-prompt.txt").read_text().strip()

    skip = (os.getenv("ELEVENLABS_INSECURE_SKIP_VERIFY") or "").strip().lower() in {
        "1", "true", "yes",
    }
    print(f"{D}pushing prompts/tools (verify={'off' if skip else 'on'}){X}", flush=True)
    with httpx.Client(verify=not skip, timeout=30.0) as client:
        failed = 0
        failed += _patch_prompt(client, key, renter, renter_prompt, "renter")
        failed += _patch_prompt(client, key, listing, listing_prompt, "listing")
        failed += _patch_renter_tools(client, key, renter)
        failed += _patch_listing_tools(client, key, listing)
        return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
