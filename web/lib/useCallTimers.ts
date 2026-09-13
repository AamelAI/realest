"use client";

import { useEffect, useState } from "react";
import type { Card } from "./types";

/**
 * How long each row has been on the phone, in seconds.
 *
 * Three rows ticking in unison is the one frame that proves a human couldn't
 * have done this, so the numbers must agree. Every row that flips to `calling`
 * in the same poll gets the *same* start stamp, and one interval drives them
 * all — no per-row timers drifting a second apart on camera.
 *
 * The clock is the browser's: SessionState carries no call-start time and the
 * page is not allowed to make the server grow a field for a decoration. A page
 * opened mid-call therefore counts from when it opened, which is honest about
 * what this device knows and never renders a wrong-looking large number.
 */
export function useCallTimers(listings: Card[], paused = false): Record<string, number> {
  const [starts, setStarts] = useState<Record<string, number>>({});
  // A call that has ended keeps its final length. Without this the panel reads
  // "0:00" the moment the last line hangs up.
  const [frozen, setFrozen] = useState<Record<string, number>>({});
  const [now, setNow] = useState(0);

  // Sorted id list as a string: a stable dependency that only changes when the
  // *set* of rows on the phone changes, not on every poll tick.
  const onCall = listings
    .filter((c) => c.status === "calling")
    .map((c) => c.listing_id)
    .sort()
    .join(",");

  useEffect(() => {
    const ids = onCall ? onCall.split(",") : [];
    const stamp = Date.now();
    setStarts((prev) => {
      // Anything that was on the phone and no longer is: freeze its length.
      const ended = Object.keys(prev).filter((id) => !ids.includes(id));
      if (ended.length) {
        setFrozen((f) => {
          const next = { ...f };
          for (const id of ended) next[id] = Math.max(0, Math.floor((stamp - prev[id]) / 1000));
          return next;
        });
      }
      const next: Record<string, number> = {};
      for (const id of ids) next[id] = prev[id] ?? stamp;
      const same =
        ids.length === Object.keys(prev).length && ids.every((id) => prev[id] === next[id]);
      return same ? prev : next;
    });
  }, [onCall]);

  // One interval for the whole board, and only while someone is on the phone.
  // Paused while the connection is stale: we can't see the call, so the clock
  // stops rather than ticking on as if we could. On resume it jumps to the
  // real elapsed time, which is the honest number.
  useEffect(() => {
    if (!onCall || paused) return;
    setNow(Date.now());
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [onCall, paused]);

  const elapsed: Record<string, number> = { ...frozen };
  for (const [id, start] of Object.entries(starts)) {
    elapsed[id] = Math.max(0, Math.floor((now - start) / 1000));
  }
  return elapsed;
}

/** 0:07, 1:42 — a call length, not a duration string. */
export function clock(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s < 10 ? "0" : ""}${s}`;
}
