"""Proxy browser UI routes to the Next.js process on the VM."""
from __future__ import annotations

import os
from pathlib import Path

import httpx
from fastapi import HTTPException, Request, Response
from fastapi.responses import FileResponse

_STATIC = Path(__file__).resolve().parent / "static"
_UPSTREAM = os.getenv("WEB_UPSTREAM", "http://127.0.0.1:3000").rstrip("/")
# httpx decompresses the upstream body, so never forward encoding/length
# headers — browsers will refuse to render ("content encoding error").
_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
    "content-encoding",
}


async def proxy_to_web(request: Request, path: str) -> Response:
    """Forward a browser request to Next. Falls back to static /admin HTML."""
    if not path.startswith("/"):
        path = f"/{path}"
    url = f"{_UPSTREAM}{path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"

    headers = {k: v for k, v in request.headers.items() if k.lower() not in _HOP}
    body = await request.body()
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=False) as client:
            upstream = await client.request(
                request.method,
                url,
                headers=headers,
                content=body or None,
            )
    except httpx.ConnectError as exc:
        if path.rstrip("/") == "/admin" and (_STATIC / "admin.html").exists():
            return FileResponse(_STATIC / "admin.html")
        raise HTTPException(status_code=502, detail="admin UI is not running") from exc

    out_headers = {k: v for k, v in upstream.headers.items() if k.lower() not in _HOP}
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=out_headers,
        media_type=upstream.headers.get("content-type"),
    )
