"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { CallDetail, HistoryCall, LiveCall } from "@/lib/admin";

const RAIL = ["init", "preferences", "start_calls", "outcome", "book"] as const;

function statusClass(status: string): string {
  const s = status.toLowerCase();
  if (s === "in_flight" || s === "calling" || s === "in-progress" || s === "initiated") {
    return "text-warn";
  }
  if (s === "booked" || s === "verified" || s === "done" || s === "ok") {
    return "text-real";
  }
  if (s === "dead" || s === "failed" || s === "error") return "text-dead";
  return "text-muted";
}

function when(unix: number): string {
  if (!unix) return "—";
  const d = new Date(unix * 1000);
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  const ss = String(d.getSeconds()).padStart(2, "0");
  return `${hh}:${mm}:${ss}`;
}

function ToolRail({ tools, current }: { tools: string[]; current: string }) {
  const hit = new Set(tools);
  return (
    <div className="mt-1 flex flex-wrap gap-x-2 gap-y-0.5 font-mono text-[11px]">
      {RAIL.map((step, i) => {
        const on = hit.has(step);
        const now = current === step;
        return (
          <span key={step}>
            {i > 0 ? <span className="text-dim"> — </span> : null}
            <span className={now ? "text-ink" : on ? "text-muted" : "text-dim"}>
              {step}
            </span>
          </span>
        );
      })}
    </div>
  );
}

function LogPane({
  title,
  events,
  transcript,
  detail,
}: {
  title: string;
  events?: LiveCall["events"];
  transcript?: string;
  detail?: CallDetail | null;
}) {
  return (
    <aside className="min-w-0 border-l border-[var(--hair-panel)] bg-warm px-6 py-5">
      <h2 className="text-[13px] font-semibold">{title || "Select a call"}</h2>
      {!title ? (
        <p className="mt-3 text-[13px] text-muted">Click a row for the log.</p>
      ) : null}

      {events && events.length > 0 ? (
        <ol className="mt-5 border-t border-[var(--hair-row)]">
          {events.map((ev, i) => (
            <li key={`${ev.t}-${i}`} className="border-b border-[var(--hair-row)] py-2.5">
              <div className="flex items-baseline justify-between gap-4">
                <span className="font-mono text-[12px]">{ev.tool}</span>
                <span className={`font-mono text-[11px] ${statusClass(ev.status)}`}>
                  {ev.status}
                </span>
              </div>
              <div className="mt-0.5 font-mono text-[11px] text-faint">
                {when(ev.t)}
                {ev.summary ? `  ${ev.summary}` : ""}
              </div>
            </li>
          ))}
        </ol>
      ) : null}

      {detail?.tools && detail.tools.length > 0 ? (
        <ol className="mt-5 border-t border-[var(--hair-row)]">
          {detail.tools.map((tool, i) => (
            <li key={`${tool.name}-${i}`} className="border-b border-[var(--hair-row)] py-2.5">
              <div className="flex items-baseline justify-between gap-4">
                <span className="font-mono text-[12px]">{tool.name}</span>
                <span className={`font-mono text-[11px] ${tool.error ? "text-dead" : "text-real"}`}>
                  {tool.error ? "error" : "ok"}
                </span>
              </div>
              {tool.params && tool.params !== "{}" ? (
                <pre className="mt-1 whitespace-pre-wrap font-mono text-[11px] text-muted">
                  {tool.params}
                </pre>
              ) : null}
              {tool.result ? (
                <pre className="mt-1 whitespace-pre-wrap font-mono text-[11px] text-faint">
                  {tool.result}
                </pre>
              ) : null}
            </li>
          ))}
        </ol>
      ) : null}

      {detail?.turns && detail.turns.length > 0 ? (
        <div className="mt-6">
          <h3 className="text-[12px] font-medium text-muted">Transcript</h3>
          <ol className="mt-2">
            {detail.turns.map((turn, i) => (
              <li key={i} className="border-b border-[var(--hair-row)] py-2">
                <div className="font-mono text-[11px] text-faint">{turn.role}</div>
                <p className="mt-0.5 text-[13px] leading-snug">{turn.text}</p>
              </li>
            ))}
          </ol>
        </div>
      ) : transcript ? (
        <div className="mt-6">
          <h3 className="text-[12px] font-medium text-muted">Transcript</h3>
          <pre className="mt-2 whitespace-pre-wrap font-mono text-[12px] leading-relaxed text-muted">
            {transcript}
          </pre>
        </div>
      ) : null}
    </aside>
  );
}

