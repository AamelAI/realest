"use client";

import { useEffect, useRef, useState } from "react";
import { SessionState, DEFAULT_STATE } from "./types";

/**
 * Poll, don't socket. A 3rd-place winner shipped exactly this at 2000ms.
 * Websockets can drop mid-take; polling can't.
 *
 * Three things here matter:
 *   - cache: "no-store", or you poll a cached response and blame the backend
 *   - diff the serialized payload before setState, or cards flicker every tick
 *   - swallow errors and keep last good state; a dropped poll must never blank
 *     the screen mid-demo
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

  useEffect(() => {
    if (!sessionId) return;
    let alive = true;

    const poll = async () => {
      try {
        const res = await fetch(`/api/state?session=${sessionId}`, { cache: "no-store" });
        if (!res.ok) return;
        const data = (await res.json()) as SessionState;
        const json = JSON.stringify(data);
        if (alive && json !== prev.current) {
          prev.current = json;
          setState(data);
        }
      } catch {
        // server unreachable — keep last good state
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
