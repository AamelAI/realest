// The adapter: our live SessionState -> the view model the design handoff
// specifies. Everything here is derived from what a human actually told us.
//
// The rule that governs this file: if the server does not know it, the page
// does not show it. The product's whole claim is that these facts came off a
// phone call, so a plausible-looking invented status would be the one bug that
// matters.

import type { Card, CallStatus, SessionState } from "./types";

export const money = (n: number) => "$" + n.toLocaleString("en-CA");

/* ── status ──────────────────────────────────────────────────────────────── */

export type Status = {
  /** the pill label */
  label: string;
  /** the one-line form used in dense rows and the calls panel */
  short: string;
  fg: string;
  bg: string;
  dot: string;
  dead: boolean;
  /** verified-real gets a green card edge */
  proven: boolean;
};

const REAL = "var(--color-real)", REAL_BG = "var(--color-real-bg)";
const WARN = "var(--color-warn)", WARN_BG = "var(--color-warn-bg)";
const DEAD = "var(--color-dead)", DEAD_BG = "var(--color-dead-bg)";
const NONE = "var(--color-none)", NONE_BG = "var(--color-none-bg)";
const ACCENT = "var(--color-accent)";

export function statusOf(card: Card, starting = false): Status {
  const o = card.outcome;
  // The renter tapped call and the server hasn't reflected it yet. This states
  // what the renter did, not what the phone network is doing — so it is
  // "Starting call", never an invented "Dialing" or "Ringing".
  if (starting && isSelectable(card.status)) {
    return {
      label: "Starting", short: "Starting call…",
      fg: ACCENT, bg: "var(--color-tint)", dot: ACCENT, dead: false, proven: false,
    };
  }
  switch (card.status) {
    case "booked":
      return {
        label: "Booked", short: o?.viewing_slot ? `Booked · ${o.viewing_slot}` : "Booked",
        fg: REAL, bg: REAL_BG, dot: REAL, dead: false, proven: true,
      };
    case "verified":
      return {
        label: "Real", short: o?.pets_allowed ? `Real · ${o.pets_allowed}` : "Real",
        fg: REAL, bg: REAL_BG, dot: REAL, dead: false, proven: true,
      };
    case "dead":
      return {
        label: "Leased", short: "Leased — still posted",
        fg: DEAD, bg: DEAD_BG, dot: DEAD, dead: true, proven: false,
      };
    case "no_answer":
      return {
        label: "Emailed", short: "No answer · emailed",
        fg: WARN, bg: WARN_BG, dot: WARN, dead: false, proven: false,
      };
    case "calling":
      return {
        label: "Calling", short: "On the phone now",
        fg: ACCENT, bg: "var(--color-tint)", dot: ACCENT, dead: false, proven: false,
      };
    default:
      return {
        label: "Not checked", short: "Not checked",
        fg: NONE, bg: NONE_BG, dot: "var(--color-dim)", dead: false, proven: false,
      };
  }
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
      // Terse on purpose: the card is a fixed 144px and the note is clamped to
      // three lines, so anything verbose here pushes the provenance off the
      // card — and provenance is the half that makes this evidence.
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

/** Old figure struck, real figure beside it — the correction is the product. */
export function rentOf(card: Card): { now: string; was: string } {
  const real = card.outcome?.real_rent ?? null;
  return real !== null && real !== card.rent
    ? { now: money(real), was: money(card.rent) }
    : { now: money(card.rent), was: "" };
}

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

export const HEADER_STATUS: Record<Phase, string> = {
  waiting: "connecting",
  listening: "listening — page updates live",
  calling: "calling agents",
  verified: "verified just now",
  emailed: "no answer — emailed instead",
};

/** Which listings the renter may still send us out to call. */
export const isSelectable = (s: CallStatus) => s === "pending" || s === "verified";
