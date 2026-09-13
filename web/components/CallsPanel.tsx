"use client";

import { statusLineOf, noteOf } from "@/lib/present";
import { clock } from "@/lib/useCallTimers";
import type { Card } from "@/lib/types";

/**
 * The calls, one row each, resolving independently as each agent answers.
 * Several lines open at once is the thing a chat window cannot do, so it gets
 * its own list — on the same light material as everything else.
 *
 * Only what the telephony layer reports is shown: a line is on the phone, or it
 * has come back with something. No invented "dialing / ringing" steps, no
 * estimates, no Stop button the backend couldn't honour.
 */
export function CallsPanel({
  cards,
  elapsed,
  stale = false,
}: {
  /** every listing we placed a call to this session */
  cards: Card[];
  elapsed: Record<string, number>;
  /** the connection is down — stop claiming the calls are visibly live */
  stale?: boolean;
}) {
  if (!cards.length) return null;

  const live = cards.filter((c) => c.status === "calling").length;
  // Only a duration this browser actually measured. A page opened after the
  // calls finished never saw them ring, and printing 0:00 would invent a fact.
  const longest = Math.max(0, ...cards.map((c) => elapsed[c.listing_id] ?? 0));

  return (
    <section
      className="r-in mx-4 mt-6 overflow-hidden rounded-card border bg-surface"
      style={{ borderColor: "var(--color-line)", animationDelay: "calc(var(--intro-on, 0) * 560ms)" }}
      aria-label="Calls to listing agents"
    >
      <div
        className="flex items-center gap-2 border-b px-4 py-3"
        style={{ borderColor: "var(--color-hair)" }}
      >
        {live > 0 && (
          <span
            aria-hidden
            className={`${stale ? "" : "r-pulse"} inline-block h-[7px] w-[7px] shrink-0 rounded-full`}
            style={{ background: "var(--color-live)" }}
          />
        )}
        <h2 className="min-w-0 truncate text-support font-strong">{summary(cards, live)}</h2>
        {longest > 0 && (
          <span className="ml-auto shrink-0 font-mono text-meta tnum text-ink-3">{clock(longest)}</span>
        )}
      </div>

      <ul>
        {cards.map((card, i) => {
          const s = statusLineOf(card);
          const note = noteOf(card);
          const secs = elapsed[card.listing_id];
          return (
            <li
              key={card.listing_id}
              className="r-in px-4 py-3"
              style={{
                animationDelay: `${i * 50}ms`,
                borderTop: i ? "1px solid var(--color-hair)" : undefined,
              }}
            >
              <div className="flex items-start gap-2.5">
                <span
                  aria-hidden
                  className="mt-[7px] inline-block h-[7px] w-[7px] shrink-0 rounded-full"
                  style={{ background: s.dot }}
                />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-support font-strong">{card.address}</p>
                  {card.agent_name && !s.detail.includes(card.agent_name) && (
                    <p className="truncate text-meta text-ink-3">{card.agent_name}</p>
                  )}
                </div>
                <div className="shrink-0 text-right">
                  <p className="text-support font-label" style={{ color: s.tone }}>{s.word}</p>
                  {s.clock && secs !== undefined ? (
                    <p className="font-mono text-meta tnum text-ink-3">{clock(secs)}</p>
                  ) : s.detail ? (
                    <p className="max-w-[150px] truncate text-meta text-ink-3">{s.detail}</p>
                  ) : null}
                </div>
              </div>
              {note && <p className="mt-1.5 pl-[17px] text-support text-ink-2">{note}</p>}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

/** Counts, not adjectives: "3 calls · 2 back · 1 on the line", then the outcome. */
function summary(cards: Card[], live: number): string {
  const n = cards.length;
  if (live > 0) {
    const back = n - live;
    return back > 0
      ? `${n} calls · ${back} back · ${live} on the line`
      : `${live} call${live === 1 ? "" : "s"} on the line`;
  }
  const confirmed = cards.filter((c) => c.status === "verified" || c.status === "booked").length;
  const leased = cards.filter((c) => c.status === "dead").length;
  const unanswered = cards.filter((c) => c.status === "no_answer").length;
  const parts = [
    confirmed && `${confirmed} confirmed`,
    leased && `${leased} leased`,
    unanswered && `${unanswered} no answer`,
  ].filter(Boolean);
  return parts.length ? parts.join(" · ") : `${n} call${n === 1 ? "" : "s"} complete`;
}
