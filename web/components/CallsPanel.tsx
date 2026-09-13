"use client";

import { statusOf, noteOf } from "@/lib/present";
import { clock } from "@/lib/useCallTimers";
import type { Card } from "@/lib/types";

/**
 * Three calls at once, running in parallel. This is the frame that a chat
 * window cannot produce, so it gets its own panel rather than living inside
 * the rows.
 *
 * We show only what the telephony layer actually reports — a line is either on
 * the phone or it has come back with something. The prototype cycled
 * "dialing / ringing / connected"; our backend does not know which of those is
 * true, and inventing it would undercut the one claim the product rests on.
 */
/** Only a call a human picked up gets an "answered" duration. */
const answered = (c: Card) =>
  c.status === "verified" || c.status === "booked" || c.status === "dead";

export function CallsPanel({
  cards,
  elapsed,
  stale = false,
}: {
  /** every listing we placed a call to this session, in call order */
  cards: Card[];
  elapsed: Record<string, number>;
  /** the connection is down — stop claiming the calls are visibly live */
  stale?: boolean;
}) {
  if (!cards.length) return null;

  const live = cards.filter((c) => c.status === "calling").length;
  const longest = Math.max(0, ...cards.map((c) => elapsed[c.listing_id] ?? 0));

  return (
    <section
      className="r-in mx-[14px] mt-4 overflow-hidden rounded-[16px]"
      style={{ border: "1px solid var(--hair-card)" }}
      aria-label="Calls to listing agents"
    >
      <div className="flex items-center gap-[7px] px-[14px] py-3" style={{ background: "var(--color-ink)" }}>
        {live > 0 && !stale && (
          <span
            aria-hidden
            className="r-pulse-fast inline-block h-[6px] w-[6px] rounded-full"
            style={{ background: "#7dd3a0" }}
          />
        )}
        <span className="text-[12.5px] font-semibold text-white">
          {live > 0 ? `${live} call${live === 1 ? "" : "s"} in progress` : `${cards.length} call${cards.length === 1 ? "" : "s"} complete`}
        </span>
        {/* Only ever show a duration this browser actually measured. A page
            opened after the calls finished never saw them ring, and printing
            0:00 would be inventing a fact. */}
        {longest > 0 && (
          <span className="ml-auto font-mono text-[11px] tnum" style={{ color: "rgba(255,255,255,.6)" }}>
            {clock(longest)}
          </span>
        )}
      </div>

      {cards.map((card, i) => {
        const s = statusOf(card);
        const note = noteOf(card);
        const secs = elapsed[card.listing_id];
        return (
          <div
            key={card.listing_id}
            className="r-in bg-surface px-[14px] py-3"
            style={{ borderBottom: "1px solid var(--hair-row)", animationDelay: `${i * 260}ms` }}
          >
            <div className="flex items-center gap-[9px]">
              <span
                aria-hidden
                className="inline-block h-[7px] w-[7px] shrink-0 rounded-full"
                style={{ background: s.dot }}
              />
              <div className="min-w-0 flex-1">
                <p className="truncate text-[13px] font-semibold">{card.address}</p>
                <p className="truncate text-[10.5px] text-faint">{card.agent_name}</p>
              </div>
              <span className="shrink-0 font-mono text-[11px] tnum" style={{ color: s.fg }}>
                {card.status === "calling"
                  ? secs !== undefined
                    ? `on the call · ${clock(secs)}`
                    : "on the call"
                  : answered(card) && secs
                    ? `answered ${secs}s`
                    : s.short}
              </span>
            </div>

            {note && (
              <p
                className="mt-[9px] rounded-[9px] px-[10px] py-[9px] text-[11.5px] leading-[1.45]"
                style={{ background: s.bg, color: s.fg }}
              >
                {note}
              </p>
            )}
          </div>
        );
      })}
    </section>
  );
}
