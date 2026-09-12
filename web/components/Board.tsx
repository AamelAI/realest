"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Header } from "./Header";
import { Listings } from "./Listings";
import { VerifyPrompt, DEFAULT_ASKS } from "./VerifyPrompt";
import { CallsPanel } from "./CallsPanel";
import { Verdict, EmailCard } from "./Outcome";
import { usePolling } from "@/lib/usePolling";
import { useCallTimers } from "@/lib/useCallTimers";
import { criteriaOf, phaseOf, HEADER_STATUS, isSelectable } from "@/lib/present";
import type { SessionState } from "@/lib/types";

type SendState = "idle" | "sending" | "sent" | "failed";

export function Board({
  sid,
  initial,
  live = true,
}: {
  sid: string;
  initial: SessionState;
  live?: boolean;
}) {
  // Server-rendered first paint, then the poller takes over.
  // live={false} renders the static template with mock data.
  const polled = usePolling(live ? sid : "", 1200, initial);
  const state = live ? polled : initial;

  const [selected, setSelected] = useState<string[] | null>(null);
  const [asks, setAsks] = useState<string[]>(DEFAULT_ASKS);
  const [sending, setSending] = useState(false);
  const [sends, setSends] = useState<Record<string, SendState>>({});

  const phase = phaseOf(state);
  const criteria = useMemo(() => criteriaOf(state.preferences), [state.preferences]);
  const elapsed = useCallTimers(state.listings);

  // Chips heard since the page opened are tinted. The first paint is the
  // renter's opening brief, so nothing in it counts as "just heard".
  const opening = useRef<Set<string> | null>(null);
  if (opening.current === null && criteria.length) {
    opening.current = new Set(criteria.map((c) => c.key));
  }
  const fresh = useMemo(() => {
    const base = opening.current;
    if (!base) return new Set<string>();
    return new Set(criteria.filter((c) => !base.has(c.key)).map((c) => c.key));
  }, [criteria]);

  const selectable = state.listings.filter((l) => isSelectable(l.status));
  const calling = state.listings.filter((l) => l.status === "calling");
  const called = state.listings.filter((l) => l.status !== "pending");
  const noAnswer = state.listings.filter((l) => l.status === "no_answer" && l.email_draft);

  // Default to the top three the ranker put up, but never fight a tap.
  const picks = selected ?? selectable.slice(0, 3).map((l) => l.listing_id);
  const toggle = (id: string) =>
    setSelected(picks.includes(id) ? picks.filter((x) => x !== id) : [...picks, id]);

  const promptOpen = selectable.length > 0 && calling.length === 0 && !sending;

  // The reorder is the centrepiece, and a screen reader cannot see a transform.
  const order = state.listings.map((l) => l.listing_id).join(",");
  const [announce, setAnnounce] = useState("");
  const prevOrder = useRef(order);
  useEffect(() => {
    if (prevOrder.current !== order && state.listings.length) {
      prevOrder.current = order;
      setAnnounce(`Shortlist reordered: ${state.listings[0].address} now first.`);
    }
  }, [order, state.listings]);

  async function startCalls() {
    if (!picks.length || sending) return;
    setSending(true);
    const ids = picks;
    try {
      await fetch("/api/call", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ session_id: sid, listing_ids: ids, extra_questions: asks }),
      });
      setSelected([]);
    } catch {
      // The voice loop is the source of truth; a failed tap is never fatal.
    } finally {
      setSending(false);
    }
  }

  async function sendEmail(id: string) {
    setSends((s) => ({ ...s, [id]: "sending" }));
    try {
      const r = await fetch("/api/email", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ session_id: sid, listing_id: id }),
      });
      const ok = r.ok && (await r.json())?.sent === true;
      setSends((s) => ({ ...s, [id]: ok ? "sent" : "failed" }));
    } catch {
      setSends((s) => ({ ...s, [id]: "failed" }));
    }
  }

  return (
    <div className="min-h-dvh bg-surface pb-10">
      <Header
        criteria={criteria}
        fresh={fresh}
        status={HEADER_STATUS[phase]}
        count={state.listings.length}
        live={phase !== "waiting"}
      />

      <p aria-live="polite" className="sr-only">{announce}</p>

      <main className="mx-auto max-w-[820px]">
        {state.listings.length === 0 ? (
          <div className="px-[26px] py-16 text-center">
            <p className="text-[14px] font-semibold">Waiting for the call</p>
            <p className="mt-1 text-[12.5px] leading-[1.5] text-faint">
              Say what you&rsquo;re after. This page fills in while you talk.
            </p>
          </div>
        ) : (
          <>
            <Listings
              cards={state.listings}
              selecting={promptOpen}
              selected={picks}
              onToggle={toggle}
            />

            {promptOpen && (
              <VerifyPrompt
                count={picks.length}
                asks={asks}
                onToggleAsk={(a) =>
                  setAsks((s) => (s.includes(a) ? s.filter((x) => x !== a) : [...s, a]))
                }
                spokenAsk={(state.preferences.extra_questions ?? []).join(" ")}
                onCall={startCalls}
                sending={sending}
              />
            )}

            {called.length > 0 && <CallsPanel cards={called} elapsed={elapsed} />}

            {phase === "verified" && <Verdict says={state.agent_says} />}

            {noAnswer.map((card) => (
              <EmailCard
                key={card.listing_id}
                card={card}
                onSend={sendEmail}
                state={sends[card.listing_id] ?? "idle"}
              />
            ))}
          </>
        )}
      </main>
    </div>
  );
}
