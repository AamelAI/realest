#!/usr/bin/env python3
"""Build-day progress board. Completion comes from git log, not from editing files.

    make todo              # the board
    make todo MINE=D2      # just your lane
    make todo STEP=3       # just one step

Mark a task done by putting its id in a commit message:

    git commit -m "[1.4] outbound call places and rings"

Nobody edits TODO.md during the build, so there's nothing to merge-conflict on.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TODO = ROOT / "TODO.md"

R, Y, G, B, D, X = "\033[31m", "\033[33m", "\033[32m", "\033[34m", "\033[2m", "\033[0m"
LANE = {"D1": "\033[36m", "D2": "\033[35m", "D3": "\033[33m", "ALL": "\033[37m"}

STEP_RE = re.compile(r"^## (Step \d+[^\n·]*?)(?: ·.*)?$")
TASK_RE = re.compile(r"^- `([\d.]+)` \*\*(D\d|ALL)\*\* — (.+?)(?: · \*done when:\* (.+))?$")


def done_ids() -> dict[str, str]:
    """id -> "author · subject" for every task referenced in a commit."""
    try:
        log = subprocess.run(
            ["git", "log", "--format=%an\x1f%s%x1f%b\x1e"],
            cwd=ROOT, capture_output=True, text=True, check=True).stdout
    except subprocess.CalledProcessError:
        return {}
    out: dict[str, str] = {}
    for entry in log.split("\x1e"):
        if not entry.strip():
            continue
        author, subject, body = (entry.strip().split("\x1f") + ["", ""])[:3]
        for tid in re.findall(r"\[(\d+\.\d+)\]", subject + " " + body):
            out.setdefault(tid, f"{author} · {subject[:46]}")
    return out


def main() -> int:
    if not TODO.exists():
        print(f"{R}✗{X} TODO.md not found")
        return 1

    done = done_ids()
    mine = (os.environ.get("MINE") or "").upper().strip()
    only = (os.environ.get("STEP") or "").strip()

    step = ""
    steps: list[tuple[str, list[tuple]]] = []
    for line in TODO.read_text().splitlines():
        if m := STEP_RE.match(line):
            step = m.group(1).strip()
            steps.append((step, []))
        elif (m := TASK_RE.match(line.strip())) and steps:
            steps[-1][1].append(m.groups())

    total = sum(len(t) for _, t in steps)
    complete = sum(1 for _, ts in steps for t in ts if t[0] in done)

    print()
    for title, tasks in steps:
        if not tasks:
            continue
        if only and not title.startswith(f"Step {only}"):
            continue
        shown = [t for t in tasks if not mine or t[1] in (mine, "ALL")]
        if not shown:
            continue
        d = sum(1 for t in tasks if t[0] in done)
        bar = "█" * d + "░" * (len(tasks) - d)
        head = G if d == len(tasks) else (Y if d else D)
        print(f"{head}{title}{X}  {D}{bar} {d}/{len(tasks)}{X}")
        for tid, lane, text, _crit in shown:
            c = LANE.get(lane, "")
            if tid in done:
                print(f"  {G}✓{X} {D}{tid:>4}  {lane}  {text[:64]}{X}")
                print(f"       {D}{done[tid]}{X}")
            else:
                print(f"  {D}○{X} {tid:>4}  {c}{lane}{X}  {text[:64]}")
        print()

    print(f"{D}{'─' * 58}{X}")
    for lane in ("D1", "D2", "D3"):
        ts = [t for _, tasks in steps for t in tasks if t[1] == lane]
        d = sum(1 for t in ts if t[0] in done)
        nxt = next((t for t in ts if t[0] not in done), None)
        tail = f"next {nxt[0]} — {nxt[2][:40]}" if nxt else "all clear"
        print(f"  {LANE[lane]}{lane}{X} {d:>2}/{len(ts):<2} {D}{tail}{X}")
    print(f"\n  {complete}/{total} tasks · {D}mark done: git commit -m \"[1.4] …\"{X}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
