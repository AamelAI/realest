"use client";

import { money } from "@/lib/present";
import type { Card } from "@/lib/types";

/**
 * The rent, and the correction when a human gave us one.
 *
 * The real figure is the largest thing on the card and stays in ink — colour
 * on a headline price reads as an error. The listed figure sits beneath it,
 * struck, *with the word "Listed"*: a bare strikethrough is invisible on a
 * muted, compressed video and silent to a screen reader. The colour goes on
 * the small delta instead, which is what the renter actually needs to know.
 */
export function Money({
  card,
  lead = false,
  maxRent,
}: {
  card: Card;
  lead?: boolean;
  maxRent?: number | null;
}) {
  const listed = card.rent;
  const real = card.outcome?.real_rent ?? null;
  const corrected = real !== null && real !== listed;
  const now = corrected ? real : listed;
  const delta = corrected ? real - listed : 0;
  const over = maxRent != null && maxRent > 0 && now > maxRent;

  return (
    <div className="min-w-0">
      <div aria-hidden className="flex items-baseline gap-1">
        <span className={`${lead ? "text-rent-lead" : "text-rent"} font-strong tnum`}>
          {money(now)}
        </span>
        <span className="text-support text-ink-2">/mo</span>
      </div>

      {corrected && (
        <div aria-hidden className="mt-1 flex items-baseline gap-2 text-support">
          <span className="text-ink-3">
            Listed <s className="tnum">{money(listed)}</s>
          </span>
          <span
            className="font-label tnum"
            style={{ color: delta > 0 ? "var(--color-dead)" : "var(--color-real)" }}
          >
            {delta > 0 ? "+" : "−"}
            {money(Math.abs(delta))}/mo
          </span>
        </div>
      )}

      <span className="sr-only">
        {corrected
          ? `Real rent ${money(now)} a month, listed as ${money(listed)}.`
          : `${money(now)} a month.`}
        {over ? " Over your budget." : ""}
      </span>
    </div>
  );
}
