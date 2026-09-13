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
 * The approval gate, written as a plan the renter can read in two seconds:
 * who will be called, and what they'll be asked. Approving is one tap, and the
 * button names exactly what it will do.
 */
export function VerifyPrompt({
  count,
  names,
  asks,
  onToggleAsk,
  spokenAsk,
  onCall,
  sending,
  failed = false,
}: {
  count: number;
  /** agent names for the chosen listings, in order — used only when unambiguous */
  names: string[];
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
      className="r-in mx-4 mt-6 rounded-card border bg-surface p-4"
      style={{ borderColor: "var(--color-line)", animationDelay: "calc(var(--intro-on, 0) * 560ms)" }}
      aria-labelledby="verify-title"
    >
      <h2 id="verify-title" className="text-fact font-strong">
        Want me to call and check they&rsquo;re real?
      </h2>
      <p className="mt-1 text-support text-ink-2">
        {count} chosen · tap a listing to change
      </p>

      <p className="mt-4 text-support text-ink-2">I&rsquo;ll ask about</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {ASKS.map((a) => {
          const on = asks.includes(a);
          return (
            <button
              key={a}
              type="button"
              aria-pressed={on}
              onClick={() => onToggleAsk(a)}
              className="min-h-[36px] rounded-full border px-3 text-meta font-label transition-colors duration-150"
              style={{
                borderColor: on ? "var(--color-ink)" : "var(--color-line)",
                color: on ? "var(--color-ink)" : "var(--color-ink-3)",
                boxShadow: on ? "inset 0 0 0 0.5px var(--color-ink)" : "none",
              }}
            >
              {a}
            </button>
          );
        })}
      </div>

      {spokenAsk && (
        <p className="mt-3 text-support text-ink-2">
          You also asked: <span className="text-ink">&ldquo;{spokenAsk}&rdquo;</span>
        </p>
      )}

      <button
        type="button"
        onClick={onCall}
        disabled={sending || count === 0}
        className="mt-4 h-[52px] w-full rounded-control bg-ink text-fact font-label text-white transition-[opacity,transform] duration-150 active:scale-[.98] disabled:opacity-40"
      >
        {sending ? "Starting calls…" : callLabel(count, names)}
      </button>

      {failed && (
        <p className="mt-2 text-support" style={{ color: "var(--color-dead)" }}>
          That didn&rsquo;t reach the line. Your picks are still here — try again, or tell the agent
          out loud.
        </p>
      )}
    </section>
  );
}

/**
 * "Call Nadia, Dana and Raj" — but only when that's unambiguous. Several
 * listings share an agent, so repeated or missing names fall back to a count.
 */
function callLabel(count: number, names: string[]): string {
  if (count === 0) return "Pick a listing to call";
  const clean = names.filter(Boolean);
  const unique = new Set(clean);
  if (clean.length === count && unique.size === count && count <= 3) {
    const list =
      count === 1 ? clean[0]
      : count === 2 ? `${clean[0]} and ${clean[1]}`
      : `${clean[0]}, ${clean[1]} and ${clean[2]}`;
    return `Call ${list}`;
  }
  return `Call ${count} agent${count === 1 ? "" : "s"}`;
}
