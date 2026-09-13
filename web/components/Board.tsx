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
import { ALL_ASKS } from "./VerifyPrompt";
import type { CallStatus, SessionState } from "@/lib/types";

type SendState = "idle" | "sending" | "sent" | "failed";
type Starting = { ids: string[]; base: Record<string, CallStatus> };

/**
 * How long a tap may go unconfirmed by the poll before we call it failed. The
 * server flips cards to calling before it dials, so a healthy start shows up
 * within a poll or two; this only catches a start that genuinely never landed.
 */
const START_EXPIRY_MS = 20000;

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
  const { state: polled, stale: pollStale } = usePolling(live ? sid : "", 1200, initial);
  const state = live ? polled : initial;
  const stale = live && pollStale;

  const [selected, setSelected] = useState<string[] | null>(null);
  const [asks, setAsks] = useState<string[]>(DEFAULT_ASKS);
  // Tapped "Call", not yet reflected by the server. `base` is each card's status
  // at the tap, so we can tell when the server has actually picked it up.
  const [starting, setStarting] = useState<Starting | null>(null);
  const [callFailed, setCallFailed] = useState(false);
  // Which tap a late response belongs to, and whether the poll already proved
  // that tap landed — so a slow 504 after the calls went out is not a failure.
  const attempt = useRef(0);
  const confirmed = useRef(false);
  // Survives a reload: the backend has no "already sent" flag, and re-arming
  // this button would mail the listing agent a second time.
  const [sends, setSends] = useState<Record<string, SendState>>({});

  // Read after mount, never during render — this component server-renders, and
  // sessionStorage does not exist there.
  useEffect(() => {
    try {
      const saved = sessionStorage.getItem(`realest:sent:${sid}`);
      if (saved) setSends(JSON.parse(saved));
    } catch {
      /* private mode — the button simply re-arms, the old behaviour */
    }
  }, [sid]);

  useEffect(() => {
    if (!Object.keys(sends).length) return;
    try {
      sessionStorage.setItem(`realest:sent:${sid}`, JSON.stringify(sends));
    } catch {
      /* ignore */
    }
  }, [sends, sid]);

  const phase = phaseOf(state);
  const criteria = useMemo(() => criteriaOf(state.preferences), [state.preferences]);
  const elapsed = useCallTimers(state.listings, stale);

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
  // We POST our own chip labels as extra_questions, and the server writes them
  // straight back into preferences. Echoing those as "what the renter said out
  // loud" would put words in their mouth, so only genuinely spoken questions
  // — the ones that are not one of our canned chips — are shown.
  const spokenAsk = (state.preferences.extra_questions ?? [])
    .filter((q) => !ALL_ASKS.includes(q))
    .join(" ");

  const rewritten =
    Boolean(state.agent_says) &&
    state.listings.some(
      (l) => l.outcome && ["verified", "booked", "dead"].includes(l.status),
    );

  // Default to the top three the ranker put up, but never fight a tap.
  const callable = new Set(selectable.map((l) => l.listing_id));
  const picks = (selected ?? selectable.slice(0, 3).map((l) => l.listing_id)).filter((id) =>
    callable.has(id),
  );
  const toggle = (id: string) =>
    setSelected(picks.includes(id) ? picks.filter((x) => x !== id) : [...picks, id]);

  const promptOpen = selectable.length > 0 && calling.length === 0 && !starting;

  // The tap has landed once any chosen card's status moves — to calling, or
  // straight to no_answer on the out-of-hours path, or past calling entirely if
  // a call finished between two polls.
  const byId = useMemo(
    () => new Map(state.listings.map((l) => [l.listing_id, l])),
    [state.listings],
  );
  const landed =
    !!starting &&
    starting.ids.some((id) => {
      const now = byId.get(id)?.status;
      return now !== undefined && now !== starting.base[id];
    });

  useEffect(() => {
    if (!starting || !landed) return;
    confirmed.current = true;
    setStarting(null);
  }, [starting, landed]);

  // A start the poll never confirms. Paused while stale: if we can't see the
  // server, we can't tell a failed start from a slow connection.
  useEffect(() => {
    if (!starting || stale) return;
    const ids = starting.ids;
    const t = setTimeout(() => {
      if (!confirmed.current) failStart(ids);
    }, START_EXPIRY_MS);
    return () => clearTimeout(t);
  }, [starting, stale]);

  function failStart(ids: string[]) {
    setStarting(null);
    setSelected(ids);
    setCallFailed(true);
  }

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

  /**
   * Optimistic, and deliberately not waiting on the response.
   *
   * /agent/start-calls now holds the request open until the listing agent's
   * call has finished — up to two minutes. Waiting on it froze the prompt, and
   * on a serverless host the function can be cut off first, which reported a
   * failure for calls that had gone out (and invited a second tap that dialled
   * the agents again). The poll is the source of truth; the response is only
   * consulted to catch a start that genuinely did nothing.
   */
  function startCalls() {
    if (!picks.length || starting) return;
    const ids = picks;
    const mine = ++attempt.current;
    confirmed.current = false;
    setCallFailed(false);
    setSelected([]);
    setStarting({ ids, base: Object.fromEntries(ids.map((id) => [id, byId.get(id)!.status])) });

    const stillMine = () => attempt.current === mine && !confirmed.current;

    fetch("/api/call", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ session_id: sid, listing_ids: ids, extra_questions: asks }),
    })
      .then(async (r) => {
        if (!r.ok) throw new Error(String(r.status));
        const body = (await r.json().catch(() => ({}))) as { called?: number; emailed?: number };
        // The server answered and placed nothing: no call, no email.
        if (body.called === 0 && !body.emailed && stillMine()) failStart(ids);
      })
      .catch(() => {
        if (stillMine()) failStart(ids);
      });
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
    <div className="min-h-dvh bg-ground pb-10">
      <Header
        criteria={criteria}
        fresh={fresh}
        status={stale ? "Reconnecting…" : HEADER_STATUS[phase]}
        count={state.listings.length}
        live={phase !== "waiting" && !stale}
        pulse={phase !== "waiting" && !stale && calling.length === 0}
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
              starting={starting?.ids}
            />

            {promptOpen && (
              <VerifyPrompt
                count={picks.length}
                asks={asks}
                onToggleAsk={(a) =>
                  setAsks((s) => (s.includes(a) ? s.filter((x) => x !== a) : [...s, a]))
                }
                spokenAsk={spokenAsk}
                onCall={startCalls}
                sending={Boolean(starting)}
                failed={callFailed}
              />
            )}

            {called.length > 0 && <CallsPanel cards={called} elapsed={elapsed} stale={stale} />}

            {/* "Shortlist, rewritten" is a claim. Only make it when a call
                actually returned facts — if every line went to voicemail,
                nothing was rewritten and the email cards tell the story. */}
            {rewritten && <Verdict says={state.agent_says} />}

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
