#!/usr/bin/env bash
# Browse ElevenLabs call logs. Uses ELEVENLABS_* from .env — never prints the key.
#
#   make calls
#   bash scripts/call_logs.sh
#   bash scripts/call_logs.sh conv_5101m2bywwfmen7rb6tekt8xdb22
#
# Stays open. Arrow / click a row, Enter to open logs, Enter again to go back. q quits.
#
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if [[ -z "${ELEVENLABS_API_KEY:-}" ]]; then
  echo "✗ ELEVENLABS_API_KEY missing — put it in .env"
  exit 1
fi
if [[ -z "${ELEVENLABS_RENTER_AGENT_ID:-}" || -z "${ELEVENLABS_LISTING_AGENT_ID:-}" ]]; then
  echo "✗ need ELEVENLABS_RENTER_AGENT_ID and ELEVENLABS_LISTING_AGENT_ID in .env"
  exit 1
fi

export ELEVENLABS_API_KEY ELEVENLABS_RENTER_AGENT_ID ELEVENLABS_LISTING_AGENT_ID

exec python3 -u - "$ROOT" "${1:-}" <<'PY'
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.elevenlabs.io/v1/convai/conversations"
KEY = os.environ["ELEVENLABS_API_KEY"]
AGENTS = [
    ("renter", os.environ["ELEVENLABS_RENTER_AGENT_ID"]),
    ("listing", os.environ["ELEVENLABS_LISTING_AGENT_ID"]),
]
PAGE = 20

DIM, BOLD, RED, GRN, YEL, CYN, RST, REV, HIDE, SHOW = (
    "\033[2m", "\033[1m", "\033[31m", "\033[32m", "\033[33m", "\033[36m",
    "\033[0m", "\033[7m", "\033[?25l", "\033[?25h",
)
CLEAR = "\033[2J\033[H"
MOUSE_ON, MOUSE_OFF = "\033[?1000h\033[?1006h", "\033[?1000l\033[?1006l"


def get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"xi-api-key": KEY})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"{RED}✗ ElevenLabs {e.code}{RST}  {body}") from e


def when(unix) -> str:
    if not unix:
        return "?"
    return dt.datetime.fromtimestamp(int(unix)).strftime("%Y-%m-%d %H:%M")


def phone(d: dict) -> tuple[str, str, str]:
    pc = (d.get("metadata") or {}).get("phone_call") or {}
    ext = pc.get("external_number") or "?"
    agent = pc.get("agent_number") or "?"
    direction = (pc.get("direction") or pc.get("type") or "").lower()
    if direction == "outbound":
        return ext, agent, "out"
    if direction == "inbound":
        return ext, agent, "in"
    return ext, agent, direction or "?"


def list_calls() -> list[dict]:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    rows: list[dict] = []
    for role, aid in AGENTS:
        data = get(f"{API}?agent_id={aid}&page_size={PAGE}")
        for c in data.get("conversations") or []:
            rows.append({**c, "_role": role})
    rows.sort(key=lambda c: int(c.get("start_time_unix_secs") or 0), reverse=True)

    def enrich(row: dict) -> dict:
        cid = row.get("conversation_id")
        if not cid:
            return row
        try:
            d = get(f"{API}/{cid}")
        except Exception:
            return row
        ext, agent_n, direction = phone(d)
        names = []
        for name, _params, _res in tools_of(d):
            if name not in names:
                names.append(name)
        row["_from"] = ext
        row["_to"] = agent_n
        row["_dir"] = direction
        row["_tools"] = names
        row["_detail"] = d
        return row

    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(enrich, r) for r in rows]
        for _ in as_completed(futs):
            pass
    return rows


def row_text(i: int, c: dict) -> str:
    start = when(c.get("start_time_unix_secs") or c.get("start_time"))
    role = c.get("_role", "?")
    status = c.get("status") or "?"
    dur = c.get("call_duration_secs")
    dur_s = f"{dur}s" if dur is not None else "?"
    path = f"{c.get('_from', '?')} → {c.get('_to', '?')}"
    tools = ",".join(c.get("_tools") or []) or "—"
    return (
        f"{i:>2}  {start}  {role:<7}  {c.get('_dir', '?'):<3}  "
        f"{status:<8}  {dur_s:>4}  {path}  {tools}"
    )


