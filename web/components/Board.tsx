"use client";

import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ListingCard } from "./ListingCard";
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
  // Server-rendered first paint, then the poller takes over. `live={false}`
  // renders the static template with mock data.
  const polled = usePolling(live ? sid : "", 1200, initial);
  const state = live ? polled : initial;

  const [selected, setSelected] = useState<string[]>([]);
  const toggle = (id: string) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  const calling = state.listings.some((l) => l.status === "calling");
  const prefs = state.preferences;
  const summary = useMemo(() => {
    const bits: string[] = [];
    if (prefs.beds) bits.push(`${prefs.beds} bed`);
    if (prefs.areas?.length) bits.push(prefs.areas.join(" · "));
    if (prefs.max_rent) bits.push(`under $${prefs.max_rent.toLocaleString("en-CA")}`);
    if (prefs.parking) bits.push("parking");
    return bits.join("  ·  ");
  }, [prefs]);

  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-20 border-b border-rule bg-paper/85 backdrop-blur-md">
        <div className="mx-auto max-w-5xl px-4 py-3 sm:px-6 sm:py-4">
          <div className="flex items-baseline justify-between gap-4">
            <h1 className="font-display text-[17px] font-extrabold tracking-[-0.02em] sm:text-xl">
              Realest
            </h1>
            <span className="eyebrow flex items-center gap-1.5 text-muted">
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  calling ? "dot-live bg-live" : "bg-real"
                }`}
              />
              {calling ? "On the phone" : "Live"}
            </span>
          </div>

          {summary && <p className="mt-1 text-[12.5px] text-muted tnum">{summary}</p>}

          {/* What the agent last said, so a viewer can follow without audio.
              initial={false}: present on first paint, animates only on change —
              a fade-in here leaves a hole in the most important line. */}
          <AnimatePresence mode="wait" initial={false}>
            {state.agent_says && (
              <motion.p
                key={state.agent_says}
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="mt-2.5 border-l-2 border-ink pl-3 text-[13px] leading-snug text-ink-2 sm:text-sm"
              >
                {state.agent_says}
              </motion.p>
            )}
          </AnimatePresence>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 pb-32 pt-4 sm:px-6 sm:pt-6">
        {state.listings.length === 0 ? (
          <p className="py-24 text-center text-sm text-muted">
            Tell the agent what you&rsquo;re after and your shortlist appears here.
          </p>
        ) : (
          <motion.div layout className="grid gap-3 md:grid-cols-2 md:gap-4">
            {state.listings.map((card) => (
              <ListingCard
                key={card.listing_id}
                card={card}
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
            initial={{ y: 80 }}
            animate={{ y: 0 }}
            exit={{ y: 80 }}
            transition={{ type: "spring", stiffness: 400, damping: 34 }}
            className="fixed inset-x-0 bottom-0 z-30 border-t border-rule bg-card/95 backdrop-blur-md"
            style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
          >
            <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
              <div>
                <p className="font-display text-[15px] font-bold tnum">
                  {selected.length} selected
                </p>
                <p className="text-[12px] text-muted">
                  We&rsquo;ll ask: still available · real cost · pets
                </p>
              </div>
              <button
                type="button"
                // TODO(hackathon): POST selected ids to /agent/start-calls
                className="rounded-lg bg-ink px-5 py-2.5 font-display text-[14px] font-bold text-paper transition-opacity hover:opacity-85 active:opacity-70"
              >
                Call {selected.length === 1 ? "them" : "all " + selected.length}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
