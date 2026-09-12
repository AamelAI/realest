"""Text transport for the renter agent.

Same prompt, same tools, same dispatch() as the voice bridge — only the
transport differs. That is the whole point of the seam: D2 and D3 can exercise
the entire product by typing, while D4 lands voice in parallel.

    POST /chat  {"session_id": "demo", "message": "2 bed in King West under 3400"}
              -> {"reply": "...", "session_id": "demo", "link": "https://.../s/demo"}

    GET  /chat  -> a plain harness page for testing without curl.

Model: whichever key is present. OpenAI first, OpenRouter second — both speak
the OpenAI chat-completions shape, so one code path covers both.
"""
from __future__ import annotations

import json
import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from openai import AsyncOpenAI

import state as store
from bridge import RENTER_PROMPT, RENTER_TOOLS, dispatch

MAX_TOOL_HOPS = 4          # a turn that needs more than this is looping
HISTORY_TURNS = 24         # keep the transcript bounded

_history: dict[str, list[dict]] = {}


# Every provider below speaks the OpenAI chat-completions shape, so one code
# path covers all three. Gemini exposes a compatibility endpoint; note it needs
# `gemini-flash-latest` — the pinned 2.5 ids are closed to new keys.
PROVIDERS = (
    ("OPENAI_API_KEY", None, "gpt-4.1-mini"),
    ("OPENROUTER_API_KEY", "https://openrouter.ai/api/v1", "openai/gpt-4.1-mini"),
    ("GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta/openai/",
     "gemini-flash-latest"),
)


def _client() -> tuple[AsyncOpenAI, str]:
    """First key present wins. CHAT_MODEL overrides the default for that provider."""
    for env_key, base_url, default_model in PROVIDERS:
        if key := os.getenv(env_key, "").strip():
            kw = {"api_key": key}
            if base_url:
                kw["base_url"] = base_url
            return AsyncOpenAI(**kw), os.getenv("CHAT_MODEL", default_model)
    raise RuntimeError(
        "set one of OPENAI_API_KEY / OPENROUTER_API_KEY / GEMINI_API_KEY in .env"
    )


def _tools() -> list[dict]:
    """agent/tools.json is in Realtime shape; chat completions nests under
    `function`. Same definitions, one adapter, so the two transports can never
    drift apart."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            },
        }
        for t in RENTER_TOOLS
    ]


def _board(session_id: str) -> str:
    """Compact shortlist for the model's eyes only. Never spoken."""
    s = store.get(session_id)
    if not s or not s.listings:
        return ""
    import listings as L
    rows = []
    for st in s.listings:
        lst = L.by_id(st.listing_id)
        addr = lst.address if lst else ""
        rows.append(f"{st.listing_id}={addr} [{st.status.value}]")
    return ("\n\n(current shortlist, for your reference only - never read ids "
            "aloud; pass them to start_calls and book_viewing: "
            + "; ".join(rows) + ")")


async def turn(session_id: str, message: str) -> str:
    """One user message in, one assistant reply out. Tools fire in between."""
    client, model = _client()

    msgs = _history.setdefault(
        session_id, [{"role": "system", "content": RENTER_PROMPT}]
    )
    msgs.append({"role": "user", "content": message})

    for _ in range(MAX_TOOL_HOPS):
        res = await client.chat.completions.create(
            model=model, messages=msgs, tools=_tools(), tool_choice="auto"
        )
        m = res.choices[0].message
        msgs.append(m.model_dump(exclude_none=True))

        if not m.tool_calls:
            reply = m.content or ""
            break

        for tc in m.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            # Exactly the call the voice bridge makes.
            out = await dispatch(tc.function.name, args, session_id)
            # dispatch() returns only the line to SPEAK. A voice caller hears
            # addresses and that's enough, but a model needs the ids to pass
            # back to start_calls - without them it echoes one address and only
            # one listing gets called. Append the board as context, not speech.
            msgs.append({"role": "tool", "tool_call_id": tc.id,
                         "content": out + _board(session_id)})
    else:
        reply = "Sorry, I got tangled up there. Say that again?"

    # Keep the page header in sync whether the user typed or spoke.
    if reply:
        await store.mutate(session_id, lambda s: setattr(s, "agent_says", reply))

    # Bound the transcript: system prompt + the last N exchanges.
    if len(msgs) > HISTORY_TURNS:
        _history[session_id] = [msgs[0]] + msgs[-HISTORY_TURNS:]

    return reply


