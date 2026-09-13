// The adapter: our live SessionState -> the view model the design handoff
// specifies. Everything here is derived from what a human actually told us.
//
// The rule that governs this file: if the server does not know it, the page
// does not show it. The product's whole claim is that these facts came off a
// phone call, so a plausible-looking invented status would be the one bug that
// matters.

import type { Card, CallStatus, SessionState } from "./types";

export const money = (n: number) => "$" + n.toLocaleString("en-CA");

// Colour means status and nothing else. Three hues — confirmed, live, gone —
// and everything else is ink. "No answer" is deliberately not a warning colour:
// nobody picking up is a normal outcome with the next step already taken.
// Every value is a literal `var(--color-…)` so the token is always emitted.
const REAL = "var(--color-real)";
const LIVE = "var(--color-live)";
const DEAD = "var(--color-dead)";
const QUIET = "var(--color-ink-2)";
const NONE = "var(--color-ink-3)";

/* ── the status line: what happened, and who said so ─────────────────────── */

export type StatusLine = {
  /** the word, set in its colour */
  word: string;
  /** who said it and when, verbatim — or the next step */
  detail: string;
  /** a live call length to show in mono after the detail */
  clock: boolean;
  tone: string;
  dot: string;
};

/**
 * One line that replaces the tinted pill. The attributed fact is the badge:
 * "Confirmed · Mark, 1:42pm" says more than a green "Real" ever could.
 *
 * `outcome.source` is free-form text written by the call extractor, so it is
 * rendered exactly as it arrived — never parsed, never reformatted, and never
 * given a time it didn't come with.
 */
export function statusLineOf(card: Card, starting = false): StatusLine {
  const o = card.outcome;
  const src = o?.source?.trim() ?? "";
  if (starting && isSelectable(card.status)) {
    return { word: "Starting call…", detail: "", clock: false, tone: LIVE, dot: LIVE };
  }
  switch (card.status) {
    case "calling":
      return {
        word: "On the phone",
        detail: card.agent_name ? `with ${card.agent_name}` : "",
        clock: true, tone: LIVE, dot: LIVE,
      };
    case "verified":
      return { word: "Confirmed", detail: src, clock: false, tone: REAL, dot: REAL };
    case "booked":
      return { word: "Booked", detail: src, clock: false, tone: REAL, dot: REAL };
    case "dead":
      return { word: "Leased", detail: src, clock: false, tone: DEAD, dot: DEAD };
    case "no_answer":
      return { word: "No answer", detail: "Draft ready", clock: false, tone: QUIET, dot: NONE };
    default:
      return { word: "Not checked yet", detail: "", clock: false, tone: NONE, dot: "var(--color-line)" };
  }
}

/* ── facts: two inks, so a human's word never looks like a listing's claim ── */

export type Fact = { text: string; kind: "call" | "listed" | "conflict" };

/**
 * What the card knows beyond the rent. A fact a person said on the phone and a
 * claim copied from the listing must never look the same — the first is the
 * product, the second is what the product exists to check.
 *
 * Only numeric conflicts are called out (the real rent over the renter's cap).
 * Free-text judgements like "cats only vs. a dog" are left to the renter.
 */
export function factsOf(card: Card, maxRent?: number | null): Fact[] {
  const o = card.outcome;
  const out: Fact[] = [];
  const now = o?.real_rent ?? card.rent;
  if (maxRent && maxRent > 0 && now > maxRent) {
    out.push({ text: `Over your ${money(maxRent)} budget`, kind: "conflict" });
  }
  if (o) {
    for (const a of o.addons) out.push({ text: cap(a), kind: "call" });
    if (o.pets_allowed) out.push({ text: cap(o.pets_allowed), kind: "call" });
    if (o.viewing_slot) out.push({ text: `Viewing ${o.viewing_slot}`, kind: "call" });
    for (const [k, v] of Object.entries(o.answers ?? {})) out.push({ text: `${cap(k)}: ${v}`, kind: "call" });
    return out;
  }
  if (card.parking_included) out.push({ text: "Parking included", kind: "listed" });
  if (card.pets) out.push({ text: `Pets: ${card.pets}`, kind: "listed" });
  return out;
}