export function AdminMonitor() {
  const [tab, setTab] = useState<"live" | "history">("live");
  const [live, setLive] = useState<LiveCall[]>([]);
  const [history, setHistory] = useState<HistoryCall[]>([]);
  const [histError, setHistError] = useState("");
  const [selectedLive, setSelectedLive] = useState<string>("");
  const [selectedHist, setSelectedHist] = useState<string>("");
  const [detail, setDetail] = useState<CallDetail | null>(null);
  const [loadingHist, setLoadingHist] = useState(false);
  const prev = useRef("");

  useEffect(() => {
    if (tab !== "live") return;
    let alive = true;
    const poll = async () => {
      try {
        const r = await fetch("/api/admin/live", { cache: "no-store" });
        if (!r.ok || !alive) return;
        const data = (await r.json()) as { calls?: LiveCall[] };
        const calls = Array.isArray(data.calls) ? data.calls : [];
        const json = JSON.stringify(calls);
        if (json === prev.current) return;
        prev.current = json;
        setLive(calls);
      } catch {
        /* keep last */
      }
    };
    poll();
    const id = setInterval(poll, 1200);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [tab]);

  const loadHistory = useCallback(async () => {
    setLoadingHist(true);
    setHistError("");
    try {
      const r = await fetch("/api/admin/calls?limit=20", { cache: "no-store" });
      const data = (await r.json()) as { calls?: HistoryCall[]; error?: string };
      setHistory(Array.isArray(data.calls) ? data.calls : []);
      if (data.error) setHistError(data.error);
    } catch {
      setHistError("Could not fetch calls");
    } finally {
      setLoadingHist(false);
    }
  }, []);

  useEffect(() => {
    if (tab === "history" && history.length === 0 && !loadingHist) {
      void loadHistory();
    }
  }, [tab, history.length, loadingHist, loadHistory]);

  const openHistory = async (cid: string) => {
    setSelectedHist(cid);
    setDetail(null);
    try {
      const r = await fetch(`/api/admin/calls/${encodeURIComponent(cid)}`, {
        cache: "no-store",
      });
      if (!r.ok) return;
      setDetail((await r.json()) as CallDetail);
    } catch {
      /* keep empty pane */
    }
  };

  const liveRow = live.find((c) => c.id === selectedLive);

  return (
    <div className="min-h-svh bg-surface text-ink">
      <header className="border-b border-[var(--hair-head)] bg-surface px-6 py-4">
        <div className="flex items-baseline justify-between gap-6">
          <div>
            <div className="text-[16px] font-bold tracking-[-0.02em]">Realest</div>
            <div className="mt-0.5 text-[12px] text-muted">Admin monitor</div>
          </div>
          <nav className="flex gap-6 text-[13px]">
            <button
              type="button"
              onClick={() => setTab("live")}
              className={tab === "live" ? "font-semibold" : "text-muted"}
            >
              Live
            </button>
            <button
              type="button"
              onClick={() => setTab("history")}
              className={tab === "history" ? "font-semibold" : "text-muted"}
            >
              History
            </button>
          </nav>
        </div>
      </header>

      <div className="grid min-h-[calc(100svh-65px)] grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(320px,42%)]">
        <section className="min-w-0 px-6 py-5">
          {tab === "live" ? (
            <>
              <div className="flex items-baseline justify-between">
                <h1 className="text-[15px] font-semibold">Live calls</h1>
                <span className="font-mono text-[11px] text-faint tnum">{live.length}</span>
              </div>
              {live.length === 0 ? (
                <p className="mt-8 text-[13px] text-muted">No in-memory sessions yet.</p>
              ) : (
                <ol className="mt-4 border-t border-[var(--hair-row)]">
                  {live.map((c) => (
                    <li key={c.id}>
                      <button
                        type="button"
                        onClick={() => setSelectedLive(c.id)}
                        className="w-full border-b border-[var(--hair-row)] py-3 text-left"
                        style={
                          selectedLive === c.id
                            ? { background: "var(--color-tint)" }
                            : undefined
                        }
                      >
                        <div className="flex items-baseline justify-between gap-4">
                          <span className="text-[14px] font-medium">
                            {c.role}
                            {c.summary ? ` · ${c.summary}` : ""}
                          </span>
                          <span className={`font-mono text-[11px] ${statusClass(c.status)}`}>
                            {c.current_tool && c.status === "in_flight"
                              ? c.current_tool
                              : c.status}
                          </span>
                        </div>
                        <div className="mt-0.5 font-mono text-[11px] text-faint">
                          {c.session_id}
                          {c.listing_id ? ` · ${c.listing_id}` : ""}
                        </div>
                        <ToolRail tools={c.tools} current={c.current_tool} />
                      </button>
                    </li>
                  ))}
                </ol>
              )}
            </>
          ) : (
            <>
              <div className="flex items-baseline justify-between gap-4">
                <h1 className="text-[15px] font-semibold">Last calls</h1>
                <button
                  type="button"
                  onClick={() => void loadHistory()}
                  className="font-mono text-[11px] text-muted underline-offset-2 hover:underline"
                >
                  {loadingHist ? "Fetching…" : "Fetch"}
                </button>
              </div>
              {histError ? (
                <p className="mt-3 text-[13px] text-dead">{histError}</p>
              ) : null}
              {history.length === 0 && !loadingHist ? (
                <p className="mt-8 text-[13px] text-muted">
                  Fetch to load the last ElevenLabs conversations.
                </p>
              ) : (
                <ol className="mt-4 border-t border-[var(--hair-row)]">
                  {history.map((c) => (
                    <li key={c.conversation_id}>
                      <button
                        type="button"
                        onClick={() => void openHistory(c.conversation_id)}
                        className="w-full border-b border-[var(--hair-row)] py-3 text-left"
                        style={
                          selectedHist === c.conversation_id
                            ? { background: "var(--color-tint)" }
                            : undefined
                        }
                      >
                        <div className="flex items-baseline justify-between gap-4">
                          <span className="text-[14px] font-medium">
                            {c.role}
                            {c.direction ? ` · ${c.direction}` : ""}
                          </span>
                          <span className={`font-mono text-[11px] ${statusClass(c.status)}`}>
                            {c.status || "—"}
                          </span>
                        </div>
                        <div className="mt-0.5 flex justify-between gap-4 font-mono text-[11px] text-faint">
                          <span>{c.conversation_id}</span>
                          <span className="tnum">
                            {c.duration_secs != null ? `${c.duration_secs}s` : ""}
                          </span>
                        </div>
                        {c.tools.length > 0 ? (
                          <div className="mt-1 font-mono text-[11px] text-muted">
                            {c.tools.join(" — ")}
                          </div>
                        ) : null}
                      </button>
                    </li>
                  ))}
                </ol>
              )}
            </>
          )}
        </section>

        {tab === "live" ? (
          <LogPane
            title={liveRow ? `${liveRow.role} ${liveRow.session_id}` : ""}
            events={liveRow?.events}
            transcript={liveRow?.transcript}
          />
        ) : (
          <LogPane
            title={detail ? `${detail.role} ${detail.conversation_id}` : selectedHist}
            detail={detail}
          />
        )}
      </div>
    </div>
  );
}