def reset(session_id: str) -> None:
    _history.pop(session_id, None)


HARNESS = """<!doctype html><meta charset=utf-8>
<title>Realest · chat harness</title>
<style>
 body{background:#fcfcfb;color:#15171c;font:14px/1.5 ui-monospace,monospace;
      margin:0;padding:24px;max-width:760px}
 h1{font:600 15px/1 ui-monospace,monospace;margin:0 0 4px}
 p.sub{color:#8a8d95;margin:0 0 20px}
 #log{border-top:1px solid #dcdee2}
 .t{border-bottom:1px solid #ededef;padding:10px 0;white-space:pre-wrap}
 .who{color:#8a8d95}
 .a .who{color:#17633f}
 form{display:flex;gap:10px;margin-top:18px}
 input{flex:1;border:0;border-bottom:1px solid #15171c;background:none;
       font:inherit;padding:8px 0;color:inherit}
 input:focus{outline:none}
 button{border:0;background:#15171c;color:#fcfcfb;font:inherit;padding:8px 16px;cursor:pointer}
 a{color:#15171c}
</style>
<h1>Realest &middot; chat harness</h1>
<p class=sub>Same prompt, same tools, same dispatch as the phone. Session
<b id=sid></b> &middot; <a id=page target=_blank>open the page</a></p>
<div id=log></div>
<form id=f><input id=m autocomplete=off autofocus
  placeholder="2 bed in King West under 3400, need parking"><button>Send</button></form>
<script>
const sid = new URLSearchParams(location.search).get('s')
  || 'dev-' + Math.random().toString(36).slice(2, 7);
sid_.textContent = sid;
page.href = '/s/' + sid;
function add(who, text, cls) {
  const d = document.createElement('div');
  d.className = 't ' + (cls || '');
  d.innerHTML = '<span class=who>' + who + '</span>  ' + text.replace(/</g, '&lt;');
  log.append(d); d.scrollIntoView();
}
f.onsubmit = async e => {
  e.preventDefault();
  const text = m.value.trim(); if (!text) return;
  m.value = ''; add('you', text);
  const r = await fetch('/chat', {
    method: 'POST', headers: {'content-type': 'application/json'},
    body: JSON.stringify({session_id: sid, message: text}),
  });
  const j = await r.json();
  add('agent', j.reply || j.error || '(no reply)', 'a');
};
</script>
"""


def attach(app: FastAPI) -> None:
    @app.post("/chat")
    async def chat(payload: dict):
        sid = payload.get("session_id") or "demo"
        msg = (payload.get("message") or "").strip()
        if not msg:
            return {"error": "message is required", "session_id": sid}
        try:
            reply = await turn(sid, msg)
        except Exception as exc:  # never 500 into the harness mid-demo
            return {"error": str(exc)[:300], "session_id": sid}
        web = os.getenv("WEB_URL", "http://localhost:3000").rstrip("/")
        return {"reply": reply, "session_id": sid, "link": f"{web}/s/{sid}"}

    @app.post("/chat/reset")
    async def chat_reset(payload: dict):
        reset(payload.get("session_id") or "demo")
        return {"ok": True}

    @app.get("/chat")
    def harness():
        # `sid` is taken by the <b> element id, so the script uses sid_.
        return HTMLResponse(HARNESS.replace('id=sid>', 'id=sid_>'))
