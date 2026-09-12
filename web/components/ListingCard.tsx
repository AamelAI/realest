"use client";

import { motion } from "framer-motion";
import type { Card } from "@/lib/types";

const money = (n: number) => "$" + n.toLocaleString("en-CA");

/* Status carries the only saturated colour on the page. */
const STATUS = {
  pending:   { label: "Not checked", fg: "text-muted",   bg: "bg-sunk",     ring: "ring-rule" },
  calling:   { label: "Calling",     fg: "text-live",    bg: "bg-live-bg",  ring: "ring-live/30" },
  verified:  { label: "Verified",    fg: "text-real",    bg: "bg-real-bg",  ring: "ring-real/30" },
  booked:    { label: "Booked",      fg: "text-real",    bg: "bg-real-bg",  ring: "ring-real/40" },
  no_answer: { label: "No answer",   fg: "text-live",    bg: "bg-live-bg",  ring: "ring-live/30" },
  dead:      { label: "Gone",        fg: "text-gone",    bg: "bg-gone-bg",  ring: "ring-gone/30" },
} as const;

export function ListingCard({
  card,
  selected,
  onToggle,
}: {
  card: Card;
  selected: boolean;
  onToggle: (id: string) => void;
}) {
  const s = STATUS[card.status];
  const dead = card.status === "dead";
  const selectable = card.status === "pending" || card.status === "verified";

  // The correction is the product: listed price struck, real price beside it.
  const real = card.outcome?.real_rent ?? null;
  const corrected = real !== null && real !== card.rent;

  return (
    <motion.article
      layout
      layoutId={card.listing_id}
      transition={{ type: "spring", stiffness: 420, damping: 38, mass: 0.7 }}
      className={`group relative overflow-hidden rounded-xl bg-card ring-1 ${s.ring} ${
        dead ? "opacity-55" : ""
      } ${selected ? "ring-2 ring-ink" : ""}`}
    >
      <div className="flex gap-3 p-3 sm:gap-4 sm:p-4">
        {/* photo */}
        <div className="relative shrink-0 overflow-hidden rounded-lg bg-sunk">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={card.photo_url}
            alt=""
            loading="lazy"
            className={`h-[76px] w-[76px] object-cover sm:h-[104px] sm:w-[104px] ${
              dead ? "grayscale" : ""
            }`}
          />
          <span className="absolute left-0 top-0 flex h-5 w-5 items-center justify-center rounded-br-lg bg-ink text-[10px] font-semibold text-paper tnum">
            {card.rank}
          </span>
        </div>

        {/* body */}
        <div className="flex min-w-0 flex-1 flex-col gap-1.5">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h3
                className={`truncate font-display text-[15px] font-bold leading-tight tracking-[-0.01em] sm:text-base ${
                  dead ? "line-through decoration-gone/70" : ""
                }`}
              >
                {card.address}
              </h3>
              <p className="eyebrow mt-0.5 text-muted">{card.neighbourhood}</p>
            </div>

            <div className="shrink-0 text-right">
              {corrected ? (
                <>
                  <div className="font-display text-[17px] font-extrabold leading-none tracking-[-0.02em] text-gone tnum sm:text-lg">
                    {money(real!)}
                  </div>
                  <div className="mt-0.5 text-[11px] text-muted line-through tnum">
                    {money(card.rent)}
                  </div>
                </>
              ) : (
                <div
                  className={`font-display text-[17px] font-extrabold leading-none tracking-[-0.02em] tnum sm:text-lg ${
                    dead ? "text-muted line-through" : ""
                  }`}
                >
                  {money(card.rent)}
                </div>
              )}
            </div>
          </div>

          <p className="text-[12.5px] text-ink-2 tnum">
            {card.beds} bed · {card.baths} bath
            {card.sqft ? ` · ${card.sqft} ft²` : ""}
            {card.parking_included ? " · parking" : ""}
          </p>
          <p className="truncate text-[12.5px] text-muted">
            {card.transit_note}
            {card.amenities.length ? ` · ${card.amenities.join(", ")}` : ""}
          </p>

          <div className="mt-0.5 flex flex-wrap items-center gap-1.5">
            <span
              className={`eyebrow inline-flex items-center gap-1.5 rounded-full px-2 py-1 font-medium ${s.bg} ${s.fg}`}
            >
              {card.status === "calling" && (
                <span className="dot-live h-1.5 w-1.5 rounded-full bg-live" />
              )}
              {s.label}
            </span>

            {card.outcome?.viewing_slot && (
              <span className="eyebrow rounded-full bg-real-bg px-2 py-1 font-medium text-real">
                {card.outcome.viewing_slot}
              </span>
            )}
            {card.outcome?.pets_allowed && (
              <span className="eyebrow rounded-full bg-sunk px-2 py-1 text-ink-2">
                {card.outcome.pets_allowed}
              </span>
            )}
          </div>
        </div>

        {selectable && (
          <label className="flex shrink-0 cursor-pointer items-start pt-0.5">
            <input
              type="checkbox"
              checked={selected}
              onChange={() => onToggle(card.listing_id)}
              className="h-[18px] w-[18px] cursor-pointer accent-[var(--color-ink)]"
              aria-label={`Select ${card.address}`}
            />
          </label>
        )}
      </div>

      {/* What a human told us, and who. Provenance is what turns this into evidence. */}
      {(card.outcome?.addons.length || card.outcome?.source || card.email_draft) && (
        <div className="border-t border-hair px-3 py-2.5 sm:px-4">
          {card.outcome?.addons.length ? (
            <p className="text-[12.5px] text-ink-2">
              <span className="text-muted">Not in the listing: </span>
              {card.outcome.addons.join(" · ")}
            </p>
          ) : null}

          {card.email_draft && (
            <div className="flex items-start gap-3">
              <p className="line-clamp-2 flex-1 text-[12.5px] italic text-ink-2">
                “{card.email_draft}”
              </p>
              <button
                type="button"
                className="shrink-0 rounded-md bg-ink px-2.5 py-1.5 text-[11px] font-semibold text-paper transition-opacity hover:opacity-85"
              >
                Send
              </button>
            </div>
          )}

          {card.outcome?.source && (
            <p className="mt-1 font-mono text-[10.5px] text-muted">— {card.outcome.source}</p>
          )}
        </div>
      )}
    </motion.article>
  );
}
