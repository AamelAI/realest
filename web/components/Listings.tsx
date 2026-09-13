"use client";

import { useEffect, useRef } from "react";
import { Money } from "./Money";
import { statusLineOf, factsOf, isSelectable } from "@/lib/present";
import { clock } from "@/lib/useCallTimers";
import type { Card } from "@/lib/types";

/**
 * One slot height for every rank. Consistent slots put every attribute in the
 * same place on every card, so the eye can rule a listing out without reading
 * it — and a fixed pitch is what lets the reorder stay a pure transform.
 */
const CARD = 204;
const GAP = 10;
const SLOT = CARD + GAP;

/**
 * The reorder is the centrepiece, so the list is never re-rendered into a new
 * DOM order. There is one node per listing, held in an absolutely positioned
 * slot, and re-ranking only changes that node's translateY — the card visibly
 * travels to its new position.
 *
 * `cards` arrives ranked from the server and is NEVER sorted here; rank is
 * simply its index. What we do hold is the order the cards were first seen in,
 * and we paint in that order forever, so React never moves a DOM node and no
 * transition is ever interrupted mid-travel.
 */
export function Listings({
  cards,
  selecting,
  selected,
  onToggle,
  starting = [],
  elapsed = {},
  maxRent,
}: {
  cards: Card[];
  /** the prompt is open, so cards are tappable to choose who to call */
  selecting: boolean;
  selected: string[];
  onToggle: (id: string) => void;
  /** tapped to call, not yet reflected by the server */
  starting?: string[];
  /** seconds on the phone, per listing */
  elapsed?: Record<string, number>;
  maxRent?: number | null;
}) {
  const rank = new Map(cards.map((c, i) => [c.listing_id, i]));
  const order = cards.map((c) => c.listing_id).join(",");

  // Paint order = first-seen order, held across polls. New listings append.
  const seen = useRef<string[]>([]);
  for (const c of cards) {
    if (!seen.current.includes(c.listing_id)) seen.current.push(c.listing_id);
  }
  const byId = new Map(cards.map((c) => [c.listing_id, c]));
  const stable = seen.current.map((id) => byId.get(id)).filter((c): c is Card => Boolean(c));

  // When cards cross, the one moving up passes over the ones it overtakes.
  // Left DOM order to decide, a promoted card would slide underneath. The lift
  // persists until that card moves again — cards never overlap at rest, and
  // resetting it on a timer would drop it mid-travel on the next re-render.
  const prevRank = useRef(new Map<string, number>());
  const lift = useRef(new Map<string, number>());
  for (const c of cards) {
    const now = rank.get(c.listing_id)!;
    const before = prevRank.current.get(c.listing_id);
    if (before !== undefined && before !== now) lift.current.set(c.listing_id, before - now);
  }
  useEffect(() => {
    prevRank.current = new Map(rank);
    // `order` is the only real dependency; `rank` is derived from it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [order]);

  return (
    <div className="relative isolate mx-4 mt-4" style={{ height: cards.length * SLOT }}>
      {stable.map((card) => {
        const r = rank.get(card.listing_id) ?? 0;
        return (
          <Row
            key={card.listing_id}
            card={card}
            rank={r}
            z={50 + (lift.current.get(card.listing_id) ?? 0)}
            selecting={selecting && isSelectable(card.status)}
            selected={selected.includes(card.listing_id)}
            onToggle={onToggle}
            starting={starting.includes(card.listing_id)}
            seconds={elapsed[card.listing_id]}
            maxRent={maxRent}
          />
        );
      })}
    </div>
  );
}

function Row({
  card, rank, z, selecting, selected, onToggle, starting, seconds, maxRent,
}: {
  card: Card;
  rank: number;
  z: number;
  selecting: boolean;
  selected: boolean;
  onToggle: (id: string) => void;
  starting: boolean;
  seconds?: number;
  maxRent?: number | null;
}) {
  const id = card.listing_id;
  const lead = rank === 0;
  const dead = card.status === "dead";
  const status = statusLineOf(card, starting);
  const facts = factsOf(card, maxRent);

  // Selection is a ring plus a check — never colour or fill alone. The lead
  // card carries the only shadow on the page; everything else is a hairline.
  const ring = selecting && selected ? "0 0 0 1.5px var(--color-ink)" : "";
  const lift = lead ? "0 1px 2px rgba(26,24,21,.04), 0 6px 16px rgba(26,24,21,.05)" : "";
  const boxShadow = [ring, lift].filter(Boolean).join(", ") || "none";

  return (
    <article
      data-listing-id={id}
      data-rank={rank}
      className="absolute inset-x-0 top-0"
      style={{
        height: CARD,
        zIndex: z,
        transform: `translateY(${rank * SLOT}px)`,
        transition: "transform 520ms cubic-bezier(.23,1,.32,1)",
      }}
    >
      <div
        className="relative h-full rounded-card border bg-surface transition-shadow duration-150"
        style={{ borderColor: "var(--color-line)", boxShadow }}
      >
        {/* The whole card is the target while choosing. A real button sits over
            the content, so there is exactly one interactive thing per card and
            the visible text stays readable to assistive tech as its label. */}
        {selecting && (
          <button
            type="button"
            role="checkbox"
            aria-checked={selected}
            aria-labelledby={`addr-${id}`}
            aria-describedby={`status-${id}`}
            onClick={() => onToggle(id)}
            className="absolute inset-0 z-[1] rounded-card [touch-action:manipulation]"
          />
        )}

        <div className="pointer-events-none relative flex h-full flex-col overflow-hidden p-3.5">
          {/* the claim: where, and what the listing says it is */}
          <div className="flex gap-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={card.photo_url}
              alt=""
              loading="lazy"
              className="h-[72px] w-[72px] shrink-0 rounded-photo object-cover"
              style={{
                background: "var(--color-press)",
                filter: dead ? "grayscale(1)" : undefined,
                opacity: dead ? 0.7 : 1,
              }}
            />
            <div className="min-w-0 flex-1">
              <div className="flex items-start justify-between gap-2">
                <h3
                  id={`addr-${id}`}
                  className={`line-clamp-2 text-address font-strong ${dead ? "text-ink-3 line-through" : ""}`}
                >
                  {card.address}
                </h3>
                {selecting && <Check on={selected} />}
              </div>
              <p className="mt-0.5 truncate text-support text-ink-2">
                <span className="tnum text-ink-3">#{rank + 1}</span>
                {" · "}
                {card.beds} bed · {card.baths} bath · {card.neighbourhood}
              </p>
            </div>
          </div>

          {/* the money, and where it stands */}
          <div className="mt-4 flex items-end justify-between gap-3">
            <Money card={card} lead={lead} maxRent={maxRent} />

            <div id={`status-${id}`} className="min-w-0 max-w-[52%] shrink text-right">
              <p
                className="flex items-center justify-end gap-1.5 text-support font-label"
                style={{ color: status.tone }}
              >
                <span
                  aria-hidden
                  className="inline-block h-[7px] w-[7px] shrink-0 rounded-full"
                  style={{ background: status.dot }}
                />
                <span className="truncate">{status.word}</span>
              </p>
              {(status.detail || (status.clock && seconds !== undefined)) && (
                <p className="truncate text-meta text-ink-3">
                  {status.detail}
                  {status.clock && seconds !== undefined && (
                    <span className="font-mono tnum"> · {clock(seconds)}</span>
                  )}
                </p>
              )}
            </div>
          </div>

          {/* what a human said, in ink; what the listing claims, in grey */}
          <p className="mt-auto truncate pt-2 text-support">
            {facts.length ? (
              facts.map((f, i) => (
                <span key={i}>
                  {i > 0 && <span className="text-ink-3"> · </span>}
                  {f.kind === "listed" && facts.findIndex((x) => x.kind === "listed") === i && (
                    <span className="text-ink-3">Listed: </span>
                  )}
                  <span
                    className={f.kind === "listed" ? "text-ink-2" : "font-label"}
                    style={{
                      color:
                        f.kind === "conflict" ? "var(--color-dead)"
                        : f.kind === "call" ? "var(--color-ink)"
                        : undefined,
                    }}
                  >
                    {f.kind === "listed" ? f.text.toLowerCase() : f.text}
                  </span>
                </span>
              ))
            ) : (
              <span className="text-ink-3">{card.transit_note}</span>
            )}
          </p>
        </div>
      </div>
    </article>
  );
}

/** The visible half of the checkbox. The button over the card is the real control. */
function Check({ on }: { on: boolean }) {
  return (
    <span
      aria-hidden
      className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-[1.5px] transition-colors duration-150"
      style={{
        borderColor: on ? "var(--color-ink)" : "var(--color-line)",
        background: on ? "var(--color-ink)" : "var(--color-surface)",
      }}
    >
      {on && (
        <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" aria-hidden>
          <path d="M3.5 8.5l3 3 6-7" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )}
    </span>
  );
}
