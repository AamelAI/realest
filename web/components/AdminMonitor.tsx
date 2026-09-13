"use client";

import {
  Fragment,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import type { AdminEvent, CallDetail, HistoryCall, LiveCall } from "@/lib/admin";

// The admin monitor. Styles live in app/admin/admin.css and are shared with
// server/static/admin.html (the FastAPI fallback). Keep the two in step.

const RAIL = ["init", "preferences", "start_calls", "outcome", "book"] as const;
const POLL_MS = 1200;
const STALE_MS = 4000;

type Tone = "good" | "bad" | "warn" | "live" | "quiet";
type Status = { label: string; tone: Tone };
type Turn = { role: string; text: string };
type Group = { sid: string; head: LiveCall | null; kids: LiveCall[]; last: number };

/* ── words for states ──────────────────────────────────────────────────── */

const LISTING: Record<string, Status> = {
  pending: { label: "Queued", tone: "quiet" },
  calling: { label: "On the call", tone: "live" },
  verified: { label: "Verified", tone: "good" },
  booked: { label: "Booked", tone: "good" },
  dead: { label: "Leased", tone: "bad" },
  no_answer: { label: "No answer", tone: "warn" },
};

const CONVERSATION: Record<string, Status> = {
  initiated: { label: "Ringing", tone: "live" },
  "in-progress": { label: "On the line", tone: "live" },
  processing: { label: "Processing", tone: "quiet" },
  done: { label: "Completed", tone: "quiet" },
  failed: { label: "Failed", tone: "bad" },
};

const SETTLED = new Set(["verified", "booked", "dead", "no_answer"]);

function liveStatus(c: LiveCall): Status {
  if (c.status === "in_flight") return { label: "Waiting on calls", tone: "live" };
  if (c.role === "listing" && LISTING[c.status]) return LISTING[c.status];
  if (c.el_status && CONVERSATION[c.el_status]) return CONVERSATION[c.el_status];
  return { label: "Open", tone: "quiet" };
}

function conversationStatus(status: string): Status {
  return CONVERSATION[status] ?? { label: status || "Unknown", tone: "quiet" };
}

function eventTone(status: string): Tone {
  const s = status.toLowerCase();
  if (s === "started") return "live";
  if (s === "ok" || s === "done") return "good";
  if (s === "failed" || s === "error") return "bad";
  return "quiet";
}

const roleName = (role: string) => (role === "listing" ? "Listing agent" : "Renter");

/* ── time ──────────────────────────────────────────────────────────────── */

const pad = (n: number) => String(n).padStart(2, "0");

function clock(unix: number): string {
  if (!unix) return "–";
  const d = new Date(unix * 1000);
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function day(unix: number): string {
  return unix ? new Date(unix * 1000).toLocaleDateString("en-CA", { month: "short", day: "numeric" }) : "";
}

function ago(unix: number, nowMs: number): string {
  if (!unix || !nowMs) return "";
  const s = Math.max(0, Math.round(nowMs / 1000 - unix));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

function length(secs: number | null): string {
  if (secs == null) return "";
  return `${Math.floor(secs / 60)}:${pad(Math.round(secs % 60))}`;
}

/* ── shaping the payloads ──────────────────────────────────────────────── */

const lastT = (c: LiveCall) => (c.events.length ? c.events[c.events.length - 1].t : 0);

/** One renter session per group, its listing calls beneath it. */
function groupSessions(calls: LiveCall[]): Group[] {
  const bySid = new Map<string, Group>();
  for (const c of calls) {
    const g = bySid.get(c.session_id) ?? { sid: c.session_id, head: null, kids: [], last: 0 };
    bySid.set(c.session_id, g);
    if (c.role !== "listing" && !g.head) g.head = c;
    else g.kids.push(c);
    g.last = Math.max(g.last, lastT(c));
  }
  const groups = [...bySid.values()];
  for (const g of groups) g.kids.sort((a, b) => a.listing_id.localeCompare(b.listing_id));
  return groups.sort((a, b) => b.last - a.last);
}

/** The renter row never records `outcome` itself; its listing calls do. */
function reached(head: LiveCall, kids: LiveCall[]): Set<string> {
  const hit = new Set(head.tools);
  if (kids.some((k) => k.tools.includes("outcome") || SETTLED.has(k.status))) hit.add("outcome");
  return hit;
}

/** flatten_transcript() writes "role: text" lines. */
function parseTranscript(text: string): Turn[] {
  const out: Turn[] = [];
  for (const line of (text || "").split("\n")) {
    const m = /^([a-z_]+):\s?(.*)$/i.exec(line);
    if (m) out.push({ role: m[1].toLowerCase(), text: m[2] });
    else if (line.trim() && out.length) out[out.length - 1].text += ` ${line.trim()}`;
    else if (line.trim()) out.push({ role: "", text: line.trim() });
  }
  return out;
}

function speaker(role: string, callRole: string): { who: string; us: boolean } {
  if (role === "agent" || role === "ai") return { who: "Realest", us: true };
  if (role === "user") return { who: callRole === "listing" ? "Leasing agent" : "Renter", us: false };
  return { who: role ? role[0].toUpperCase() + role.slice(1) : "", us: false };
}

function show(v: unknown): string {
  if (Array.isArray(v)) return v.length ? v.map(show).join(", ") : "none";
  if (v && typeof v === "object") return JSON.stringify(v);
  return String(v);
}

function fields(raw: string): [string, string][] | null {
  try {
    const v: unknown = JSON.parse(raw);
    if (v && typeof v === "object" && !Array.isArray(v)) {
      return Object.entries(v as Record<string, unknown>).map(([k, x]) => [k, show(x)]);
    }
  } catch {
    /* not JSON */
  }
  return null;
}

/** A tool result: what the agent was told to say, the rest as fields. */
function result(raw: string): { said: string; rest: [string, string][]; text: string } {
  const f = raw ? fields(raw) : null;
  if (!f) return { said: "", rest: [], text: raw };
  const said = f.find(([k]) => k === "speak")?.[1] ?? "";
  return { said, rest: f.filter(([k]) => k !== "speak"), text: "" };
}

/* ── small pieces ──────────────────────────────────────────────────────── */

function State({ status, mono = false }: { status: Status; mono?: boolean }) {
  return (
    <span className={`adm-state t-${status.tone}${mono ? " mono" : ""}`}>
      {status.tone === "live" ? <span className="adm-dot" aria-hidden /> : null}
      {status.label}
    </span>
  );
}

function Copy({ text }: { text: string }) {
  const [done, setDone] = useState(false);
  if (!text) return <>–</>;
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setDone(true);
      setTimeout(() => setDone(false), 1200);
    } catch {
      /* clipboard needs a secure context; the id is still selectable */
    }
  };
  return (
    <button type="button" className={`adm-copy${done ? " is-done" : ""}`} onClick={copy}>
      {text}
      <span className="note">{done ? "copied" : "copy"}</span>
    </button>
  );
}

function Rail({ hit, now, live }: { hit: Set<string>; now: string; live: boolean }) {
  return (
    <span className="adm-rail" aria-label={`Tools reached: ${[...hit].join(", ") || "none"}`}>
      {RAIL.map((step) => {
        const cls = [
          hit.has(step) ? "is-done" : "",
          step === now ? `is-now${live ? " t-live" : ""}` : "",
        ].filter(Boolean).join(" ");
        return (
          <span key={step} className={cls || undefined}>
            {step}
          </span>
        );
      })}
    </span>
  );
}

function Timeline({ events }: { events: AdminEvent[] }) {
  const started = new Map<string, number>();
  return (
    <ol className="adm-log">
      {events.map((ev, i) => {
        let took = "";
        if (ev.status === "started") started.set(ev.tool, ev.t);
        else if (ev.status === "done" && started.has(ev.tool)) {
          took = `after ${Math.round(ev.t - (started.get(ev.tool) ?? ev.t))}s`;
          started.delete(ev.tool);
        }
        const note = [ev.summary.replaceAll(",", ", "), took].filter(Boolean).join(" · ");
        return (
          <li key={`${ev.t}-${i}`} className="adm-ev">
            <time>{clock(ev.t)}</time>
            <span>
              <span className="tool">{ev.tool}</span>
              {note ? <span className="note">{note}</span> : null}
            </span>
            <span className={`adm-state t-${eventTone(ev.status)}`}>{ev.status}</span>
          </li>
        );
      })}
    </ol>
  );
}

function Turns({ turns, callRole }: { turns: Turn[]; callRole: string }) {
  return (
    <ol className="adm-turns">
      {turns.map((t, i) => {
        const s = speaker(t.role, callRole);
        return (
          <li key={i} className={`adm-turn${s.us ? " is-us" : ""}`}>
            <span className="who">{s.who}</span>
            <p>{t.text}</p>
          </li>
        );
      })}
    </ol>
  );
}

function KV({ rows }: { rows: [string, string][] }) {
  return (
    <dl className="adm-kv">
      {rows.map(([k, v]) => (
        <Fragment key={k}>
          <dt>{k}</dt>
          <dd>{v}</dd>
        </Fragment>
      ))}
    </dl>
  );
}

function ToolCall({ tool }: { tool: CallDetail["tools"][number] }) {
  const params = fields(tool.params);
  const out = result(tool.result);
  return (
    <li className="adm-toolcall">
      <div className="adm-toolcall-head">
        <span className="tool">{tool.name}</span>
        <State status={{ label: tool.error ? "error" : "ok", tone: tool.error ? "bad" : "good" }} mono />
      </div>
      {params && params.length ? (
        <KV rows={params} />
      ) : tool.params && tool.params !== "{}" && !params ? (
        <pre className="adm-raw">{tool.params}</pre>
      ) : null}
      {out.said ? <p className="adm-said">{out.said}</p> : null}
      {out.rest.length ? <KV rows={out.rest} /> : null}
      {out.text ? <pre className={`adm-raw${tool.error ? " t-bad" : ""}`}>{out.text}</pre> : null}
    </li>
  );
}

function PaneEmpty({ title, body }: { title: string; body: string }) {
  return (
    <div className="adm-empty">
      <b>{title}</b>
      {body}
    </div>
  );
}

/* ── the tape, for a live row ──────────────────────────────────────────── */

function LivePane({ row, kids, now }: { row: LiveCall; kids: LiveCall[]; now: number }) {
  const listing = row.role === "listing";
  const turns = parseTranscript(row.transcript);
  const last = lastT(row);
  return (
    <>
      <header className="adm-pane-head">
        <p className="kicker">
          <span>{listing ? "Listing agent call" : "Inbound renter call"}</span>
          <State status={liveStatus(row)} />
        </p>
        <h2>{listing ? row.summary || row.listing_id : `Session ${row.session_id}`}</h2>
        <dl className="adm-ids">
          <dt>Session</dt>
          <dd><Copy text={row.session_id} /></dd>
          {listing ? (
            <>
              <dt>Listing</dt>
              <dd>{row.listing_id}</dd>
            </>
          ) : null}
          <dt>Conversation</dt>
          <dd><Copy text={row.conversation_id} /></dd>
          <dt>Last activity</dt>
          <dd>{last ? `${clock(last)} · ${ago(last, now)}` : "–"}</dd>
        </dl>
      </header>

      {!listing && kids.length ? (
        <section className="adm-section">
          <h3>Listing calls <span className="num">{kids.length}</span></h3>
          <ul className="adm-calls">
            {kids.map((k) => (
              <li key={k.id}>
                <span>
                  {k.summary || k.listing_id}
                  <span className="mono">{k.listing_id}</span>
                </span>
                <State status={liveStatus(k)} />
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="adm-section">
        <h3>Timeline <span className="num">{row.events.length}</span></h3>
        {row.events.length ? (
          <Timeline events={row.events} />
        ) : (
          <p>No webhook has fired for this call yet.</p>
        )}
      </section>

      <section className="adm-section">
        <h3>Transcript <span className="num">{turns.length ? `${turns.length} turns` : ""}</span></h3>
        {turns.length ? (
          <Turns turns={turns} callRole={row.role} />
        ) : (
          <p>Nothing yet. ElevenLabs returns the transcript while the call runs and after it ends.</p>
        )}
      </section>
    </>
  );
}

/* ── the tape, for a past conversation ─────────────────────────────────── */

function HistoryPane({ id, detail, error, now }: {
  id: string;
  detail: CallDetail | null;
  error: string;
  now: number;
}) {
  if (!detail) {
    return (
      <>
        <header className="adm-pane-head">
          <p className="kicker"><span>Conversation</span></p>
          <h2 className="mono">{id}</h2>
        </header>
        <section className="adm-section">
          <p className={error ? "t-bad" : undefined}>{error || "Loading from ElevenLabs…"}</p>
        </section>
      </>
    );
  }
  const turns = detail.turns.length ? detail.turns : parseTranscript(detail.transcript);
  const direction = detail.direction && detail.direction !== "?" ? detail.direction : "";
  return (
    <>
      <header className="adm-pane-head">
        <p className="kicker">
          <span>{direction ? `${direction[0].toUpperCase()}${direction.slice(1)} call` : "Call"}</span>
          <State status={conversationStatus(detail.status)} />
        </p>
        <h2>{detail.role === "listing" ? "Listing agent call" : "Renter call"}</h2>
        <dl className="adm-ids">
          <dt>Conversation</dt>
          <dd><Copy text={detail.conversation_id} /></dd>
          <dt>Started</dt>
          <dd>
            {detail.started_at
              ? `${day(detail.started_at)}, ${clock(detail.started_at)} · ${ago(detail.started_at, now)}`
              : "–"}
          </dd>
          <dt>Length</dt>
          <dd>{length(detail.duration_secs) || "–"}</dd>
        </dl>
      </header>

      <section className="adm-section">
        <h3>Tool calls <span className="num">{detail.tools.length}</span></h3>
        {detail.tools.length ? (
          <ol className="adm-log">
            {detail.tools.map((tool, i) => (
              <ToolCall key={`${tool.name}-${i}`} tool={tool} />
            ))}
          </ol>
        ) : (
          <p>No tool calls in this conversation.</p>
        )}
      </section>

      <section className="adm-section">
        <h3>Transcript <span className="num">{turns.length ? `${turns.length} turns` : ""}</span></h3>
        {turns.length ? (
          <Turns turns={turns} callRole={detail.role} />
        ) : (
          <p>No transcript. The call may never have connected.</p>
        )}
      </section>
    </>
  );
}

/* ── ↑/↓ or j/k walk the list ─────────────────────────────────────────── */

function stepThrough(
  e: KeyboardEvent<HTMLElement>,
  ids: string[],
  current: string,
  select: (id: string) => void,
) {
  const down = e.key === "ArrowDown" || e.key === "j";
  const up = e.key === "ArrowUp" || e.key === "k";
  if (!down && !up) return;
  e.preventDefault();
  // Step from the focused row, not from state: a held arrow key fires faster
  // than React re-renders, and focus has already moved on each press.
  const from = (e.target as HTMLElement).closest("[data-id]")?.getAttribute("data-id") || current;
  const i = ids.indexOf(from);
  const next = ids[Math.min(ids.length - 1, Math.max(0, i + (down ? 1 : -1)))];
  if (!next) return;
  select(next);
  e.currentTarget.querySelector<HTMLElement>(`[data-id="${CSS.escape(next)}"]`)?.focus();
}

/* ── the page ──────────────────────────────────────────────────────────── */

export function AdminMonitor() {
  const [tab, setTab] = useState<"live" | "history">("live");
  const [live, setLive] = useState<LiveCall[]>([]);
  const [history, setHistory] = useState<HistoryCall[]>([]);
  const [histError, setHistError] = useState("");
  const [histLoadedAt, setHistLoadedAt] = useState(0);
  const [selectedLive, setSelectedLive] = useState("");
  const [selectedHist, setSelectedHist] = useState("");
  const [detail, setDetail] = useState<CallDetail | null>(null);
  const [detailError, setDetailError] = useState("");
  const [loadingHist, setLoadingHist] = useState(false);
  const [lastOk, setLastOk] = useState(0);
  const [failing, setFailing] = useState(false);
  const [now, setNow] = useState(0);
  const prev = useRef("");
  const histSel = useRef("");
  const pane = useRef<HTMLElement>(null);

  // One clock for every "12s ago" on the page. Starts after mount so the
  // server render never disagrees with the browser about the time.
  useEffect(() => {
    setNow(Date.now());
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (tab !== "live") return;
    let alive = true;
    const poll = async () => {
      // Each poll can fan out to ElevenLabs; don't spend that on a hidden tab.
      if (document.visibilityState === "hidden") return;
      try {
        const r = await fetch("/api/admin/live", { cache: "no-store" });
        if (!alive) return;
        if (!r.ok) {
          setFailing(true);
          return;
        }
        const data = (await r.json()) as { calls?: LiveCall[] };
        const calls = Array.isArray(data.calls) ? data.calls : [];
        setLastOk(Date.now());
        setFailing(false);
        const json = JSON.stringify(calls);
        if (json === prev.current) return;
        prev.current = json;
        setLive(calls);
      } catch {
        if (alive) setFailing(true); // keep the last good list on screen
      }
    };
    poll();
    const id = setInterval(poll, POLL_MS);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [tab]);

  const openHistory = useCallback(async (cid: string) => {
    histSel.current = cid;
    setSelectedHist(cid);
    setDetail(null);
    setDetailError("");
    try {
      const r = await fetch(`/api/admin/calls/${encodeURIComponent(cid)}`, { cache: "no-store" });
      if (!r.ok) {
        setDetailError(`ElevenLabs answered ${r.status} for this conversation.`);
        return;
      }
      setDetail((await r.json()) as CallDetail);
    } catch {
      setDetailError("Could not reach the backend.");
    }
  }, []);

  const loadHistory = useCallback(async () => {
    setLoadingHist(true);
    setHistError("");
    try {
      const r = await fetch("/api/admin/calls?limit=20", { cache: "no-store" });
      const data = (await r.json()) as { calls?: HistoryCall[]; error?: string };
      const calls = Array.isArray(data.calls) ? data.calls : [];
      setHistory(calls);
      setHistLoadedAt(Date.now());
      if (data.error) setHistError(data.error);
      // Open the newest conversation so the tape is never blank on arrival.
      if (calls.length && !histSel.current) void openHistory(calls[0].conversation_id);
    } catch {
      setHistError("Could not fetch calls.");
    } finally {
      setLoadingHist(false);
    }
  }, [openHistory]);

  useEffect(() => {
    if (tab === "history" && !histLoadedAt && !loadingHist) void loadHistory();
  }, [tab, histLoadedAt, loadingHist, loadHistory]);

  const groups = useMemo(() => groupSessions(live), [live]);
  const order = useMemo(
    () => groups.flatMap((g) => [...(g.head ? [g.head.id] : []), ...g.kids.map((k) => k.id)]),
    [groups],
  );

  // Never leave the tape empty when there is something to show.
  useEffect(() => {
    if (order.length && !order.includes(selectedLive)) setSelectedLive(order[0]);
  }, [order, selectedLive]);

  const reveal = () => {
    if (window.matchMedia("(max-width: 1023px)").matches) {
      pane.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  const listing = live.filter((c) => c.role === "listing");
  const count = (s: string) => listing.filter((c) => c.status === s).length;
  const allFigures: { n: number; label: string; tone?: Tone }[] = [
    { n: groups.length, label: groups.length === 1 ? "session" : "sessions" },
    { n: listing.length, label: listing.length === 1 ? "listing call" : "listing calls" },
    { n: count("calling"), label: "on the line", tone: "live" },
    { n: count("verified"), label: "verified", tone: "good" },
    { n: count("booked"), label: "booked", tone: "good" },
    { n: count("dead"), label: "leased", tone: "bad" },
    { n: count("no_answer"), label: "no answer", tone: "warn" },
  ];
  const figures = allFigures.filter((f, i) => i < 2 || f.n > 0);

  const liveRow = live.find((c) => c.id === selectedLive) ?? null;
  const liveKids = liveRow ? groups.find((g) => g.sid === liveRow.session_id)?.kids ?? [] : [];
  const stale = failing && (!lastOk || now - lastOk > STALE_MS);

  return (
    <div className="adm">
      <header className="adm-top">
        <div className="adm-brand">
          <b>Realest</b>
          <span>Call monitor</span>
        </div>
        <nav className="adm-tabs" role="tablist" aria-label="Views">
          <button type="button" role="tab" aria-selected={tab === "live"} className="adm-tab" onClick={() => setTab("live")}>
            Live <span className="num">{groups.length}</span>
          </button>
          <button type="button" role="tab" aria-selected={tab === "history"} className="adm-tab" onClick={() => setTab("history")}>
            History
          </button>
        </nav>
        <div className="adm-health" aria-live="polite">
          {tab === "live" ? (
            stale ? (
              <>
                <span className="adm-dot t-bad" aria-hidden />
                <span className="t-bad">Backend unreachable</span>
                {lastOk ? <span className="num">last {clock(lastOk / 1000)}</span> : null}
              </>
            ) : lastOk ? (
              <>
                <span className="adm-dot is-live t-good" aria-hidden />
                Live
                <span className="num">every 1.2 s</span>
              </>
            ) : (
              <>Connecting…</>
            )
          ) : loadingHist ? (
            <>Loading from ElevenLabs…</>
          ) : histLoadedAt ? (
            <>
              ElevenLabs history
              <span className="num">loaded {clock(histLoadedAt / 1000)}</span>
            </>
          ) : null}
        </div>
      </header>

      {tab === "live" && lastOk ? (
        <div className="adm-figures" aria-label="Right now">
          {figures.map((f) => (
            <span key={f.label}>
              <span className={`num${f.tone ? ` t-${f.tone}` : ""}`}>{f.n}</span>
              {f.label}
            </span>
          ))}
        </div>
      ) : null}

      <div className="adm-body">
        <section className="adm-list" role="tabpanel">
          {tab === "live" ? (
            <>
              <div className="adm-listhead">
                <h1>Sessions in memory</h1>
                <span className="aside">newest first</span>
              </div>
              {groups.length === 0 ? (
                !lastOk ? (
                  <PaneEmpty
                    title={stale ? "Waiting for the backend" : "Connecting…"}
                    body="This page asks /admin/live every 1.2 s and fills in as soon as it answers."
                  />
                ) : (
                  <PaneEmpty
                    title="No calls yet"
                    body="A session appears here the moment a call reaches /agent/init, and its listing calls hang beneath it."
                  />
                )
              ) : (
                <ol
                  className="adm-rows"
                  onKeyDown={(e) => stepThrough(e, order, selectedLive, setSelectedLive)}
                >
                  {groups.map((g) => (
                    <li key={g.sid} className="adm-group">
                      {g.head ? (
                        <button
                          type="button"
                          className="adm-row"
                          data-id={g.head.id}
                          aria-current={selectedLive === g.head.id ? "true" : undefined}
                          onClick={() => {
                            setSelectedLive(g.head?.id ?? "");
                            reveal();
                          }}
                        >
                          <span className="adm-row-main">
                            <span className="adm-row-title">
                              Renter <span className="mono">{g.sid}</span>
                            </span>
                          </span>
                          <Rail
                            hit={reached(g.head, g.kids)}
                            now={g.head.current_tool}
                            live={g.head.status === "in_flight"}
                          />
                          <span className="adm-row-end">
                            <State status={liveStatus(g.head)} />
                            <span className="adm-when">{ago(g.last, now)}</span>
                          </span>
                        </button>
                      ) : (
                        <div className="adm-row">
                          <span className="adm-row-main">
                            <span className="adm-row-title">
                              Session <span className="mono">{g.sid}</span>
                            </span>
                          </span>
                        </div>
                      )}
                      {g.kids.length ? (
                        <ul className="adm-kids">
                          {g.kids.map((k) => (
                            <li key={k.id} className="adm-kid">
                              <button
                                type="button"
                                className="adm-row"
                                data-id={k.id}
                                aria-current={selectedLive === k.id ? "true" : undefined}
                                onClick={() => {
                                  setSelectedLive(k.id);
                                  reveal();
                                }}
                              >
                                <span className="adm-row-main">
                                  <span className="adm-row-title">{k.summary || k.listing_id}</span>
                                  <span className="adm-row-meta">
                                    {k.listing_id}
                                    {k.conversation_id ? ` · ${k.conversation_id}` : ""}
                                  </span>
                                </span>
                                <span className="adm-row-end">
                                  <State status={liveStatus(k)} />
                                  {lastT(k) ? <span className="adm-when">{ago(lastT(k), now)}</span> : null}
                                </span>
                              </button>
                            </li>
                          ))}
                        </ul>
                      ) : null}
                    </li>
                  ))}
                </ol>
              )}
            </>
          ) : (
            <>
              <div className="adm-listhead">
                <h1>Recent conversations</h1>
                <span className="aside">
                  {history.length ? <span className="num">{history.length}</span> : null}
                  <button type="button" className="adm-link" disabled={loadingHist} onClick={() => void loadHistory()}>
                    {loadingHist ? "Refreshing…" : "Refresh"}
                  </button>
                </span>
              </div>
              {histError ? <p className="adm-error">{histError}</p> : null}
              {history.length === 0 ? (
                <PaneEmpty
                  title={loadingHist ? "Loading…" : "Nothing to show"}
                  body="The last twenty conversations from both ElevenLabs agents, renter and listing, newest first."
                />
              ) : (
                <ol
                  className="adm-rows"
                  onKeyDown={(e) =>
                    stepThrough(e, history.map((c) => c.conversation_id), selectedHist, (id) => void openHistory(id))
                  }
                >
                  {history.map((c) => (
                    <li key={c.conversation_id} className="adm-group">
                      <button
                        type="button"
                        className="adm-row is-hist"
                        data-id={c.conversation_id}
                        aria-current={selectedHist === c.conversation_id ? "true" : undefined}
                        onClick={() => {
                          void openHistory(c.conversation_id);
                          reveal();
                        }}
                      >
                        <span className="adm-date">
                          <b>{c.started_at ? clock(c.started_at).slice(0, 5) : "–"}</b>
                          {day(c.started_at)}
                        </span>
                        <span className="adm-row-main">
                          <span className="adm-row-title">
                            {roleName(c.role)}
                            {c.direction && c.direction !== "?" ? <span className="soft"> · {c.direction}</span> : null}
                          </span>
                          <span className="adm-row-meta">{c.tools.length ? c.tools.join(" · ") : "no tool calls"}</span>
                        </span>
                        <span className="adm-row-end">
                          <State status={conversationStatus(c.status)} />
                          <span className="adm-when num">{length(c.duration_secs)}</span>
                        </span>
                      </button>
                    </li>
                  ))}
                </ol>
              )}
            </>
          )}
        </section>

        <aside className="adm-pane" ref={pane} aria-label="Call detail">
          {tab === "live" ? (
            liveRow ? (
              <LivePane row={liveRow} kids={liveKids} now={now} />
            ) : (
              <PaneEmpty title="Nothing selected" body="Pick a session or a listing call to see its timeline and transcript." />
            )
          ) : selectedHist ? (
            <HistoryPane id={selectedHist} detail={detail} error={detailError} now={now} />
          ) : (
            <PaneEmpty title="Nothing selected" body="Pick a conversation to read its tool calls and transcript." />
          )}
        </aside>
      </div>
    </div>
  );
}
