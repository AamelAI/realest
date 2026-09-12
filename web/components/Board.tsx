"use client";

import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ListingRow } from "./ListingRow";
import { usePolling } from "@/lib/usePolling";
import type { SessionState } from "@/lib/types";

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

  const [selected, setSelected] = useState<string[]>([]);
  const [sending, setSending] = useState(false);
  const toggle = (id: string) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  // The approval gate. Voice asked "anything else you want me to ask?"; this is
  // where the caller says which ones. Clear selection immediately so the cards
  // flipping to "calling" are the only feedback that matters.
  async function startCalls() {
    if (!selected.length || sending) return;
    setSending(true);
    const ids = selected;
    setSelected([]);
    try {
      await fetch("/api/call", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ session_id: sid, listing_ids: ids }),
      });
    } catch {
      // The voice loop is the source of truth; a failed tap is never fatal.
      setSelected(ids);
    } finally {
      setSending(false);
    }
  }

  const calling = state.listings.filter((l) => l.status === "calling").length;
  const p = state.preferences;

  const brief = useMemo(() => {
    const bits: string[] = [];
    if (p.beds) bits.push(`${p.beds} bed`);
    if (p.areas?.length) bits.push(p.areas.join(", "));
    if (p.max_rent) bits.push(`under $${p.max_rent.toLocaleString("en-CA")}`);
    if (p.parking) bits.push("parking");
    return bits.join(" · ");
  }, [p]);

  return (
    <div className="min-h-dvh">
      {/* Solid, hairline-ruled. No blur, no floating panel. */}
      <header className="border-b border-rule bg-paper">
        <div className="mx-auto max-w-3xl px-5 pb-5 pt-6 sm:px-8 sm:pt-8">
          <div className="flex items-baseline justify-between gap-6">
            <h1 className="text-[15px] font-semibold tracking-[-0.01em]">Realest</h1>
            <p className="font-mono text-[11px] tnum text-muted">
              {calling > 0
                ? `${calling} call${calling > 1 ? "s" : ""} in progress`
                : `${state.listings.length} listings`}
            </p>
          </div>

          {brief && (
            <p className="mt-1 font-mono text-[11.5px] tnum text-muted">{brief}</p>
          )}

          {/* The agent's last line. Present on first paint; animates only on change. */}
          <AnimatePresence mode="wait" initial={false}>
            {state.agent_says && (
              <motion.p
                key={state.agent_says}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.18 }}
                className="mt-4 max-w-[46ch] text-[19px] font-medium leading-[1.3] tracking-[-0.018em] sm:text-[22px]"
              >
                {state.agent_says}
              </motion.p>
            )}
          </AnimatePresence>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-5 pb-32 sm:px-8">
        {state.listings.length === 0 ? (
          <p className="py-24 text-[15px] text-muted">
            Tell the agent what you&rsquo;re after and your shortlist appears here.
          </p>
        ) : (
          <motion.div layout>
            {state.listings.map((card, i) => (
              <ListingRow
                key={card.listing_id}
                card={card}
                lead={i === 0}
                selected={selected.includes(card.listing_id)}
                onToggle={toggle}
              />
            ))}
          </motion.div>
        )}
      </main>

      {/* Tap-to-confirm: more reliable than parsing multi-select out of speech. */}
      <AnimatePresence>
        {selected.length > 0 && (
          <motion.div
            initial={{ y: 90 }}
            animate={{ y: 0 }}
            exit={{ y: 90 }}
            transition={{ type: "spring", stiffness: 420, damping: 36 }}
            className="fixed inset-x-0 bottom-0 z-30 border-t border-ink bg-paper"
            style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
          >
            <div className="mx-auto flex max-w-3xl items-center justify-between gap-6 px-5 py-4 sm:px-8">
              <p className="font-mono text-[11.5px] tnum text-ink-2">
                {selected.length} selected · we&rsquo;ll ask availability, real cost, pets
              </p>
              <button
                type="button"
                onClick={startCalls}
                disabled={sending}
                className="shrink-0 bg-ink px-5 py-2.5 text-[14px] font-semibold text-paper transition-opacity hover:opacity-80 active:opacity-65 disabled:opacity-40"
              >
                {sending
                  ? "Dialling…"
                  : `Call ${selected.length === 1 ? "them" : `all ${selected.length}`}`}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
