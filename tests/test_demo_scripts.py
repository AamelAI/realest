"""Keeps server/transport.py's SCRIPTS in sync with docs/DEMO.md.

The four canonical demo listings and their reveals are documented in
docs/DEMO.md - this test hardcodes that same set and fails loudly the moment
they drift apart again (as they did: SCRIPTS was still keyed to an older
generation of demo ids, L013/L054/L061/L063, while docs/DEMO.md had already
moved on to L092/L095/L086/L100 - meaning a rehearsal against the current
curated listings silently fell through to the generic transcript for all
four, and the reorder never happened).

    uv run pytest tests/test_demo_scripts.py -q
    python3 tests/test_demo_scripts.py           # also runs standalone
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "server"))

import transport  # noqa: E402

# The four ids and roles documented in docs/DEMO.md's "The four, and what
# each call reveals" table. Update both together, always.
CANONICAL_DEMO_IDS = {
    "L092": "dead",         # "leased Tuesday" - opens #1, ends #4
    "L095": "price_wrong",  # $180 parking add-on -> $3,470, over the $3,400 cap
    "L086": "booked",       # Saturday 2pm, cats only vs. the caller's dog
    "L100": "no_answer",    # nobody picks up -> email drafted
}


def test_scripts_cover_exactly_the_canonical_demo_ids() -> None:
    assert set(transport.SCRIPTS) == set(CANONICAL_DEMO_IDS), (
        "server/transport.py's SCRIPTS no longer matches docs/DEMO.md's four "
        "canonical demo listings - the stub will fall through to the generic "
        "transcript for any id that's missing, and the scripted reveals "
        "(dead / price-wrong / pet-conflict / no-answer) won't fire."
    )


def test_l092_reads_as_dead() -> None:
    script = transport.SCRIPTS["L092"]
    assert script is not None
    assert "leased" in script.lower() or "gone" in script.lower()


def test_l095_reveals_the_180_parking_addon() -> None:
    script = transport.SCRIPTS["L095"]
    assert script is not None
    # Spoken as words, not digits - "a hundred and eighty" - since it's meant
    # to read like an actual phone call. extract_outcome() still parses this
    # into a real number; see tests/test_extraction_live.py.
    assert "hundred and eighty" in script.lower() or "180" in script
    assert "parking" in script.lower()


def test_l086_books_saturday_with_a_pet_conflict() -> None:
    script = transport.SCRIPTS["L086"]
    assert script is not None
    assert "saturday" in script.lower()
    assert "cats only" in script.lower() or "cat" in script.lower()


def test_l100_is_no_answer() -> None:
    assert transport.SCRIPTS["L100"] is None


if __name__ == "__main__":
    test_scripts_cover_exactly_the_canonical_demo_ids()
    test_l092_reads_as_dead()
    test_l095_reveals_the_180_parking_addon()
    test_l086_books_saturday_with_a_pet_conflict()
    test_l100_is_no_answer()
    print("\n\033[32mdemo script mapping checks pass\033[0m\n")
