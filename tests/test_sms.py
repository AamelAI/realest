"""SMS behaviour: the link-during-the-call trick, booking confirmations,
validation, retries, and duplicate-prevention. No Twilio credentials needed -
`calls._twilio()` is monkeypatched with a fake client that records sends.

    uv run pytest tests/test_sms.py -q
    python3 tests/test_sms.py           # also runs standalone
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "server"))

import calls  # noqa: E402
import state as store  # noqa: E402

_failures: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    print(("  \033[32mPASS\033[0m " if cond else "  \033[31mFAIL\033[0m ") + label + (f"  {detail}" if detail else ""))
    if not cond:
        _failures.append(label)


class FakeMessages:
    def __init__(self, fail_times: int = 0):
        self.sent: list[dict] = []
        self.fail_times = fail_times
        self.calls = 0

    def create(self, body: str, from_: str, to: str):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("simulated Twilio outage")
        self.sent.append({"body": body, "from_": from_, "to": to})


class FakeClient:
    def __init__(self, fail_times: int = 0):
        self.messages = FakeMessages(fail_times)


def use_fake_twilio(fail_times: int = 0) -> FakeClient:
    fake = FakeClient(fail_times)
    calls._twilio = lambda: fake  # type: ignore[assignment]
    return fake


def reset_sms_module_state() -> None:
    """These are process-lifetime dedupe/tracking dicts - clear between tests
    so one test's session ids can't leak into the next."""
    calls._ended.clear()
    calls._link_sms_started.clear()
    calls._recent_sms.clear()


async def new_session(sid: str, phone: str = "+14165551234"):
    await store.mutate(sid, lambda s: setattr(s, "caller_phone", phone))


async def _run() -> None:
    # ── basic send + validation ──────────────────────────────────────────
    print("\nsms() - basic send")
    reset_sms_module_state()
    fake = use_fake_twilio()
    await new_session("s-basic")
    sent = await calls.sms("s-basic", "hello")
    check("returns True", sent is True)
    check("exactly one message sent", len(fake.messages.sent) == 1)
    check("went to the session's caller_phone", fake.messages.sent[0]["to"] == "+14165551234")

    print("\nsms() - invalid/missing destination never calls Twilio")
    reset_sms_module_state()
    fake = use_fake_twilio()
    ok1 = await calls.sms("s-no-session-at-all", "hello")
    ok2 = await calls.sms("s-basic", "hello", to="not-a-phone-number")
    check("no session, no caller_phone -> False, no crash", ok1 is False)
    check("garbage phone -> False, no crash", ok2 is False)
    check("Twilio never actually called", fake.messages.calls == 0)

    print("\nsms() - Twilio not configured returns False, doesn't crash")
    calls._twilio = lambda: None
    reset_sms_module_state()
    await new_session("s-no-twilio")
    r = await calls.sms("s-no-twilio", "hello")
    check("returns False", r is False)

    # ── retry ─────────────────────────────────────────────────────────────
    print("\nsms() - retries once on a transient failure, then succeeds")
    reset_sms_module_state()
    fake = use_fake_twilio(fail_times=1)
    await new_session("s-retry")
    r = await calls.sms("s-retry", "retry me")
    check("eventually succeeds", r is True)
    check("took exactly two attempts", fake.messages.calls == 2)
    check("exactly one message actually delivered", len(fake.messages.sent) == 1)

    print("\nsms() - gives up after two failures, never raises")
    reset_sms_module_state()
    fake = use_fake_twilio(fail_times=99)
    await new_session("s-always-fails")
    r = await calls.sms("s-always-fails", "doomed")
    check("returns False, does not raise", r is False)
    check("stopped after two attempts", fake.messages.calls == 2)

    # ── duplicate prevention ─────────────────────────────────────────────
    print("\nsms() - identical (to, body) within the window is suppressed")
    reset_sms_module_state()
    fake = use_fake_twilio()
    await new_session("s-dup")
    r1 = await calls.sms("s-dup", "same message")
    r2 = await calls.sms("s-dup", "same message")
    check("both calls report success", r1 is True and r2 is True)
    check("Twilio only actually invoked once", fake.messages.calls == 1)

    print("\nsms() - a DIFFERENT body to the same number is NOT suppressed")
    r3 = await calls.sms("s-dup", "a different message")
    check("distinct body still sends", fake.messages.calls == 2)

    # ── the 5s link trick ────────────────────────────────────────────────
    print("\nsms_if_call_alive() - sends when the call is still going")
    reset_sms_module_state()
    fake = use_fake_twilio()
    calls.SMS_LINK_DELAY_S = 0  # don't actually wait 5s in a test
    await new_session("s-alive")
    await calls.sms_if_call_alive("s-alive", "https://realest.example/s/s-alive")
    check("link sms went out", any("shortlist" in m["body"] for m in fake.messages.sent))

    print("\nsms_if_call_alive() - cancelled if the call already ended")
    reset_sms_module_state()
    fake = use_fake_twilio()
    calls.SMS_LINK_DELAY_S = 0.05
    await new_session("s-ended")
    calls.mark_call_ended("s-ended")
    await calls.sms_if_call_alive("s-ended", "https://realest.example/s/s-ended")
    check("no message sent", fake.messages.calls == 0)

    print("\nsms_if_call_alive() - calling it twice for one session only schedules once")
    reset_sms_module_state()
    fake = use_fake_twilio()
    calls.SMS_LINK_DELAY_S = 0
    await new_session("s-twice")
    await asyncio.gather(
        calls.sms_if_call_alive("s-twice", "https://realest.example/s/s-twice"),
        calls.sms_if_call_alive("s-twice", "https://realest.example/s/s-twice"),
    )
    check("only one link sms actually sent", fake.messages.calls == 1)

    # ── booking confirmation reuses the same hardened sms() ─────────────
    print("\nbooking confirmation: calling agent_book twice does not double-text")
    reset_sms_module_state()
    fake = use_fake_twilio()
    import main
    sid = "s-booking"
    await main.agent_preferences({"session_id": sid, "beds": 2, "max_rent": 4000})
    s = store.get(sid)
    await new_session(sid)  # (re)attach a caller_phone after preferences overwrote nothing here
    lid = s.listings[0].listing_id
    await main.agent_book({"session_id": sid, "listing_id": lid, "slot": "Saturday 2pm"})
    await main.agent_book({"session_id": sid, "listing_id": lid, "slot": "Saturday 2pm"})
    check("only one confirmation actually sent", fake.messages.calls == 1,
          f"calls={fake.messages.calls}")

    calls.SMS_LINK_DELAY_S = 5  # restore the real constant for anything after this module


def test_sms_behavior() -> None:
    _failures.clear()
    asyncio.run(_run())
    assert not _failures, f"{len(_failures)} check(s) failed: {_failures}"


if __name__ == "__main__":
    test_sms_behavior()
    print("\n\033[32mall SMS checks pass\033[0m\n")
