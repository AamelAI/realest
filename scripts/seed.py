#!/usr/bin/env python3
"""Validate a listings JSON file and write the canonical data/listings.json.

    uv run python scripts/seed.py                       # data/listings.json in place
    uv run python scripts/seed.py --in raw.json         # validate raw.json, write data/listings.json
    uv run python scripts/seed.py --in raw.json --check # validate only, write nothing

Fails loudly. A bad row at 3am is cheap; a bad row at 13:00 costs the afternoon.
This is dev tooling, not product code - it carries no TODO(hackathon) marker.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))

from pydantic import ValidationError  # noqa: E402

from schemas import Listing  # noqa: E402

E164 = re.compile(r"^\+[1-9]\d{7,14}$")
PLACEHOLDER = re.compile(r"REPLACE|XXX|0000000|555555", re.I)
RENT_RANGE = (800, 12_000)
MIN_ROWS = 20

RESET, RED, YEL, GRN, DIM = "\033[0m", "\033[31m", "\033[33m", "\033[32m", "\033[2m"


def fail(row: int, field: str, msg: str) -> str:
    return f"{RED}✗{RESET} row {row:>3} {DIM}·{RESET} {field:<16} {msg}"


def warn(row: int, field: str, msg: str) -> str:
    return f"{YEL}!{RESET} row {row:>3} {DIM}·{RESET} {field:<16} {msg}"


def check(raw: list[dict]) -> tuple[list[Listing], list[str], list[str]]:
    listings: list[Listing] = []
    errors: list[str] = []
    warnings: list[str] = []
    seen_ids: set[str] = set()

    for i, row in enumerate(raw):
        try:
            listing = Listing(**row)
        except ValidationError as exc:
            for err in exc.errors():
                field = ".".join(str(p) for p in err["loc"]) or "?"
                errors.append(fail(i, field, err["msg"]))
            continue

        if listing.listing_id in seen_ids:
            errors.append(fail(i, "listing_id", f"duplicate: {listing.listing_id}"))
        seen_ids.add(listing.listing_id)

        # Every contact must be a teammate's real number. We never cold-call strangers.
        if not E164.match(listing.agent_phone):
            errors.append(fail(i, "agent_phone", f"not E.164: {listing.agent_phone!r}"))
        elif PLACEHOLDER.search(listing.agent_phone):
            errors.append(fail(i, "agent_phone", f"still a placeholder: {listing.agent_phone!r}"))

        if not listing.photo_url.startswith(("http://", "https://")):
            errors.append(fail(i, "photo_url", "missing or not a URL - the cards need images"))

        lo, hi = RENT_RANGE
        if not lo <= listing.rent <= hi:
            errors.append(fail(i, "rent", f"{listing.rent} outside {lo}-{hi}, typo?"))

        if not listing.transit_note:
            warnings.append(warn(i, "transit_note", "empty - the card will look thin"))
        if not listing.agent_name:
            warnings.append(warn(i, "agent_name", "empty - provenance line needs a name"))

        listings.append(listing)

    return listings, errors, warnings


def summarize(listings: list[Listing]) -> None:
    rents = sorted(l.rent for l in listings)
    beds = Counter(l.beds for l in listings)
    phones = Counter(l.agent_phone for l in listings)

    print(f"\n{GRN}✓{RESET} {len(listings)} listings")
    print(f"  rent     ${rents[0]:,} – ${rents[-1]:,}  (median ${rents[len(rents)//2]:,})")
    print("  beds     " + "  ".join(f"{b}br×{n}" for b, n in sorted(beds.items())))
    print(f"  parking  {sum(l.parking_included for l in listings)}/{len(listings)} included")
    print(f"  phones   {len(phones)} distinct teammate numbers")

    if len(listings) < MIN_ROWS:
        print(f"\n{YEL}!{RESET} only {len(listings)} rows - aim for ~50 so the shortlist "
              f"has somewhere to move when priorities change")


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate listings and write data/listings.json")
    ap.add_argument("--in", dest="src", default="data/listings.json")
    ap.add_argument("--out", dest="dst", default="data/listings.json")
    ap.add_argument("--check", action="store_true", help="validate only, write nothing")
    args = ap.parse_args()

    src = ROOT / args.src
    if not src.exists():
        print(f"{RED}✗{RESET} {src} not found. "
              f"Start from data/listings.sample.json and expand it.")
        return 1

    try:
        raw = json.loads(src.read_text())
    except json.JSONDecodeError as exc:
        print(f"{RED}✗{RESET} {src.name} is not valid JSON: {exc}")
        return 1

    if not isinstance(raw, list):
        print(f"{RED}✗{RESET} expected a JSON array of listings, got {type(raw).__name__}")
        return 1

    listings, errors, warnings = check(raw)

    for line in warnings:
        print(line)
    for line in errors:
        print(line)

    if errors:
        print(f"\n{RED}✗ {len(errors)} error(s). Nothing written.{RESET}")
        return 1

    summarize(listings)

    if args.check:
        print(f"\n{DIM}--check: nothing written{RESET}")
        return 0

    dst = ROOT / args.dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps([l.model_dump(mode="json") for l in listings], indent=2) + "\n")
    print(f"\n{GRN}✓{RESET} wrote {dst.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
