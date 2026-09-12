"use client";

import type { Criterion } from "@/lib/present";

/**
 * The sticky header. The renter's profile lives here and grows while they talk
 * — a chip appearing is the visible proof the agent heard something new.
 */
export function Header({
  criteria,
  fresh,
  status,
  count,
  live,
}: {
  criteria: Criterion[];
  /** keys heard since this page opened — tinted, so the new one is findable */
  fresh: Set<string>;
  status: string;
  count: number;
  live: boolean;
}) {
  return (
    <header
      className="sticky top-0 z-[5] border-b px-[18px] pb-3 pt-[max(12px,env(safe-area-inset-top))] backdrop-blur-[10px]"
      style={{ background: "rgba(255,255,255,.94)", borderColor: "var(--hair-head)" }}
    >
      <div className="mx-auto max-w-[820px]">
        <div className="flex items-center gap-2">
          <span className="text-[16px] font-bold tracking-[-0.02em]">Realest</span>

          {live && (
            <span
              aria-hidden
              className="r-pulse ml-1 inline-block h-[6px] w-[6px] shrink-0 rounded-full"
              style={{ background: "var(--color-real)" }}
            />
          )}
          <span className="min-w-0 truncate text-[11.5px] text-muted">{status}</span>

          <span className="ml-auto shrink-0 font-mono text-[11px] tnum text-faint">
            {count > 0 ? `${count} listing${count === 1 ? "" : "s"}` : ""}
          </span>
        </div>

        {criteria.length > 0 && (
          <ul className="mt-[10px] flex flex-wrap gap-[5px]" aria-label="What the agent has heard">
            {criteria.map((c) => {
              const isNew = fresh.has(c.key);
              return (
                <li
                  key={c.key}
                  className="r-in rounded-full px-[9px] py-[4px] text-[11px] font-medium"
                  style={{
                    border: `1px solid ${isNew ? "var(--accent-35)" : "rgba(20,22,26,.13)"}`,
                    background: isNew ? "var(--color-tint)" : "#fff",
                    color: isNew ? "var(--color-accent)" : "var(--color-muted)",
                  }}
                >
                  {c.label}
                  {isNew && <span className="sr-only"> (just heard)</span>}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </header>
  );
}
