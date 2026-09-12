"""The three fixtures from .claude/skills/ranking/.

If fixtures 2 and 3 produce the demo's reshuffle, the demo works.
    uv run pytest tests/test_rank.py -q
    uv run python tests/test_rank.py       # also runs standalone

Wrapped in a pytest function (mechanical only, no logic changed) - a bare
module-level `raise SystemExit` aborts pytest's collection for the whole
suite, not just this file.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "server"))

from listings import rank  # noqa: E402
from schemas import CallOutcome, CallStatus, Listing, Preferences  # noqa: E402

DEMO = [
    Listing(listing_id="L001", address="155 Strachan Ave", rent=3180, beds=2, baths=1,
            neighbourhood="King West", parking_included=True, pets="ask",
            transit_note="4 min to King streetcar", agent_name="Mark"),
    Listing(listing_id="L002", address="850 Wellington St W", rent=3250, beds=2, baths=2,
            neighbourhood="King West", parking_included=True, pets="ask",
            transit_note="8 min to King streetcar", agent_name="Dana"),
    Listing(listing_id="L003", address="700 Bathurst St", rent=3390, beds=2, baths=1,
            neighbourhood="King West", parking_included=False, pets="yes",
            transit_note="11 min to King streetcar", agent_name="Sam"),
    Listing(listing_id="L004", address="80 Lynn Williams St", rent=3295, beds=2, baths=2,
            neighbourhood="Liberty Village", parking_included=True, pets="ask",
            transit_note="3 min to Exhibition GO", agent_name="Priya"),
]

PREFS = Preferences(beds=2, areas=["King West", "Liberty Village"], max_rent=3400,
                    parking=True, pets="dog", priority_order=["parking", "price"])


def order(states) -> list[str]:
    return [s.listing_id for s in states]


def test_ranking_fixtures() -> None:
    ok = True

    def check(label: str, cond: bool, detail: str = "") -> None:
        nonlocal ok
        print(("  \033[32mPASS\033[0m " if cond else "  \033[31mFAIL\033[0m ") + label + (f"  {detail}" if detail else ""))
        ok = ok and cond

    print("\nfixture 1 - no outcomes, pure preference fit")
    r1 = rank(DEMO, PREFS, {})
    print("  order:", order(r1))
    check("all four present", len(r1) == 4)
    check("ranks are 1..4", [s.rank for s in r1] == [1, 2, 3, 4])
    check("no-parking Bathurst is last", order(r1)[-1] == "L003", "parking was priority #1")
    check("nothing marked dead", all(s.status is CallStatus.PENDING for s in r1))

    print("\nfixture 2 - top pick returns available:False, it sinks")
    top = order(r1)[0]
    r2 = rank(DEMO, PREFS, {top: CallOutcome(available=False, source="Mark, 1:42pm")}, previous=r1)
    print("  order:", order(r2))
    check(f"{top} sank to the bottom", order(r2)[-1] == top)
    check("it reads as dead", r2[-1].status is CallStatus.DEAD)
    check("everything else shifted up", order(r2)[0] != top)

    print("\nfixture 3 - add-ons push a listing over budget, it demotes below a cheaper verified unit")
    outs = {
        "L001": CallOutcome(available=False, source="Mark, 1:42pm"),
        "L002": CallOutcome(available=True, addons=["parking $180", "locker $40"], source="Dana, 1:41pm"),
        "L004": CallOutcome(available=True, viewing_slot="Saturday 2:00pm",
                            pets_allowed="cats only", source="Priya, 1:43pm"),
    }
    r3 = rank(DEMO, PREFS, outs, previous=r2)
    print("  order:", order(r3))
    pos = {s.listing_id: i for i, s in enumerate(r3)}
    check("Lynn Williams (verified, in budget) is #1", order(r3)[0] == "L004")
    check("Wellington demoted below it", pos["L002"] > pos["L004"], "$3,470 real vs $3,400 cap")
    check("Strachan still bottom", order(r3)[-1] == "L001")
    check("cats-only listing was NOT removed", "L004" in pos, "rule 5: annotate, never remove")

    print("\nfixture 4 - ties are stable across identical re-ranks")
    a, b = rank(DEMO, PREFS, outs, previous=r3), rank(DEMO, PREFS, outs, previous=r3)
    check("two identical ranks agree", order(a) == order(b), " ".join(order(a)))

    print("\nfixture 5 - reprioritising transit over parking flips the order, removes nothing")
    p2 = PREFS.model_copy(update={"priority_order": ["transit", "parking", "price"]})
    r5 = rank(DEMO, p2, {})
    print("  order:", order(r5))
    check("all four still present", len(r5) == 4, "a weight change is not a filter change")
    check("order actually changed", order(r5) != order(r1), f"{order(r1)} -> {order(r5)}")

    assert ok, "one or more ranking fixtures failed - see output above"


if __name__ == "__main__":
    test_ranking_fixtures()
    print("\n\033[32mall fixtures pass\033[0m\n")
