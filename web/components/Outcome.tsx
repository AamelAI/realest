"use client";

import type { Card } from "@/lib/types";

/**
 * The agent's latest line, captioned. On a muted screen or a glance mid-call,
 * this is what makes the voice and the page read as one conversation. It is a
 * rendering of something the renter also heard — never a summary the page
 * wrote for itself.
 */
export function Caption({ says }: { says: string }) {
  if (!says) return null;
  return (
    <div className="mx-auto max-w-[820px] px-4 pt-3" aria-live="polite">
      <p
        key={says}
        className="r-in line-clamp-2 text-fact text-ink"
        style={{ animationDelay: "calc(var(--intro-on, 0) * 220ms)" }}
      >
        <span className="text-ink-3">Realest: </span>
        {says}
      </p>
    </div>
  );
}

/**
 * Nobody picked up, so the agent drafted an email. Drafts only: the page never
 * claims to have sent anything. The whole draft is visible, paragraph breaks
 * intact — nothing written in the renter's name is hidden behind a tap.
 */
export function EmailCard({ card }: { card: Card }) {
  const [subject, body] = splitDraft(card.email_draft);
  if (!body && !subject) return null;

  return (
    <section
      className="r-in mx-4 mt-4 rounded-card border bg-surface p-4"
      style={{ borderColor: "var(--color-line)", animationDelay: "calc(var(--intro-on, 0) * 620ms)" }}
      aria-label={`Email draft for ${card.address}`}
    >
      <h2 className="text-support font-strong">
        No answer{card.agent_name ? ` from ${card.agent_name}` : ""} · draft ready
      </h2>
      <p className="mt-0.5 truncate text-meta text-ink-3">{card.address}</p>

      <div
        className="mt-3 rounded-control border p-3"
        style={{ borderColor: "var(--color-hair)", background: "var(--color-ground)" }}
      >
        {subject && <p className="text-support font-label">{subject}</p>}
        <p className="mt-1 whitespace-pre-line text-support text-ink-2">{body}</p>
      </div>

      <p className="mt-2 text-meta text-ink-3">Drafted, not sent.</p>
    </section>
  );
}

/** Drafts arrive as "Subject: …\n\nBody". Show them as two things, not one blob. */
function splitDraft(draft: string | null | undefined): [string, string] {
  if (!draft) return ["", ""];
  const [head, ...rest] = draft.split("\n\n");
  // Only a line that says it's a subject is one. A draft that opens straight
  // into "Hi Marco, …" keeps its first paragraph as body.
  if (!rest.length || !/^Subject:/i.test(head)) return ["", draft];
  return [head.replace(/^Subject:\s*/i, ""), rest.join("\n\n")];
}