def _getch() -> str:
    return os.read(sys.stdin.fileno(), 1).decode("utf-8", "replace")


def _read_keys() -> str:
    """One key or escape sequence. Empty string means nothing."""
    ch = _getch()
    if ch != "\x1b":
        return ch
    rest = _getch()
    if rest != "[":
        return ch
    nxt = _getch()
    if nxt in "ABCD":
        return {"A": "up", "B": "down", "C": "right", "D": "left"}[nxt]
    # SGR mouse: ESC [ < btn ; x ; y M/m
    if nxt == "<":
        buf = nxt
        while True:
            c = _getch()
            buf += c
            if c in "Mm":
                break
        return "mouse:" + buf
    return ch


def pick(rows: list[dict], idx: int = 0) -> tuple[str, int]:
    """Live list. Returns (open|refresh|quit, selected_index)."""
    import shutil
    import termios
    import tty

    if not rows:
        print("  (no conversations)  press q")
        while _read_keys() not in {"q", "Q", "\x03"}:
            pass
        return "quit", 0

    idx = max(0, min(idx, len(rows) - 1))
    header_lines = 4  # title, hint, columns, rule
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        sys.stdout.write(HIDE + MOUSE_ON)
        sys.stdout.flush()
        while True:
            h = shutil.get_terminal_size().lines
            visible = max(3, h - header_lines - 2)
            if idx < 0:
                idx = 0
            if idx >= len(rows):
                idx = len(rows) - 1
            top = 0
            if idx >= visible:
                top = idx - visible + 1
            sys.stdout.write(CLEAR)
            sys.stdout.write(f"{BOLD}calls{RST}  {len(rows)} recent   click a row, then Enter\r\n")
            sys.stdout.write(f"{DIM}↑↓ / click  ·  Enter open  ·  r refresh  ·  q quit{RST}\r\n")
            sys.stdout.write(f"{BOLD} #  when             role     dir  status    dur   from → to  tools{RST}\r\n")
            sys.stdout.write(f"{DIM}{'─' * 88}{RST}\r\n")
            for i in range(top, min(top + visible, len(rows))):
                line = row_text(i + 1, rows[i])
                if i == idx:
                    sys.stdout.write(f"{REV} {line:<88}{RST}\r\n")
                else:
                    sys.stdout.write(f" {line}\r\n")
            sys.stdout.flush()

            key = _read_keys()
            if key in {"q", "Q", "\x03"}:
                return "quit", idx
            if key in {"r", "R"}:
                return "refresh", idx
            if key in {"\r", "\n"}:
                return "open", idx
            if key in {"up", "k", "K"}:
                idx = (idx - 1) % len(rows)
            elif key in {"down", "j", "J"}:
                idx = (idx + 1) % len(rows)
            elif key.startswith("mouse:"):
                # <0;x;yM  press, <0;x;ym release — select on press
                body = key[len("mouse:") :]
                if not body.endswith("M"):
                    continue
                try:
                    btn, _x, y = body[1:-1].split(";")
                    if btn != "0":
                        continue
                    row = int(y) - header_lines - 1 + top
                    if 0 <= row < len(rows):
                        idx = row
                except ValueError:
                    pass
    finally:
        sys.stdout.write(MOUSE_OFF + SHOW + RST)
        sys.stdout.flush()
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def wait_back() -> str:
    """After logs: Enter goes back, r refresh, q quit. Stays on this screen until then."""
    import termios
    import tty

    print(f"{BOLD}  Enter{RST} back to the list   {DIM}r refresh   q quit{RST}")
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            key = _read_keys()
            if key in {"q", "Q", "\x03"}:
                return "quit"
            if key in {"r", "R"}:
                return "refresh"
            if key in {"\r", "\n", "b", "B"}:
                return "back"
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def tools_of(d: dict) -> list[tuple[str, str, dict]]:
    from collections import defaultdict, deque

    turns = d.get("transcript") or []
    by_id: dict = {}
    by_name: dict = defaultdict(deque)
    for t in turns:
        for r in t.get("tool_results") or []:
            if r.get("tool_call_id"):
                by_id[r["tool_call_id"]] = r
            else:
                by_name[r.get("tool_name")].append(r)
    out = []
    for t in turns:
        for call in t.get("tool_calls") or []:
            name = call.get("tool_name") or "?"
            cid = call.get("tool_call_id")
            if cid and cid in by_id:
                res = by_id.pop(cid)
            elif by_name[name]:
                res = by_name[name].popleft()
            else:
                res = {}
            out.append((name, call.get("params_as_json") or call.get("params") or "{}", res))
    return out


