"use client";

import { money } from "@/lib/present";
import type { Card } from "@/lib/types";

/**
 * The verdict: what the calls changed, in the agent's own words.
 * `agent_says` is written by the voice layer, so this card is a rendering of
 * something the renter also heard — not a summary the page invented.
 */
export function Verdict({ says }: { says: string }) {
  if (!says) return null;
  return (
    <section
      className="r-in mx-[14px] mt-4 rounded-[16px] p-[14px] text-white"
      style={{ background: "var(--color-ink)" }}
      aria-label="Shortlist, rewritten"
    >
      <p className="text-[10.5px] font-semibold uppercase tracking-[.08em]" style={{ color: "rgba(255,255,255,.5)" }}>
        Shortlist, rewritten
      </p>
      <p className="mt-2 text-[14px] leading-[1.5]">{says}</p>
      <p className="mt-2 text-[11.5px]" style={{ color: "rgba(255,255,255,.55)" }}>
        Every reason above came from an agent who answered a phone in the last few minutes.
      </p>
    </section>
  );
}

/**
 * Nobody picked up, so the agent wrote instead. The draft is shown in full —
 * nothing the agent sends on the renter's behalf is hidden behind a tap.
 */
export function EmailCard({
  card,
  onSend,
  state,
}: {
  card: Card;
  onSend: (id: string) => void;
  state: "idle" | "sending" | "sent" | "failed";
}) {
  const [subject, body] = splitDraft(card.email_draft);

  return (
    <section
      className="r-in mx-[14px] mt-4 rounded-[16px] p-[14px]"
      style={{ border: "1px solid var(--hair-card)", background: "var(--color-warm)" }}
      aria-label={`No answer at ${card.address}`}
    >
      <p className="text-[10.5px] font-semibold uppercase tracking-[.08em]" style={{ color: "var(--color-warn)" }}>
        No answer{card.outcome?.source ? ` · ${card.outcome.source}` : ""}
      </p>
      <p className="mt-2 text-[13px] leading-[1.5]">
        {card.address} went to voicemail, so we drafted an email instead.
      </p>

      <div
        className="mt-[10px] rounded-[10px] bg-surface p-[11px]"
        style={{ border: "1px solid var(--hair-card)" }}
      >
        <p className="truncate font-mono text-[10.5px] text-faint">To: {card.agent_name}</p>
        {subject && <p className="truncate font-mono text-[10.5px] text-faint">Re: {subject}</p>}
        <p className="mt-2 text-[11.5px] leading-[1.5]">{body}</p>
      </div>

      <div className="mt-3 flex items-center gap-3">
        <button
          type="button"
          onClick={() => onSend(card.listing_id)}
          disabled={state === "sending" || state === "sent"}
          className="rounded-[12px] px-4 py-[10px] text-[13px] font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-40"
          style={{ background: "var(--color-accent)" }}
        >
          {state === "sending" ? "Sending…" : state === "sent" ? "Sent" : "Send it"}
        </button>
        {state === "failed" && (
          <span className="text-[11.5px]" style={{ color: "var(--color-warn)" }}>
            Couldn&rsquo;t send — the draft is kept.
          </span>
        )}
        {state === "sent" && (
          <span className="text-[11.5px] text-muted">
            You&rsquo;ll get a text when they reply.
          </span>
        )}
      </div>
    </section>
  );
}

/** Drafts arrive as "Subject: …\n\nBody". Show them as two things, not one blob. */
function splitDraft(draft: string | null | undefined): [string, string] {
  if (!draft) return ["", ""];
  const [head, ...rest] = draft.split("\n\n");
  if (!rest.length) return ["", draft];
  return [head.replace(/^Subject:\s*/i, ""), rest.join("\n\n")];
}

/** Exported for the kit. */
export { money };
