#!/usr/bin/env python3
"""Turn a raw rentals.ca scrape into validated Listing rows.

    uv run python scripts/scrape_rentals.py --phone +14165551234 --email you@example.com
    make listings PHONE=+14165551234 EMAIL=you@example.com

WHY THE FETCHING ISN'T HERE
---------------------------
rentals.ca is a Cloudflare-fronted Vue app; listings are server-rendered into
the DOM with no JSON API to hit. `requests` + BeautifulSoup gets you a
challenge page. The rows in data/raw/rentals_ca.json were collected by driving
a real browser and reading the DOM:

    for (const r of document.querySelectorAll('[class*="listing-card"]')) {
      if (!/listing-card($|\\s)/.test(r.className)) continue;
      const q = s => r.querySelector('.listing-card__' + s)?.innerText.trim();
      rows.push({
        url:      r.querySelector('a[href*="/toronto/"]').href.split('#')[0],
        address:  q('title'),
        price:    q('price'),
        type:     q('type'),
        features: q('main-features'),     // "1 - 3 BED 1 - 2 BATH 496 - 982 FT²"
        photos:   [...r.querySelectorAll('img')].map(i => i.src)
                    .filter(s => /images\\.rentals\\.ca/.test(s)),
      });
    }

Run once per search URL, paginate with ?p=N, accumulate in localStorage so the
set survives navigation. Neighbourhood URLs (/toronto/king-west,
/toronto/liberty-village, …) give far better geographic spread than paging the
city-wide search.

CONTACT DETAILS ARE DELIBERATELY NOT SCRAPED
--------------------------------------------
Every row gets our own demo phone and email assigned below. Harvesting real
agents' contact details would put personal data in a repo that goes public at
submission, and it would be overwritten here anyway.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))

from schemas import Listing  # noqa: E402

E164 = re.compile(r"^\+[1-9]\d{7,14}$")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Address fragment -> (neighbourhood, transit note). Toronto-specific and hand-built;
# the ranker needs a neighbourhood to filter on and the card looks thin without transit.
AREAS: list[tuple[tuple[str, ...], str, str]] = [
    (("ordnance", "strachan", "niagara st", "east liberty", "hanna", "pirandello"),
     "Liberty Village", "6 min to Exhibition GO"),
    # NB: "bathurst st" is deliberately NOT here. It matched before North York's
    # rule and labelled every Bathurst address in the city King West - including
    # 6020 Bathurst, which is at Steeles. It polluted the demo shortlist.
    (("adelaide", "spadina ave", "wellington", "king st", "portland"),
     "King West", "4 min to King streetcar"),
    (("queens quay", "mill street", "cherry", "eastern ave", "lower jarvis"),
     "Waterfront", "9 min to Union Station"),
    (("yorkville", "scollard", "cumberland", "prince arthur", "bloor st", "bay street", "st. thomas", "charles st"),
     "Yorkville", "3 min to Bay Station"),
    (("st george", "st. george", "spadina road", "walmer", "huron", "lowther", "brunswick",
      "albany", "barton", "vermont", "dupont", "davenport", "avenue road", "hillsboro", "marlborough"),
     "The Annex", "5 min to Spadina Station"),
    (("broadview", "gowan", "cosburn", "carlaw", "sandford", "queen street east", "leslie",
      "east end", "greenwood", "jones ave"),
     "Leslieville", "7 min to Queen streetcar"),
    (("broadway", "redpath", "erskine", "balliol", "davisville", "eglinton", "roehampton",
      "lillian", "soudan", "midtown", "rosehill", "jackes", "maitland", "gloucester", "selby"),
     "Midtown", "6 min to Eglinton Station"),
    (("dufferin", "lansdowne", "college st", "perth", "assembly", "dundas street west",
      "regal", "croham", "fairbank", "tyndall", "phipps"),
     "West End", "8 min to Dufferin Station"),
    (("bayview", "york mills", "harrison garden", "parkway forest", "sheppard", "steeles",
      "bathurst street", "tretti", "fisherville", "upper canada", "david salomon", "st. dennis",
      "st dennis", "roanoke", "eastdale", "clayland", "vena", "rexdale", "earlington", "kingston road",
      "pacific ave", "victoria street", "jarvis", "sherbourne", "ontario street", "bay st"),
     "North York", "11 min to Sheppard-Yonge"),
]
DEFAULT_AREA = ("Toronto", "close to transit")

AMENITY_POOL = [
    "gym", "roof deck", "concierge", "locker", "in-suite laundry", "balcony",
    "pet spa", "party room", "bike storage", "visitor parking",
]
AGENT_NAMES = [
    "Mark", "Dana", "Priya", "Tomasz", "Aisha", "Ben", "Sofia", "Raj",
    "Chloe", "Marco", "Nadia", "Simon",
]


def area_for(address: str) -> tuple[str, str]:
    low = address.lower()
    for keys, name, transit in AREAS:
        if any(k in low for k in keys):
            return name, transit
    return DEFAULT_AREA


def low_int(raw: str) -> int | None:
    """'$1849 - $2249' -> 1849.  We rank on the entry price, not the ceiling."""
    nums = re.findall(r"[\d,]+", raw.replace("$", ""))
    return int(nums[0].replace(",", "")) if nums else None


def low_num(raw: str, unit: str) -> float | None:
    """'1 - 3 BED 1 - 2 BATH' + 'BED' -> 1.0"""
    m = re.search(r"([\d.]+)(?:\s*[-–]\s*[\d.]+)?\s*" + unit, raw, re.I)
    return float(m.group(1)) if m else None


def build(rows: list[list], phone: str, email: str, seed: int = 7) -> list[Listing]:
    rng = random.Random(seed)          # deterministic: same data on every machine
    out: list[Listing] = []
    for i, (slug, address, price, ptype, features, photos) in enumerate(rows):
        rent = low_int(price)
        beds = low_num(features, "BED")
        baths = low_num(features, "BATH")
        if rent is None or beds is None:
            continue
        area, transit = area_for(address)
        out.append(Listing(
            listing_id=f"L{i + 1:03d}",
            address=address,
            rent=rent,
            beds=int(beds) if beds >= 1 else 0,
            baths=int(baths) if baths else 1,
            # Not in the feed - the agent finds these out BY PHONE. That's the product.
            parking_included=rng.random() < 0.45,
            pets=rng.choice([None, "ask", "cats only", "pets OK"]),
            amenities=rng.sample(AMENITY_POOL, rng.randint(1, 3)),
            transit_note=transit,
            neighbourhood=area,
            property_type=ptype,
            sqft=int(low_num(features, "FT²") or 0) or None,
            photos=photos,
            photo_url=photos[0] if photos else "",
            source_url=slug,
            agent_name=rng.choice(AGENT_NAMES),
            agent_phone=phone,
            agent_email=email,
        ))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--phone", required=True, help="demo phone, E.164, e.g. +14165551234")
    ap.add_argument("--email", required=True, help="demo email")
    ap.add_argument("--raw", default="data/raw/rentals_ca.json")
    ap.add_argument("--out", default="data/listings.json")
    args = ap.parse_args()

    if not E164.match(args.phone):
        print(f"✗ --phone must be E.164 (e.g. +14165551234), got {args.phone!r}")
        return 1
    if not EMAIL.match(args.email):
        print(f"✗ --email doesn't look like an email: {args.email!r}")
        return 1

    raw = json.loads((ROOT / args.raw).read_text())
    url_pre, photo_pre = raw["_url_prefix"], raw["_photo_prefix"]

    rows = []
    for slug, address, price, ptype, features, photos in raw["listings"]:
        rows.append([
            slug, address, price, ptype, features,
            [p if p.startswith("http") else photo_pre + p for p in photos],
        ])

    listings = build(rows, args.phone, args.email)
    for l in listings:
        l.source_url = url_pre + l.source_url

    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([l.model_dump(mode="json") for l in listings], indent=2) + "\n")

    from collections import Counter
    areas = Counter(l.neighbourhood for l in listings)
    print(f"✓ {len(listings)} listings → {out.relative_to(ROOT)}")
    print(f"  contacts   {args.phone} · {args.email}  (all rows)")
    print(f"  photos     {sum(len(l.photos) for l in listings)} across {len(listings)} listings")
    print("  areas      " + ", ".join(f"{a} {n}" for a, n in areas.most_common()))
    print("\n  next: make seed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
