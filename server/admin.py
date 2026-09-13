"""Read-only admin monitor. In-memory webhook ring + ElevenLabs history.

Does not touch SessionState. Lost on process restart; History still works
via ElevenLabs. Never stores API keys.
"""
from __future__ import annotations

import time
from collections import deque

from fastapi import HTTPException

import calls
import listings as L
import state as store

EVENT_CAP = 200
RAIL = ("init", "preferences", "start_calls", "outcome", "book")


_events: deque[dict] = deque(maxlen=EVENT_CAP)


def reset() -> None:
    _events.clear()


def record(
    session_id: str,
    role: str,
    tool: str,
    status: str = "ok",
    summary: str = "",
    conversation_id: str = "",
    listing_id: str = "",
) -> dict:
    """Append one short webhook hit. Summaries stay one line, no transcripts."""
    ev = {
        "t": time.time(),
        "session_id": session_id or "",
        "conversation_id": (conversation_id or "").strip(),
        "role": role,
        "tool": tool,
        "status": status,
        "summary": (summary or "")[:160],
        "listing_id": listing_id or "",
    }
    _events.append(ev)
    return ev


def events_for(session_id: str) -> list[dict]:
    return [e for e in _events if e["session_id"] == session_id]


def _renter_cid(session_id: str) -> str:
    return calls.renter_conversation(session_id)


def _live_calls() -> list[dict]:
    by_sid: dict[str, dict] = {}

    for sid, cid in calls._renter_conversation.items():
        by_sid[sid] = _empty_live(sid, "renter", cid)

    for (sid, lid), cid in calls._conversations.items():
        key = f"{sid}:{lid}"
        row = _empty_live(sid, "listing", cid, listing_id=lid)
        s = store.get(sid)
        card = next((st for st in (s.listings if s else []) if st.listing_id == lid), None)
        if card is not None:
            row["status"] = card.status.value
        lst = L.by_id(lid)
        if lst:
            row["summary"] = lst.address.split(",")[0]
        by_sid[key] = row

    for sid in store.all_ids():
        s = store.get(sid)
        if s is None or sid in by_sid:
            continue
        if not s.listings and not events_for(sid):
            continue
        by_sid[sid] = _empty_live(sid, "renter", _renter_cid(sid))

    for ev in _events:
        sid = ev["session_id"]
        if not sid:
            continue
        if ev["role"] == "listing" and ev.get("listing_id"):
            key = f"{sid}:{ev['listing_id']}"
        else:
            key = sid
        row = by_sid.get(key)
        if row is None:
            row = _empty_live(sid, ev["role"], ev.get("conversation_id") or "",
                              listing_id=ev.get("listing_id") or "")
            by_sid[key] = row
        if ev.get("conversation_id") and not row["conversation_id"]:
            row["conversation_id"] = ev["conversation_id"]
        row["events"].append(ev)
        if ev["tool"] not in row["tools"]:
            row["tools"].append(ev["tool"])
        row["current_tool"] = ev["tool"]
        if ev["status"] == "started":
            row["status"] = "in_flight"
        elif ev["tool"] == "start_calls" and ev["status"] == "done" and row["status"] == "in_flight":
            row["status"] = "open"

    out = list(by_sid.values())
    out.sort(key=lambda r: (r["events"][-1]["t"] if r["events"] else 0), reverse=True)
    return out


def _empty_live(session_id: str, role: str, conversation_id: str, listing_id: str = "") -> dict:
    return {
        "id": f"{session_id}:{listing_id}" if listing_id else session_id,
        "session_id": session_id,
        "conversation_id": conversation_id,
        "role": role,
        "listing_id": listing_id,
        "status": "open",
        "current_tool": "",
        "tools": [],
        "events": [],
        "summary": "",
        "transcript": "",
        "rail": list(RAIL),
    }


async def live_payload() -> dict:
    rows = _live_calls()
    if not rows:
        return {"calls": []}
    try:
        import voice
        if voice.is_elevenlabs():
            provider = voice.get_provider()
            for row in rows:
                cid = row.get("conversation_id") or ""
                if not cid:
                    continue
                try:
                    data = await provider.get_conversation(cid)
                    row["transcript"] = calls.flatten_transcript(data)
                    st = calls._conversation_status(data)
                    if st:
                        row["el_status"] = st
                except Exception:
                    pass
    except Exception:
        pass
    return {"calls": rows}