/* ── the note: what the call actually turned up ──────────────────────────── */

export function noteOf(card: Card): string {
  const o = card.outcome;
  switch (card.status) {
    case "dead":
      return "The agent said it is gone — the listing is still up.";
    case "no_answer":
      return "No answer, so we emailed instead.";
    case "calling":
      return "";
    case "pending":
      return "";
    default: {
      if (!o) return "";
      // Terse on purpose: this is the one-sentence account of the call shown
      // under each row of the calls list.
      const bits: string[] = [];
      if (o.addons.length) {
        const real = o.real_rent;
        bits.push(
          real && real > card.rent
            ? `${cap(o.addons.join(", "))} on top — really ${money(real)}.`
            : real && real < card.rent
              ? `${cap(o.addons.join(", "))}. Really ${money(real)}.`
              : `${cap(o.addons.join(", "))}.`,
        );
      }
      if (o.pets_allowed) bits.push(cap(o.pets_allowed) + ".");
      if (o.viewing_slot) bits.push(`Viewing ${o.viewing_slot}.`);
      // Whatever the renter asked us to ask, in the agent's own answer.
      for (const [k, v] of Object.entries(o.answers ?? {})) bits.push(`${cap(k)}: ${v}.`);
      if (!bits.length && o.available) bits.push("Available now.");
      return bits.join(" ");
    }
  }
}

const cap = (s: string) => (s ? s[0].toUpperCase() + s.slice(1) : s);

/* ── the criteria chips: the renter's profile, updating live ─────────────── */

export type Criterion = { key: string; label: string };

/**
 * The profile as the page shows it, in the order the renter would have said it.
 * Derived from preferences — the voice layer writes those, so a chip appearing
 * here means the agent genuinely heard it.
 */
export function criteriaOf(p: SessionState["preferences"]): Criterion[] {
  const out: Criterion[] = [];
  if (p.beds != null) {
    out.push({ key: `beds:${p.beds}`, label: p.beds === 0 ? "Studio" : `${p.beds} bed` });
  }
  if (p.baths != null) out.push({ key: `baths:${p.baths}`, label: `${p.baths} bath` });
  if (p.max_rent) out.push({ key: `rent:${p.max_rent}`, label: `Under ${money(p.max_rent)}` });
  for (const a of p.areas ?? []) out.push({ key: `area:${a}`, label: a });
  if (p.pets) out.push({ key: `pets:${p.pets}`, label: cap(p.pets) });
  if (p.parking) out.push({ key: "parking", label: "Parking" });
  for (const q of p.priority_order ?? []) {
    out.push({ key: `pri:${q}`, label: `${cap(q)} matters most` });
  }
  return out;
}

/* ── phase, and the one line at the top ──────────────────────────────────── */

export type Phase = "waiting" | "listening" | "calling" | "verified" | "emailed";

export function phaseOf(s: SessionState): Phase {
  if (!s.listings.length) return "waiting";
  if (s.listings.some((l) => l.status === "calling")) return "calling";
  // Only a call that came back with something counts as verified. A session
  // where every line went to voicemail has verified nothing.
  if (s.listings.some((l) => l.outcome && CONFIRMED.includes(l.status))) return "verified";
  if (s.listings.some((l) => l.status === "no_answer")) return "emailed";
  return "listening";
}

/** Statuses that mean a human actually told us something. */
export const CONFIRMED: CallStatus[] = ["verified", "booked", "dead"];

// Sentence case, and nothing the page can't back up — no "just now".
export const HEADER_STATUS: Record<Phase, string> = {
  waiting: "Connecting",
  listening: "Listening",
  calling: "Calling agents",
  verified: "Verified by phone",
  emailed: "No answer · draft ready",
};

/** Which listings the renter may still send us out to call. */
export const isSelectable = (s: CallStatus) => s === "pending" || s === "verified";
