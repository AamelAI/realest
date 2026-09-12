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
 */
export function usePolling(sessionId: string, intervalMs = 1500): SessionState {
  const [state, setState] = useState<SessionState>(DEFAULT_STATE);
  const prev = useRef<string>(JSON.stringify(DEFAULT_STATE));

  useEffect(() => {
    if (!sessionId) return;
    const poll = async () => {
      try {
        const res = await fetch(`/api/state?session=${sessionId}`, { cache: "no-store" });
        const data = (await res.json()) as SessionState;
        const json = JSON.stringify(data);
        if (json !== prev.current) {
          prev.current = json;
          setState(data);
        }
      } catch {
        // server unreachable - keep last good state
      }
    };
    poll();
    const id = setInterval(poll, intervalMs);
    return () => clearInterval(id);
  }, [sessionId, intervalMs]);

  return state;
}