def print_detail(cid: str, cached: dict | None = None) -> None:
    d = cached if cached is not None else get(f"{API}/{cid}")
    md = d.get("metadata") or {}
    ext, agent_n, direction = phone(d)
    start = when(
        md.get("start_time_unix_secs")
        or d.get("start_time_unix_secs")
        or md.get("start_time")
    )
    dur = md.get("call_duration_secs")
    status = d.get("status") or "?"
    print()
    print(f"{BOLD}{cid}{RST}")
    print(f"  {start}  {status}  {dur if dur is not None else '?'}s  {direction}")
    print(f"  {ext}  →  {agent_n}")
    print()

    tools = tools_of(d)
    if tools:
        print(f"{BOLD}  tool calls{RST}")
        for name, params, res in tools:
            err = res.get("is_error")
            lat = res.get("tool_latency_secs")
            tag = f"{RED}ERR{RST}" if err else f"{GRN}ok{RST}"
            lat_s = f"  {lat:.2f}s" if isinstance(lat, (int, float)) else ""
            print(f"  {CYN}{name}{RST}  {tag}{lat_s}")
            print(f"    {DIM}params{RST}  {params}")
            val = res.get("result_value") or res.get("result") or res.get("error") or ""
            if val:
                text = str(val)
                if len(text) > 500:
                    text = text[:500] + "…"
                print(f"    {DIM}result{RST}  {text}")
        print()
    else:
        print(f"  {DIM}(no tool calls){RST}")
        print()

    print(f"{BOLD}  transcript{RST}")
    turns = d.get("transcript") or []
    if not turns:
        print(f"  {DIM}(empty){RST}")
        print()
        return
    for t in turns:
        role = (t.get("role") or "?").lower()
        msg = (t.get("message") or t.get("text") or "").strip()
        if not msg:
            continue
        color = GRN if role == "agent" else (CYN if role == "user" else DIM)
        for line in msg.splitlines() or [msg]:
            print(f"  {color}{role:<6}{RST} {line}")
    print()


def fetch_rows() -> list[dict]:
    print(f"{DIM}  fetching last {PAGE} renter + listing calls…{RST}")
    sys.stdout.flush()
    return list_calls()


def main() -> None:
    direct = sys.argv[2] if len(sys.argv) > 2 else ""
    if direct:
        try:
            print_detail(direct)
        except RuntimeError as e:
            print(e, file=sys.stderr)
            raise SystemExit(1) from e
        return

    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("Run this in a real terminal (make calls) so the list stays live.", file=sys.stderr)
        raise SystemExit(1)

    rows: list[dict] = []
    idx = 0
    try:
        while True:
            if not rows:
                try:
                    rows = fetch_rows()
                except RuntimeError as e:
                    print(e, file=sys.stderr)
                    raise SystemExit(1) from e
                idx = 0
            action, idx = pick(rows, idx)
            if action == "quit":
                sys.stdout.write(CLEAR)
                return
            if action == "refresh":
                rows = []
                continue
            row = rows[idx]
            cid = row.get("conversation_id")
            sys.stdout.write(CLEAR)
            try:
                print_detail(cid, row.get("_detail"))
            except RuntimeError as e:
                print(f"  {e}")
            back = wait_back()
            if back == "quit":
                sys.stdout.write(CLEAR)
                return
            if back == "refresh":
                rows = []
    except KeyboardInterrupt:
        sys.stdout.write(MOUSE_OFF + SHOW + RST + "\n")
        return


if __name__ == "__main__":
    main()
PY
