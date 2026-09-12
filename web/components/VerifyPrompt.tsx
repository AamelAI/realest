"use client";

const ASKS = [
  "Still available?",
  "Total monthly cost",
  "Pet restrictions",
  "Earliest viewing",
] as const;

export const DEFAULT_ASKS: string[] = ASKS.slice(0, 3);
/** Used to tell our own canned chips apart from something the renter said. */
export const ALL_ASKS: string[] = [...ASKS];

/**
 * The approval gate. Voice asked "anything else you want me to ask?"; this is
 * where the renter answers — tapping three boxes is far more reliable than
 * parsing "the first and the third" out of a phone call.
 */
export function VerifyPrompt({
  count,
  asks,
  onToggleAsk,
  spokenAsk,
  onCall,
  sending,
  failed = false,
}: {
  count: number;
  asks: string[];
  onToggleAsk: (a: string) => void;
  /** what the renter said out loud, transcribed by the voice layer */
  spokenAsk: string;
  onCall: () => void;
  sending: boolean;
  /** the last attempt to start calls did not reach the backend */
  failed?: boolean;
}) {
  return (
    <section
      className="r-in mx-[14px] mt-4 rounded-[16px] p-[14px]"
      style={{ border: "1.5px solid var(--color-accent)", background: "var(--color-tint)" }}
      aria-labelledby="verify-title"
    >
      <h2 id="verify-title" className="text-[14px] font-semibold leading-[1.4]">
        Listings go stale fast. Want me to call and check they&rsquo;re real?
      </h2>
      <p className="mt-1 text-[11.5px] text-muted">
        {count} selected · tap a listing to change
      </p>

      <p className="mt-[13px] text-[10.5px] font-semibold uppercase tracking-[.08em] text-faint">
        Anything else you want me to ask?
      </p>

      <div className="mt-2 flex flex-wrap gap-[6px]">
        {ASKS.map((a) => {
          const on = asks.includes(a);
          return (
            <button
              key={a}
              type="button"
              aria-pressed={on}
              onClick={() => onToggleAsk(a)}
              className="rounded-full px-[10px] py-[5px] text-[11px] font-medium transition-colors"
              style={{
                border: `1px solid ${on ? "var(--color-accent)" : "rgba(20,22,26,.15)"}`,
                background: on ? "var(--color-accent)" : "#fff",
                color: on ? "#fff" : "var(--color-muted)",
              }}
            >
              {a}
            </button>
          );
        })}
      </div>

      {spokenAsk && (
        <p
          className="mt-[10px] rounded-[10px] bg-surface px-3 py-[10px] text-[12px] leading-[1.45]"
          style={{ border: "1px solid var(--accent-25)" }}
        >
          {spokenAsk}
        </p>
      )}

      <button
        type="button"
        onClick={onCall}
        disabled={sending || count === 0}
        className="mt-[14px] w-full rounded-[12px] py-[13px] text-[14px] font-semibold text-white transition-opacity hover:opacity-90 active:opacity-80 disabled:opacity-40"
        style={{ background: "var(--color-accent)" }}
      >
        {sending
          ? "Dialling…"
          : count === 0
            ? "Pick a listing to call"
            : `Call ${count} agent${count === 1 ? "" : "s"} now`}
      </button>

      {failed && (
        <p className="mt-2 text-[11.5px]" style={{ color: "var(--color-warn)" }}>
          That didn&rsquo;t reach the line. Your picks are still here — try again, or just
          tell the agent out loud.
        </p>
      )}
    </section>
  );
}