def _phone_meta(data: dict) -> tuple[str, str, str]:
    pc = (data.get("metadata") or {}).get("phone_call") or {}
    direction = str(pc.get("direction") or pc.get("type") or "").lower()
    return (
        str(pc.get("external_number") or ""),
        str(pc.get("agent_number") or ""),
        direction or "?",
    )


def _tool_names(data: dict) -> list[str]:
    names: list[str] = []
    for name, _params, _res in calls.tools_of(data):
        if name not in names:
            names.append(name)
    return names


def _row_from_list(item: dict, role: str) -> dict:
    md = item.get("metadata") or {}
    return {
        "conversation_id": item.get("conversation_id") or "",
        "role": role,
        "status": item.get("status") or md.get("status") or "",
        "direction": "",
        "duration_secs": item.get("call_duration_secs") or md.get("call_duration_secs"),
        "started_at": item.get("start_time_unix_secs")
        or md.get("start_time_unix_secs")
        or 0,
        "tools": [],
    }


async def history_payload(limit: int = 20) -> dict:
    try:
        import voice
        provider = voice.ElevenLabsProvider()
    except Exception:
        return {"calls": [], "error": "elevenlabs unavailable"}
    if not provider.api_key:
        return {"calls": [], "error": "ELEVENLABS_API_KEY is not set"}

    agents = [
        ("renter", provider.renter_agent_id),
        ("listing", provider.listing_agent_id),
    ]
    rows: list[dict] = []
    for role, aid in agents:
        if not aid:
            continue
        try:
            data = await provider.list_conversations(aid, page_size=min(limit, 50))
        except Exception as exc:
            return {"calls": rows, "error": str(exc)[:160]}
        for item in data.get("conversations") or []:
            if isinstance(item, dict):
                rows.append(_row_from_list(item, role))
    rows.sort(key=lambda r: int(r.get("started_at") or 0), reverse=True)
    rows = rows[:limit]

    async def enrich(row: dict) -> None:
        cid = row.get("conversation_id") or ""
        if not cid:
            return
        try:
            d = await provider.get_conversation(cid)
        except Exception:
            return
        _ext, _agent, direction = _phone_meta(d)
        row["direction"] = direction
        row["tools"] = _tool_names(d)
        md = d.get("metadata") or {}
        row["status"] = d.get("status") or row["status"]
        row["duration_secs"] = d.get("call_duration_secs") or md.get("call_duration_secs") or row.get("duration_secs")

    import asyncio
    await asyncio.gather(*(enrich(r) for r in rows), return_exceptions=True)
    return {"calls": rows}


def _role_for_agent(agent_id: str) -> str:
    import voice
    p = voice.ElevenLabsProvider()
    if agent_id and agent_id == p.listing_agent_id:
        return "listing"
    return "renter"


async def detail_payload(conversation_id: str) -> dict:
    cid = (conversation_id or "").strip()
    if not cid:
        raise HTTPException(status_code=400, detail="missing conversation_id")
    import voice
    provider = voice.ElevenLabsProvider()
    if not provider.api_key:
        raise HTTPException(status_code=502, detail="ELEVENLABS_API_KEY is not set")
    try:
        data = await provider.get_conversation(cid)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)[:200]) from exc
    md = data.get("metadata") or {}
    agent_id = str(data.get("agent_id") or md.get("agent_id") or "")
    tools = []
    for name, params, res in calls.tools_of(data):
        val = res.get("result_value") or res.get("result") or res.get("error") or ""
        tools.append({
            "name": name,
            "params": params if isinstance(params, str) else str(params),
            "result": str(val)[:800],
            "error": bool(res.get("is_error")),
        })
    return {
        "conversation_id": cid,
        "role": _role_for_agent(agent_id),
        "status": data.get("status") or md.get("status") or "",
        "direction": _phone_meta(data)[2],
        "duration_secs": data.get("call_duration_secs") or md.get("call_duration_secs"),
        "started_at": data.get("start_time_unix_secs") or md.get("start_time_unix_secs") or 0,
        "turns": calls.transcript_turns(data),
        "tools": tools,
        "transcript": calls.flatten_transcript(data),
    }
