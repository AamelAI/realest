"""DEMO_AGENT_PHONE is a list. start_calls zips it onto the shortlist."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "server"))

import calls  # noqa: E402


def test_as_e164_nanp_missing_country_code() -> None:
    assert calls.as_e164("4165550101") == "+14165550101"
    assert calls.as_e164("+4165550101") == "+14165550101"
    assert calls.as_e164("1-416-555-0101") == "+14165550101"


def test_demo_phones_csv_and_json(monkeypatch) -> None:
    monkeypatch.setenv("DEMO_AGENT_PHONE", "4375550101, +1-437-555-0102")
    got = calls.demo_phones()
    assert len(got) == 2
    assert all(p.startswith("+1") for p in got)

    monkeypatch.setenv("DEMO_AGENT_PHONE", '["4375550103", "14375550104"]')
    got = calls.demo_phones()
    assert len(got) == 2


def test_assign_demo_targets_stops_when_phones_run_out(monkeypatch) -> None:
    monkeypatch.setenv("DEMO_AGENT_PHONE", "4375550101,4375550102")
    calls._listing_dest.clear()
    ids = calls.assign_demo_targets("s1", ["L001", "L002", "L003", "L004"])
    assert ids == ["L001", "L002"]
    assert calls._listing_dest[("s1", "L001")].endswith("4375550101")
    assert calls._listing_dest[("s1", "L002")].endswith("4375550102")
    assert ("s1", "L003") not in calls._listing_dest


def test_assign_demo_targets_empty_env(monkeypatch) -> None:
    monkeypatch.setenv("DEMO_AGENT_PHONE", "")
    calls._listing_dest.clear()
    assert calls.assign_demo_targets("s2", ["L001"]) == []
