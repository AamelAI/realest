"use client";

import { motion } from "framer-motion";
import type { Card } from "@/lib/types";

const money = (n: number) => "$" + n.toLocaleString("en-CA");

/**
 * One line of the ledger.
 *
 * Status is a word, not a chip. The correction — listed rent struck, real rent
 * above it — is the whole point of the product, so it gets the largest figure
 * on the row and the only colour.
 */
export function ListingRow({
  card,
  selected,
  onToggle,
  lead = false,
}: {
  card: Card;
  selected: boolean;
  onToggle: (id: string) => void;
  lead?: boolean;
}) {
  const dead = card.status === "dead";
  const calling = card.status === "calling";
  const selectable = card.status === "pending" || card.status === "verified";

  const real = card.outcome?.real_rent ?? null;
  const corrected = real !== null && real !== card.rent;
  const over = corrected && real! > card.rent;

  // Status as a sentence, in its own colour. Never a badge.
  const note = (() => {
    switch (card.status) {
      case "booked":
        return { text: `Booked · ${card.outcome?.viewing_slot ?? ""}`, tone: "text-real" };
      case "verified":
        return {
          text: card.outcome?.viewing_slot
            ? `Verified · ${card.outcome.viewing_slot}`
            : "Verified",
          tone: "text-real",
        };
      case "calling":
        return { text: "Calling the listing agent…", tone: "text-live" };
      case "no_answer":
        return { text: "No answer · email drafted", tone: "text-live" };
      case "dead":
        return { text: "Gone · already leased", tone: "text-gone" };
      default:
        return { text: "Not checked yet", tone: "text-muted" };
    }
  })();

  return (
    <motion.div
      layout
      layoutId={card.listing_id}
      transition={{ type: "spring", stiffness: 380, damping: 36, mass: 0.8 }}
      onClick={selectable ? () => onToggle(card.listing_id) : undefined}
      className={`relative border-b border-hair transition-colors ${
        selectable ? "cursor-pointer hover:bg-wash" : ""
      } ${selected ? "bg-wash" : ""} ${dead ? "opacity-45" : ""} ${calling ? "sweep" : ""}`}
    >
      <div className="flex gap-4 py-4 sm:gap-5 sm:py-5">
        {/* rank sits in the margin like a footnote figure */}
        <span
          className={`w-4 shrink-0 pt-1 text-right font-mono text-[11px] tnum ${
            selected ? "text-ink" : "text-muted"
          }`}
        >
          {selected ? "✓" : card.rank}
        </span>

        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={card.photo_url}
          alt=""
          loading="lazy"
          className={`shrink-0 bg-wash object-cover ${
            lead ? "h-24 w-24 sm:h-32 sm:w-32" : "h-[72px] w-[72px] sm:h-24 sm:w-24"
          } ${dead ? "grayscale" : ""}`}
        />

        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <div className="flex items-start justify-between gap-3 sm:gap-5">
            <h3
              className={`min-w-0 font-semibold tracking-[-0.018em] text-balance ${
                lead ? "text-[19px] sm:text-[22px]" : "text-[17px] sm:text-[19px]"
              } ${dead ? "line-through decoration-gone decoration-1" : ""}`}
            >
              {card.address}
            </h3>

            {/* figures align to the right rule */}
            <div className="shrink-0 text-right">
              <div
                className={`font-semibold leading-none tnum ${
                  lead ? "text-[19px] sm:text-[22px]" : "text-[17px] sm:text-[19px]"
                } ${over ? "text-gone" : dead ? "text-muted line-through" : ""}`}
              >
                {money(real ?? card.rent)}
              </div>
              {corrected && (
                <div className="mt-1 font-mono text-[11px] text-muted line-through tnum">
                  {money(card.rent)}
                </div>
              )}
            </div>
          </div>

          <p className="font-mono text-[11.5px] leading-relaxed text-ink-2 tnum">
            {card.neighbourhood} · {card.beds} bed · {card.baths} bath
            {card.sqft ? <span className="hidden sm:inline"> · {card.sqft} ft²</span> : null}
            {" · "}
            {card.transit_note}
          </p>

          <p className={`font-mono text-[11.5px] ${note.tone}`}>{note.text}</p>

          {/* What a human said that the listing didn't. This is the product. */}
          {card.outcome?.addons.length ? (
            <p className="mt-1 text-[13.5px] text-ink-2">
              Not in the listing:{" "}
              <span className="text-ink">{card.outcome.addons.join(", ")}</span>
              {card.outcome.pets_allowed ? `. ${card.outcome.pets_allowed}.` : ""}
            </p>
          ) : card.outcome?.pets_allowed ? (
            <p className="mt-1 text-[13.5px] text-ink-2">
              Not in the listing: <span className="text-ink">{card.outcome.pets_allowed}</span>
            </p>
          ) : null}

          {card.email_draft && (
            <div className="mt-1.5 flex items-end gap-4">
              <p className="flex-1 border-l border-rule pl-3 text-[13px] italic text-ink-2">
                {card.email_draft}
              </p>
              <button
                type="button"
                onClick={(e) => e.stopPropagation()}
                className="shrink-0 border-b border-ink pb-0.5 text-[13px] font-medium transition-opacity hover:opacity-60"
              >
                Send
              </button>
            </div>
          )}

          {card.outcome?.source && (
            <p className="mt-1 font-mono text-[10.5px] text-muted">{card.outcome.source}</p>
          )}
        </div>
      </div>
    </motion.div>
  );
}
