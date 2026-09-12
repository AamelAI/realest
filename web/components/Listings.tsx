"use client";

import { useRef } from "react";
import { statusOf, noteOf, rentOf, isSelectable } from "@/lib/present";
import type { Card } from "@/lib/types";

const SLOT = 154;   // one card's share of the column
const CARD = 144;   // the card itself; the 10px difference is the visual gap

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
}: {
  cards: Card[];
  /** the prompt is open, so checkboxes show */
  selecting: boolean;
  selected: string[];
  onToggle: (id: string) => void;
}) {
  const rank = new Map(cards.map((c, i) => [c.listing_id, i]));

  // Paint order = first-seen order, held across polls. New listings append.
  const seen = useRef<string[]>([]);
  for (const c of cards) {
    if (!seen.current.includes(c.listing_id)) seen.current.push(c.listing_id);
  }
  const byId = new Map(cards.map((c) => [c.listing_id, c]));
  const stable = seen.current.map((id) => byId.get(id)).filter((c): c is Card => Boolean(c));

  return (
    <div className="relative mx-[14px]" style={{ height: cards.length * SLOT + 8 }}>
      {stable.map((card) => (
        <Row
          key={card.listing_id}
          card={card}
          rank={rank.get(card.listing_id) ?? 0}
          selecting={selecting && isSelectable(card.status)}
          selected={selected.includes(card.listing_id)}
          onToggle={onToggle}
        />
      ))}
    </div>
  );
}

function Row({
  card, rank, selecting, selected, onToggle,
}: {
  card: Card; rank: number; selecting: boolean; selected: boolean;
  onToggle: (id: string) => void;
}) {
  const s = statusOf(card);
  const note = noteOf(card);
  const rent = rentOf(card);

  return (
    <article
      className="absolute left-0 right-0 flex overflow-hidden rounded-[14px] bg-surface"
      style={{
        height: CARD,
        transform: `translateY(${rank * SLOT}px)`,
        transition: "transform .6s cubic-bezier(.2,.8,.2,1), opacity .4s, border-color .4s",
        border: `1px solid ${s.proven ? "var(--real-40)" : "var(--hair-card)"}`,
        boxShadow: "0 1px 2px rgba(20,22,26,.05)",
        opacity: s.dead ? 0.62 : 1,
      }}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={card.photo_url}
        alt=""
        loading="lazy"
        className="h-full w-[92px] shrink-0 object-cover"
        style={{ background: "#e3e1dc" }}
      />

      <div className="flex min-w-0 flex-1 flex-col gap-[4px] px-3 py-[11px]">
        <div className="flex min-w-0 items-baseline gap-2">
          <span className="shrink-0 font-mono text-[11px] tnum text-faint">
            {String(rank + 1).padStart(2, "0")}
          </span>
          <h3
            className="min-w-0 truncate text-[14.5px] font-semibold tracking-[-0.01em]"
            style={{ textDecoration: s.dead ? "line-through" : "none" }}
          >
            {card.address}
          </h3>
        </div>

        <p className="truncate text-[11.5px] text-muted">
          {card.beds} bed · {card.neighbourhood} · {card.transit_note}
        </p>

        <div className="flex items-baseline gap-2">
          {rent.was && (
            <span className="font-mono text-[11.5px] tnum text-faint line-through">{rent.was}</span>
          )}
          <span className="font-mono text-[15px] font-medium tnum">{rent.now}</span>
        </div>

        {/* What the call turned up, and who said it. The handoff folds
            provenance into this line rather than giving it its own row — the
            card is a fixed 144px and a second row overflows it. */}
        {(note || card.outcome?.source) && (
          <p
            className="line-clamp-3 text-[11px] leading-[1.35]"
            style={{ color: s.proven || s.dead ? s.fg : "var(--color-muted)" }}
          >
            {note}
            {card.outcome?.source && (
              <span className="text-faint">{note ? " — " : ""}{card.outcome.source}</span>
            )}
          </p>
        )}
      </div>

      <div className="flex w-[76px] shrink-0 flex-col items-end justify-between py-[11px] pr-[11px]">
        <span
          className="whitespace-nowrap rounded-[7px] px-2 py-[4px] text-[10px] font-semibold"
          style={{ background: s.bg, color: s.fg }}
        >
          {s.label}
        </span>

        {selecting && (
          <label className="flex cursor-pointer items-center justify-center p-1">
            {/* The real input is visually hidden, so the focus ring has to be
                painted on the box beside it — otherwise a keyboard user can tab
                onto this control and see nothing at all. */}
            <input
              type="checkbox"
              checked={selected}
              onChange={() => onToggle(card.listing_id)}
              className="peer sr-only"
            />
            <span className="sr-only">Call the agent for {card.address}</span>
            <span
              aria-hidden
              className="flex h-[26px] w-[26px] items-center justify-center rounded-[8px] text-[14px] font-bold text-white transition-colors peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-[color:var(--color-accent)]"
              style={{
                border: `1.5px solid ${selected ? "var(--color-accent)" : "rgba(20,22,26,.2)"}`,
                background: selected ? "var(--color-accent)" : "#fff",
              }}
            >
              {selected ? "✓" : ""}
            </span>
          </label>
        )}
      </div>
    </article>
  );
}
