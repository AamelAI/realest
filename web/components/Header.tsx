"use client";

import type { Criterion } from "@/lib/present";

/**
 * The top of the page. Only the wordmark row is sticky — a phone held mid-call
 * has little height to spare, so the renter's profile (the chips) scrolls with
 * the content instead of eating the viewport.
 *
 * A chip appearing is the visible proof the agent heard something new.
 */
export function Header({
  criteria,
  fresh,
  status,
  count,
  live,
  pulse,
}: {
  criteria: Criterion[];
  /** keys heard since this page opened — shown in ink, so the new one is findable */
  fresh: Set<string>;
  status: string;
  count: number;
  /** the connection is up and a session exists — show the dot */
  live: boolean;
  /** animate it. False while calls are live, so only one heartbeat is on screen */
  pulse: boolean;
}) {
  return (
    <>
      <header
        className="sticky top-0 z-[5] border-b bg-ground"
        style={{
          borderColor: "var(--color-line)",
          paddingTop: "max(12px, env(safe-area-inset-top))",
        }}
      >
        <div className="mx-auto flex max-w-[820px] items-center gap-2 px-4 pb-3">
          <h1 className="text-[17px] leading-[22px] font-[560] tracking-[-0.02em]">Realest</h1>

          {live && (
            <span
              aria-hidden
              className={`${pulse ? "r-pulse" : ""} ml-0.5 inline-block h-[7px] w-[7px] shrink-0 rounded-full`}
              style={{ background: "var(--color-ink)" }}
            />
          )}
          <span className="min-w-0 truncate text-support text-ink-2">{status}</span>

          <span className="ml-auto shrink-0 text-support tnum text-ink-3">
            {count > 0 ? `${count} listing${count === 1 ? "" : "s"}` : ""}
          </span>
        </div>
      </header>

      {criteria.length > 0 && (
        <div className="mx-auto max-w-[820px] px-4 pt-3">
          <ul className="flex flex-wrap gap-1.5" aria-label="What the agent has heard">
            {criteria.map((c) => {
              const isNew = fresh.has(c.key);
              return (
                <li
                  key={c.key}
                  className="r-in rounded-full border bg-surface px-2.5 py-1 text-meta font-label"
                  style={{
                    borderColor: isNew ? "var(--color-ink)" : "var(--color-line)",
                    color: isNew ? "var(--color-ink)" : "var(--color-ink-2)",
                  }}
                >
                  {c.label}
                  {isNew && <span className="sr-only"> (just heard)</span>}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </>
  );
}
