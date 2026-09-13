"""ElevenLabs Conversational AI over Twilio.

One POST places a call. Audio, barge-in and TwiML stay on their side.
No listing or session imports — the caller passes plain strings.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os

import httpx

from voice.types import CallHandle, Role

log = logging.getLogger("realest.elevenlabs")

API = "https://api.elevenlabs.io/v1"
OUTBOUND = f"{API}/convai/twilio/outbound-call"
USER = f"{API}/user"
CONVERSATION = f"{API}/convai/conversations"
MONITOR = "wss://api.elevenlabs.io/v1/convai/conversations/{id}/monitor"


class ElevenLabsError(RuntimeError):
    pass


class ElevenLabsProvider:
    provider = "elevenlabs"

    def __init__(self, env: dict[str, str] | None = None) -> None:
        src = env if env is not None else os.environ
        self.api_key = (src.get("ELEVENLABS_API_KEY") or "").strip()
        self.phone_number_id = (src.get("ELEVENLABS_PHONE_NUMBER_ID") or "").strip()
        self.renter_agent_id = (src.get("ELEVENLABS_RENTER_AGENT_ID") or "").strip()
        self.listing_agent_id = (src.get("ELEVENLABS_LISTING_AGENT_ID") or "").strip()
        # Venue Wi-Fi often MITMs TLS. Demo only — never leave this on in a real deploy.
        flag = (src.get("ELEVENLABS_INSECURE_SKIP_VERIFY") or "").strip().lower()
        self.verify = flag not in {"1", "true", "yes"}

    def _client(self, timeout: float) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=timeout, verify=self.verify)

    def configured(self) -> bool:
        return bool(
            self.api_key
            and self.phone_number_id
            and self.renter_agent_id
            and self.listing_agent_id
        )

    def missing(self) -> list[str]:
        needed = {
            "ELEVENLABS_API_KEY": self.api_key,
            "ELEVENLABS_PHONE_NUMBER_ID": self.phone_number_id,
            "ELEVENLABS_RENTER_AGENT_ID": self.renter_agent_id,
            "ELEVENLABS_LISTING_AGENT_ID": self.listing_agent_id,
        }
        return [k for k, v in needed.items() if not v]

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ElevenLabsError("ELEVENLABS_API_KEY is not set")
        return {"xi-api-key": self.api_key, "content-type": "application/json"}

    def _agent_id(self, role: Role) -> str:
        agent_id = self.listing_agent_id if role == "listing" else self.renter_agent_id
        if not agent_id:
            key = "ELEVENLABS_LISTING_AGENT_ID" if role == "listing" else "ELEVENLABS_RENTER_AGENT_ID"
            raise ElevenLabsError(f"{key} is not set — create the {role} agent in the dashboard")
        if not self.phone_number_id:
            raise ElevenLabsError(
                "ELEVENLABS_PHONE_NUMBER_ID is not set — import the Twilio number in ElevenLabs"
            )
        return agent_id

    def _raise_http(self, r: httpx.Response, action: str) -> None:
        if r.status_code == 401:
            raise ElevenLabsError(
                "401 — ELEVENLABS_API_KEY rejected. Copy a key from ElevenLabs → Profile → API Keys."
            )
        if r.status_code >= 400:
            body = (r.text or "")[:240]
            raise ElevenLabsError(f"{action} failed HTTP {r.status_code}: {body}")

    async def health(self) -> dict:
        async with self._client(15) as client:
            r = await client.get(USER, headers=self._headers())
        self._raise_http(r, "health")
        data = r.json()
        return {
            "ok": True,
            "provider": self.provider,
            "subscription": (data.get("subscription") or {}).get("tier"),
            "configured": self.configured(),
            "missing": self.missing(),
        }

    async def place_outbound(
        self,
        to_number: str,
        role: Role,
        dynamic_variables: dict[str, str] | None = None,
    ) -> CallHandle:
        payload: dict = {
            "agent_id": self._agent_id(role),
            "agent_phone_number_id": self.phone_number_id,
            "to_number": to_number,
        }
        if dynamic_variables:
            payload["conversation_initiation_client_data"] = {
                "dynamic_variables": dynamic_variables,
            }

        async with self._client(20) as client:
            r = await client.post(OUTBOUND, headers=self._headers(), json=payload)
        self._raise_http(r, "outbound call")
        data = r.json()
        if data.get("success") is False:
            raise ElevenLabsError(data.get("message") or "outbound call was not initiated")
        return CallHandle(
            conversation_id=data.get("conversation_id"),
            call_sid=data.get("callSid") or data.get("call_sid"),
            provider=self.provider,
        )

    async def get_conversation(self, conversation_id: str) -> dict:
        async with self._client(15) as client:
            r = await client.get(
                f"{CONVERSATION}/{conversation_id}",
                headers=self._headers(),
            )
        self._raise_http(r, "get conversation")
        return r.json()

    async def list_conversations(self, agent_id: str, page_size: int = 20) -> dict:
        async with self._client(20) as client:
            r = await client.get(
                CONVERSATION,
                headers=self._headers(),
                params={"agent_id": agent_id, "page_size": page_size},
            )
        self._raise_http(r, "list conversations")
        return r.json()

    async def inject_context(self, conversation_id: str, text: str) -> bool:
        """Push a contextual_update into a live renter call. Never raises.

        Uses the enterprise monitor socket. Returns False if Monitoring is off,
        the call already ended, or the key is missing.
        """
        cid = (conversation_id or "").strip()
        body = (text or "").strip()
        if not cid or not body or not self.api_key:
            return False
        async def _send() -> bool:
            import websockets
            uri = MONITOR.format(id=cid)
            async with websockets.connect(
                uri,
                additional_headers={"xi-api-key": self.api_key},
                open_timeout=5,
                close_timeout=2,
            ) as ws:
                await ws.send(json.dumps({
                    "command_type": "contextual_update",
                    "parameters": {"contextual_update": body},
                }))
            return True

        try:
            return await asyncio.wait_for(_send(), timeout=8)
        except Exception as exc:
            log.warning("inject_context[%s]: %s", cid, exc)
            return False
