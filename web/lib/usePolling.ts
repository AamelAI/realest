"use client";

import { useEffect, useRef, useState } from "react";
import { SessionState, DEFAULT_STATE } from "./types";

/**
 * Poll, don't socket. A 3rd-place winner shipped exactly this at 2000ms.
 * Websockets can drop mid-take; polling can't.
 *
 * Four things here matter:
 *   - cache: "no-store", or you poll a cached response and blame the backend
 *   - diff the serialized payload before setState, or cards flicker every tick
 *   - swallow errors and keep last good state; a dropped poll must never blank
 *     the screen mid-demo
 *   - never let a *successful* response blank it either. An unknown or expired
 *     session answers 200 with an empty listings array, so a tunnel restart or
 *     a TTL expiry mid-call would otherwise wipe a live board back to "Waiting
 *     for the call" and never recover.
 *
 * Pass `initial` from the server render so the first paint is never empty.
 * An empty `sessionId` disables polling (used by the static template page).
 */
export function usePolling(
  sessionId: string,
  intervalMs = 1200,
  initial: SessionState = DEFAULT_STATE,
): SessionState {
  const [state, setState] = useState<SessionState>(initial);
  const prev = useRef<string>(JSON.stringify(initial));
  // Guards against an older response landing after a newer one.
  const latest = useRef<number>(initial.updated_at ?? 0);
  const inFlight = useRef(false);

  useEffect(() => {
    if (!sessionId) return;
    let alive = true;

    const poll = async () => {
      if (inFlight.current) return;      // don't stack requests on a slow tunnel
      inFlight.current = true;
      try {
        const res = await fetch(`/api/state?session=${encodeURIComponent(sessionId)}`, {
          cache: "no-store",
          signal: AbortSignal.timeout(4000),
        });
        if (!res.ok) return;
        const data = (await res.json()) as SessionState;
        if (!alive || !data || !Array.isArray(data.listings)) return;

        // Stale response from a slow request that lost the race.
        const stamp = data.updated_at ?? 0;
        if (stamp && stamp < latest.current) return;

        // A live board never goes back to empty. That is an expired or unknown
        // session answering 200, not the renter's shortlist being cleared.
        setState((cur) => {
          if (data.listings.length === 0 && cur.listings.length > 0) return cur;
          const json = JSON.stringify(data);
          if (json === prev.current) return cur;
          prev.current = json;
          latest.current = stamp || latest.current;
          return data;
        });
      } catch {
        // server unreachable — keep last good state
      } finally {
        inFlight.current = false;
      }
    };

    poll();
    const id = setInterval(poll, intervalMs);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [sessionId, intervalMs]);

  return state;
}
