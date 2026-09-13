"use client";

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  AnimatePresence,
  motion,
  useAnimationControls,
  useDragControls,
  useReducedMotion,
  type PanInfo,
} from "framer-motion";
import { Money } from "./Money";
import { statusLineOf, factsOf } from "@/lib/present";
import { clock } from "@/lib/useCallTimers";
import type { Card } from "@/lib/types";

/**
 * One listing, opened.
 *
 * The sheet grows out of the card that was tapped — without ever scaling.
 * Scaling a sheet squashes and stretches the photos inside it mid-flight.
 * Instead the sheet stays at its real size and is revealed through a window (a
 * clip) that starts as the card's exact rectangle and springs open. Closing is
 * instant.
 *
 * Glass is kept where it belongs: on the layer floating above the page (the
 * scrim, and the sheet's own top bar as content scrolls beneath it). The
 * content itself sits on an opaque surface, so nothing written here is ever
 * harder to read than it needs to be.
 */

/** A gentle overshoot on open — the renter asked for this, so it can bounce. */
const OPEN = { type: "spring", stiffness: 380, damping: 30, mass: 0.9 } as const;

export function DetailSheet({
  card,
  rank,
  originRect,
  selectable,
  selected,
  onToggle,
  onClosed,
  maxRent,
  seconds,
}: {
  card: Card | null;
  rank: number;
  /** where the tapped card was on screen when it opened */
  originRect: DOMRect | null;
  /** the listing can be added to the next round of calls */
  selectable: boolean;
  selected: boolean;
  onToggle: (id: string) => void;
  onClosed: () => void;
  maxRent?: number | null;
  seconds?: number;
}) {
  return (
    <AnimatePresence>
      {card && (
        <Sheet
          key={card.listing_id}
          card={card}
          rank={rank}
          originRect={originRect}
          selectable={selectable}
          selected={selected}
          onToggle={onToggle}
          onClosed={onClosed}
          maxRent={maxRent}
          seconds={seconds}
        />
      )}
    </AnimatePresence>
  );
}

