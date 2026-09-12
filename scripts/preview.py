#!/usr/bin/env python3
"""Generate a QA page for the seeded listings.

    make preview

Opens every listing side by side with a link to the real rentals.ca page so you
can spot-check the scrape. Fields are marked SCRAPED (verify these against the
source) or GENERATED (synthesized on purpose - parking, pets and amenities are
exactly what the listing doesn't reliably state and the agent finds out by phone).
"""
from __future__ import annotations

import html
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "listings.json"
OUT = ROOT / "data" / "preview.html"

CSS = """
*{box-sizing:border-box}
body{margin:0;background:#f5f5f8;color:#14182b;font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
header{position:sticky;top:0;z-index:5;background:#fff;border-bottom:1px solid #dcdcea;padding:14px 20px}
h1{margin:0 0 3px;font-size:17px;letter-spacing:-.01em}
.meta{color:#6e7391;font-size:12.5px}
.meta b{color:#14182b}
.filters{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.filters button{font:600 11px/1 ui-monospace,monospace;letter-spacing:.05em;text-transform:uppercase;
  padding:6px 10px;border:1px solid #dcdcea;background:#fff;color:#6e7391;border-radius:3px;cursor:pointer}
.filters button.on{background:#33408f;border-color:#33408f;color:#fff}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:14px;padding:18px 20px 60px}
.card{background:#fff;border:1px solid #dcdcea;border-radius:5px;overflow:hidden;display:flex;flex-direction:column}
.shots{display:flex;gap:1px;background:#dcdcea}
.shots img{width:50%;height:118px;object-fit:cover;display:block;background:#ededf6}
.body{padding:12px 14px;display:flex;flex-direction:column;gap:9px;flex:1}
.top{display:flex;justify-content:space-between;gap:10px;align-items:baseline}
.addr{font-weight:600;font-size:14.5px;letter-spacing:-.01em}
.rent{font:700 15px ui-monospace,monospace;white-space:nowrap;font-variant-numeric:tabular-nums}
.id{font:11px ui-monospace,monospace;color:#9a9fba}
table{width:100%;border-collapse:collapse;font-size:12.5px}
td{padding:3px 0;vertical-align:top}
td.k{color:#6e7391;width:96px;font:11px ui-monospace,monospace;letter-spacing:.03em;text-transform:uppercase;padding-top:5px}
td.v{color:#14182b}
tr.gen td.v{color:#8a8fa8;font-style:italic}
tr.gen td.k::after{content:" ·gen";color:#c08a3e;font-style:normal}
.link{margin-top:auto;padding:9px 14px;border-top:1px solid #ededf6;background:#fafafd;
  font:600 12px ui-monospace,monospace;display:flex;justify-content:space-between;align-items:center}
.link a{color:#33408f;text-decoration:none}
.link a:hover{text-decoration:underline}
.legend{background:#fff;border:1px solid #dcdcea;border-radius:4px;padding:10px 14px;margin:16px 20px 0;font-size:12.5px;color:#41465f}
.legend b{color:#c08a3e}
"""

JS = """
const btns=[...document.querySelectorAll('.filters button')];
btns.forEach(b=>b.onclick=()=>{
  btns.forEach(x=>x.classList.toggle('on',x===b));
  const a=b.dataset.area;
  document.querySelectorAll('.card').forEach(c=>{
    c.style.display=(a==='*'||c.dataset.area===a)?'':'none';
  });
});
"""


def row(key: str, val, generated: bool = False) -> str:
    if val in (None, "", [], 0):
        val = "—"
    if isinstance(val, list):
        val = ", ".join(val)
    if isinstance(val, bool):
        val = "yes" if val else "no"
    cls = ' class="gen"' if generated else ""
    return f'<tr{cls}><td class="k">{key}</td><td class="v">{html.escape(str(val))}</td></tr>'


def main() -> int:
    if not SRC.exists():
        print(f"✗ {SRC.relative_to(ROOT)} not found — run `make listings PHONE=... EMAIL=...` first")
        return 1

    listings = json.loads(SRC.read_text())
    areas = Counter(l["neighbourhood"] for l in listings)
    photos = sum(len(l.get("photos", [])) for l in listings)
    contact = f'{listings[0]["agent_phone"]} · {listings[0]["agent_email"]}'

    filters = ['<button class="on" data-area="*">all ' + str(len(listings)) + "</button>"]
    filters += [f'<button data-area="{html.escape(a)}">{html.escape(a)} {n}</button>'
                for a, n in areas.most_common()]

    cards = []
    for l in listings:
        shots = "".join(
            f'<img src="{html.escape(p)}" loading="lazy" alt="">' for p in l.get("photos", [])[:2]
        ) or '<img alt="" style="width:100%">'
        rows = "".join([
            row("beds / baths", f'{l["beds"]} bed · {l["baths"]} bath'),
            row("sqft", l.get("sqft")),
            row("type", l.get("property_type")),
            row("area", l.get("neighbourhood"), True),
            row("transit", l.get("transit_note"), True),
            row("parking", l.get("parking_included"), True),
            row("pets", l.get("pets"), True),
            row("amenities", l.get("amenities"), True),
            row("agent", l.get("agent_name"), True),
            row("phone", l.get("agent_phone"), True),
            row("email", l.get("agent_email"), True),
        ])
        cards.append(f"""<div class="card" data-area="{html.escape(l['neighbourhood'])}">
<div class="shots">{shots}</div>
<div class="body">
  <div class="top"><span class="addr">{html.escape(l['address'])}</span><span class="rent">${l['rent']:,}</span></div>
  <table>{rows}</table>
</div>
<div class="link"><span class="id">{l['listing_id']}</span>
<a href="{html.escape(l['source_url'])}" target="_blank" rel="noopener">verify on rentals.ca →</a></div>
</div>""")

    OUT.write_text(f"""<!doctype html><html><head><meta charset="utf-8">
<title>Realest — listing QA</title><style>{CSS}</style></head><body>
<header>
  <h1>Listing QA — {len(listings)} Toronto rentals</h1>
  <div class="meta"><b>{photos}</b> photos · rent
    <b>${min(l['rent'] for l in listings):,}–${max(l['rent'] for l in listings):,}</b> ·
    <b>{len(areas)}</b> areas · contacts <b>{html.escape(contact)}</b> ·
    source <b>rentals.ca</b>, scraped 2026-09-12</div>
  <div class="filters">{''.join(filters)}</div>
</header>
<div class="legend">Plain rows are <b style="color:#14182b">scraped</b> — check these against the source page.
Italic rows marked <b>·gen</b> are <b>generated on purpose</b>: parking, pets, amenities, area and transit are
exactly the facts a listing doesn't state reliably, and the whole point is that the agent finds them out by phone.
Contacts are ours by design — realtor details were never collected.</div>
<div class="grid">{''.join(cards)}</div>
<script>{JS}</script></body></html>""")

    print(f"✓ {OUT.relative_to(ROOT)}  ({len(listings)} listings, {photos} photos)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
