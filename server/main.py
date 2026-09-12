"""FastAPI - the whole backend.

Every voice-agent tool is an HTTP webhook here. Every handler returns a short
string the agent reads ALOUD: keep it under 25 words and write it as speech.

You can build and test ~90% of this with curl, no phone involved. Do that.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Realest", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/state")
async def read_state(session: str):
    """The page polls this every 1-1.5s.

    Serialize with model_dump(mode="json") so enums come out as strings, or the
    TypeScript side breaks silently.

    TODO(hackathon): implement.
    """
    raise NotImplementedError


@app.post("/agent/preferences")
async def agent_preferences(payload: dict):
    """Caller described what they want, or reprioritized. Re-rank, then reply
    with one short spoken line. TODO(hackathon)."""
    raise NotImplementedError


@app.post("/agent/start-calls")
async def agent_start_calls(payload: dict):
    """Verify these listings. Fan out. TODO(hackathon)."""
    raise NotImplementedError


@app.post("/agent/outcome")
async def agent_outcome(payload: dict):
    """A listing agent told us something. Extract, write, RE-RANK THE WHOLE LIST.
    TODO(hackathon)."""
    raise NotImplementedError


@app.post("/agent/book")
async def agent_book(payload: dict):
    """Plain code does the write - the model only calls this. TODO(hackathon)."""
    raise NotImplementedError
