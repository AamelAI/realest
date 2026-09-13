"""The FastAPI fallback admin page embeds web/app/admin/admin.css verbatim.

Two copies of one stylesheet drift the moment someone edits only one. This
fails loudly when they do, the same way test_demo_scripts.py keeps the stub
transport in step with docs/DEMO.md.

    uv run pytest tests/test_admin_static.py -q
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BEGIN, END = "/* BEGIN admin.css */", "/* END admin.css */"


def test_static_admin_embeds_the_shared_stylesheet() -> None:
    css = (ROOT / "web" / "app" / "admin" / "admin.css").read_text().strip()
    html = (ROOT / "server" / "static" / "admin.html").read_text()
    embedded = html[html.index(BEGIN) + len(BEGIN):html.index(END)].strip()
    assert embedded == css, (
        "server/static/admin.html no longer matches web/app/admin/admin.css. "
        "Paste the stylesheet between the BEGIN/END admin.css markers."
    )