function Sheet({
  card, rank, originRect, selectable, selected, onToggle, onClosed, maxRent, seconds,
}: {
  card: Card;
  rank: number;
  originRect: DOMRect | null;
  selectable: boolean;
  selected: boolean;
  onToggle: (id: string) => void;
  onClosed: () => void;
  maxRent?: number | null;
  seconds?: number;
}) {
  const id = card.listing_id;
  const sheet = useRef<HTMLDivElement>(null);
  const controls = useAnimationControls();
  const content = useAnimationControls();
  const drag = useDragControls();
  const reduce = useReducedMotion();
  const [closing, setClosing] = useState(false);
  const [glass, setGlass] = useState(true);

  /**
   * The window onto the full-size sheet that exactly covers a rectangle: shift
   * the sheet so its top meets the rectangle's top, then clip it to the
   * rectangle's size and corner radius. Every value is a plain number, so the
   * spring interpolates the clip smoothly.
   */
  const windowOn = useCallback((rect: DOMRect | null) => {
    const el = sheet.current;
    if (!el || !rect) return null;
    const box = el.getBoundingClientRect();
    const y = rect.top - box.top;
    const right = Math.max(0, box.right - rect.right);
    const left = Math.max(0, rect.left - box.left);
    const bottom = Math.max(0, box.height - rect.height);
    return { y, clipPath: `inset(0px ${right}px ${bottom}px ${left}px round 16px 16px 16px 16px)` };
  }, []);

  /** The sheet at rest: unclipped, with its own corners. */
  const rest = () => {
    const wide = window.matchMedia("(min-width: 640px)").matches;
    return {
      y: 0,
      clipPath: `inset(0px 0px 0px 0px round 24px 24px ${wide ? 24 : 0}px ${wide ? 24 : 0}px)`,
    };
  };

  // Open: the window starts as the card and springs open; content settles in
  // once there is room for it.
  useLayoutEffect(() => {
    setGlass(typeof CSS !== "undefined" && CSS.supports("backdrop-filter", "blur(1px)"));
    const from = reduce ? null : windowOn(originRect);
    if (from) {
      controls.set({ ...from, opacity: 1 });
      void controls.start({ ...rest(), transition: OPEN });
    } else {
      controls.set({ ...rest(), opacity: 0 });
      void controls.start({ opacity: 1, transition: { duration: 0.2 } });
    }
    void content.start("shown");
    sheet.current?.focus({ preventScroll: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Closing is instant: the sheet and its scrim go at once, and focus returns
  // to the card that opened it.
  const close = useCallback(() => {
    if (closing) return;
    setClosing(true);
    onClosed();
    document
      .querySelector<HTMLElement>(`[data-listing-id="${id}"] [data-open]`)
      ?.focus({ preventScroll: true });
  }, [closing, id, onClosed]);

  // Escape, browser back, and a page that can't scroll behind the sheet.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && close();
    const onPop = () => close();
    window.addEventListener("keydown", onKey);
    window.addEventListener("popstate", onPop);
    history.pushState({ sheet: id }, "");
    const { overflow } = document.body.style;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("popstate", onPop);
      document.body.style.overflow = overflow;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** Closing from the page itself steps back through the history entry we added. */
  const dismiss = () => {
    if (history.state?.sheet === id) history.back();
    else close();
  };

  const onDragEnd = (_: unknown, info: PanInfo) => {
    if (info.offset.y > 110 || info.velocity.y > 650) dismiss();
    else void controls.start({ y: 0, transition: OPEN });
  };

  const status = statusLineOf(card);
  const facts = factsOf(card, maxRent);
  const callFacts = facts.filter((f) => f.kind !== "listed");
  const photos = (card.photos?.length ? card.photos : [card.photo_url]).filter(Boolean);
  const meta = [
    `#${rank + 1}`,
    `${card.beds} bed`,
    `${card.baths} bath`,
    card.sqft ? `${card.sqft} ft²` : "",
    card.property_type,
    card.neighbourhood,
  ].filter(Boolean);

  return (
    <>
      <motion.div
        aria-hidden
        className="fixed inset-0 z-40"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0, transition: { duration: 0 } }}
        transition={{ duration: 0.28, ease: [0.23, 1, 0.32, 1] }}
        onClick={dismiss}
        style={{
          background: glass ? "rgba(251, 250, 249, 0.55)" : "rgba(251, 250, 249, 0.92)",
          backdropFilter: glass ? "blur(14px) saturate(140%)" : undefined,
          WebkitBackdropFilter: glass ? "blur(14px) saturate(140%)" : undefined,
        }}
      />

      <motion.div
        ref={sheet}
        role="dialog"
        aria-modal="true"
        aria-labelledby={`sheet-title-${id}`}
        tabIndex={-1}
        className="fixed inset-x-0 bottom-0 z-50 mx-auto flex max-h-[86dvh] w-full max-w-[560px] flex-col overflow-hidden bg-surface outline-none sm:bottom-auto sm:top-[6vh] sm:max-h-[88vh]"
        style={{
          // A hairline drawn inside the clip; an outer shadow would be clipped away.
          boxShadow: "inset 0 0 0 1px var(--color-line)",
          willChange: "clip-path, transform",
        }}
        initial={false}
        animate={controls}
        drag="y"
        dragListener={false}
        dragControls={drag}
        dragConstraints={{ top: 0, bottom: 0 }}
        dragElastic={{ top: 0.04, bottom: 0.7 }}
        onDragEnd={onDragEnd}
      >
        {/* The floating bar: frosted, so the photos read as scrolling under it. */}
        <div
          className="absolute inset-x-0 top-0 z-10 flex h-[60px] items-center justify-center px-4"
          onPointerDown={(e) => drag.start(e)}
          style={{
            touchAction: "none",
            background: glass ? "rgba(255, 255, 255, 0.68)" : "rgba(255, 255, 255, 0.96)",
            backdropFilter: glass ? "blur(20px) saturate(160%)" : undefined,
            WebkitBackdropFilter: glass ? "blur(20px) saturate(160%)" : undefined,
            borderBottom: "1px solid var(--color-hair)",
          }}
        >
          <span aria-hidden className="mx-auto h-1 w-9 rounded-full" style={{ background: "var(--color-line)" }} />
          <button
            type="button"
            onClick={dismiss}
            aria-label="Close"
            className="absolute right-3 top-1/2 flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full"
          >
            <span
              aria-hidden
              className="flex h-8 w-8 items-center justify-center rounded-full transition-transform duration-150 active:scale-90"
              style={{ background: "rgba(26, 24, 21, 0.07)" }}
            >
              <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" aria-hidden>
                <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
              </svg>
            </span>
          </button>
        </div>

        <motion.div
          className="overflow-y-auto overscroll-contain pb-[max(20px,env(safe-area-inset-bottom))] pt-[68px]"
          initial="hidden"
          animate={content}
          variants={{ shown: { transition: { delayChildren: reduce ? 0 : 0.12, staggerChildren: reduce ? 0 : 0.04 } } }}
        >
          {/* photos */}
          <Reveal>
            <div className="flex snap-x snap-mandatory gap-2 overflow-x-auto px-4 [scrollbar-width:none]">
              {photos.map((src, i) => (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  key={src + i}
                  src={src}
                  alt={i === 0 ? `Photo of ${card.address}` : ""}
                  className={`aspect-[4/3] shrink-0 snap-center rounded-[16px] object-cover ${
                    photos.length > 1 ? "w-[86%]" : "w-full"
                  }`}
                  style={{ background: "var(--color-press)" }}
                />
              ))}
            </div>
          </Reveal>

          {/* identity */}
          <Reveal className="px-5 pt-5">
            <h2 id={`sheet-title-${id}`} className="text-rent font-strong">{card.address}</h2>
            <p className="mt-1 text-support text-ink-2">{meta.join(" · ")}</p>
          </Reveal>

          {/* the money, and where it stands */}
          <Reveal className="flex items-end justify-between gap-4 px-5 pt-5">
            <Money card={card} lead maxRent={maxRent} />
            <div className="min-w-0 text-right">
              <p className="flex items-center justify-end gap-1.5 text-support font-label" style={{ color: status.tone }}>
                <span aria-hidden className="inline-block h-[7px] w-[7px] rounded-full" style={{ background: status.dot }} />
                {status.word}
              </p>
              {(status.detail || (status.clock && seconds !== undefined)) && (
                <p className="text-meta text-ink-3">
                  {status.detail}
                  {status.clock && seconds !== undefined && <span className="font-mono tnum"> · {clock(seconds)}</span>}
                </p>
              )}
            </div>
          </Reveal>

          {/* what a human said */}
          <Reveal className="mx-5 mt-6 border-t pt-4" style={{ borderColor: "var(--color-hair)" }}>
            <h3 className="text-support font-strong">What the agent said</h3>
            {card.outcome ? (
              <>
                {callFacts.length > 0 ? (
                  <ul className="mt-2 space-y-1.5">
                    {callFacts.map((f, i) => (
                      <li key={i} className="flex gap-2.5 text-fact">
                        <span
                          aria-hidden
                          className="mt-[9px] inline-block h-[5px] w-[5px] shrink-0 rounded-full"
                          style={{ background: f.kind === "conflict" ? "var(--color-dead)" : "var(--color-ink)" }}
                        />
                        <span style={{ color: f.kind === "conflict" ? "var(--color-dead)" : undefined }}>{f.text}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-fact text-ink-2">
                    {card.status === "dead" ? "It's already leased." : "Nothing beyond what's above."}
                  </p>
                )}
                {card.outcome.source && (
                  <p className="mt-2 text-meta text-ink-3">{card.outcome.source}</p>
                )}
                {card.outcome.raw_transcript && <Transcript text={card.outcome.raw_transcript} />}
              </>
            ) : card.status === "calling" ? (
              <p className="mt-2 text-fact text-ink-2">On the phone with {card.agent_name || "the agent"} now.</p>
            ) : card.status === "no_answer" ? (
              <p className="mt-2 text-fact text-ink-2">No answer. A draft email is ready below the list.</p>
            ) : (
              <p className="mt-2 text-fact text-ink-2">Not checked yet — add it to the calls and I&rsquo;ll ask.</p>
            )}
          </Reveal>

          {/* what the listing claims */}
          <Reveal className="mx-5 mt-6 border-t pt-4" style={{ borderColor: "var(--color-hair)" }}>
            <h3 className="text-support font-strong">From the listing</h3>
            <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-support">
              <dt className="text-ink-3">Parking</dt>
              <dd className="text-ink-2">{card.parking_included ? "Included" : "Not mentioned"}</dd>
              <dt className="text-ink-3">Pets</dt>
              <dd className="text-ink-2">{card.pets ? cap(card.pets) : "Not mentioned"}</dd>
              {card.amenities.length > 0 && (
                <>
                  <dt className="text-ink-3">Amenities</dt>
                  <dd className="text-ink-2">{card.amenities.map(cap).join(", ")}</dd>
                </>
              )}
              {card.transit_note && (
                <>
                  <dt className="text-ink-3">Transit</dt>
                  <dd className="text-ink-2">{card.transit_note}</dd>
                </>
              )}
            </dl>
          </Reveal>

          {/* actions */}
          <Reveal className="mx-5 mt-6 flex flex-col gap-2">
            {selectable && (
              <button
                type="button"
                onClick={() => onToggle(id)}
                aria-pressed={selected}
                className="h-[52px] w-full rounded-control text-fact font-label transition-[transform,background-color,color] duration-150 active:scale-[.98]"
                style={{
                  background: selected ? "var(--color-surface)" : "var(--color-ink)",
                  color: selected ? "var(--color-ink)" : "#fff",
                  boxShadow: selected ? "inset 0 0 0 1.5px var(--color-ink)" : "none",
                }}
              >
                {selected ? "Added to calls — tap to remove" : "Add to calls"}
              </button>
            )}
            {card.source_url && (
              <a
                href={card.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex h-11 items-center justify-center text-support font-label text-ink-2 underline decoration-[1px] underline-offset-4"
              >
                View the original listing
              </a>
            )}
          </Reveal>
        </motion.div>
      </motion.div>
    </>
  );
}

/** Each section settles in after the sheet has grown, a beat apart. */
function Reveal({
  children, className, style,
}: {
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <motion.div
      className={className}
      style={style}
      variants={{
        hidden: { opacity: 0, y: 8 },
        shown: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 420, damping: 34 } },
      }}
    >
      {children}
    </motion.div>
  );
}

/**
 * The call, verbatim. An excerpt first; the rest on request. Never paraphrased —
 * this is the evidence everything above it rests on.
 */
function Transcript({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  const long = text.length > 280;
  return (
    <div className="mt-3 rounded-control p-3" style={{ background: "var(--color-ground)" }}>
      <p className="whitespace-pre-line text-support text-ink-2">
        {open || !long ? text : `${text.slice(0, 280).trimEnd()}…`}
      </p>
      {long && (
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="mt-2 min-h-[36px] text-support font-label text-ink underline decoration-[1px] underline-offset-4"
        >
          {open ? "Show less" : "Read the full call"}
        </button>
      )}
    </div>
  );
}

const cap = (s: string) => (s ? s[0].toUpperCase() + s.slice(1) : s);

