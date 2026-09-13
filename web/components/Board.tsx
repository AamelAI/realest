"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Header } from "./Header";
import { Listings } from "./Listings";
import { VerifyPrompt, DEFAULT_ASKS } from "./VerifyPrompt";
import { CallsPanel } from "./CallsPanel";
import { Caption, EmailCard } from "./Outcome";
import { usePolling } from "@/lib/usePolling";
import { useCallTimers } from "@/lib/useCallTimers";
import { criteriaOf, phaseOf, HEADER_STATUS, isSelectable } from "@/lib/present";
import { ALL_ASKS } from "./VerifyPrompt";
import type { CallStatus, SessionState } from "@/lib/types";

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
  // The page-open choreography plays once, while the page assembles. After that,
  // anything that appears animates immediately instead of waiting its turn.
  const [intro, setIntro] = useState(true);
  useEffect(() => {
    const t = setTimeout(() => setIntro(false), 1800);
    return () => clearTimeout(t);
  }, []);

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

  // Default to the top three nobody has called yet — never quietly queue a
  // listing an agent already confirmed. Those can still be added by hand.
  const callable = new Set(selectable.map((l) => l.listing_id));
  const uncalled = state.listings.filter((l) => l.status === "pending");
  const picks = (selected ?? uncalled.slice(0, 3).map((l) => l.listing_id)).filter((id) =>
    callable.has(id),
  );
  const toggle = (id: string) =>
    setSelected(picks.includes(id) ? picks.filter((x) => x !== id) : [...picks, id]);

  // Offer calls while there is something left to check.
  const promptOpen = uncalled.length > 0 && calling.length === 0 && !starting;

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
  // Every reorder is announced, not only a new #1; the first fill is not a
  // reorder, so an empty board filling up says nothing.
  const order = state.listings.map((l) => l.listing_id).join(",");
  const topAddress = state.listings[0]?.address ?? "";
  const [announce, setAnnounce] = useState("");
  const prevOrder = useRef(order);
  useEffect(() => {
    const before = prevOrder.current;
    prevOrder.current = order;
    if (!before || !order || before === order) return;
    const sameSet = before.split(",").sort().join() === order.split(",").sort().join();
    if (!sameSet) return;
    setAnnounce(
      before.split(",")[0] !== order.split(",")[0]
        ? `Shortlist reordered. ${topAddress} is now first.`
        : "Shortlist reordered.",
    );
  }, [order, topAddress]);

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

  return (
    <div
      className="min-h-dvh bg-ground pb-10"
      style={{ ["--intro-on" as string]: intro ? 1 : 0 }}
    >
      <Header
        criteria={criteria}
        fresh={fresh}
        status={stale ? "Reconnecting…" : HEADER_STATUS[phase]}
        count={state.listings.length}
        live={phase !== "waiting" && !stale}
        pulse={phase !== "waiting" && !stale && calling.length === 0}
      />

      <Caption says={state.agent_says} />

      <p aria-live="polite" className="sr-only">{announce}</p>

      <main className="mx-auto max-w-[820px]">
        {state.listings.length === 0 ? (
          <div className="px-6 py-20 text-center">
            <p className="text-fact font-strong">No listings yet.</p>
            <p className="mt-1 text-support text-ink-2">
              They appear here as you describe what you want.
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
              elapsed={elapsed}
              maxRent={state.preferences.max_rent}
            />

            {promptOpen && (
              <VerifyPrompt
                count={picks.length}
                names={picks.map((id) => byId.get(id)?.agent_name ?? "")}
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

            {noAnswer.map((card) => (
              <EmailCard key={card.listing_id} card={card} />
            ))}
          </>
        )}
      </main>
    </div>
  );
}
