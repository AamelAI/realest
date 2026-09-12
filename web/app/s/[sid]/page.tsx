import { Board } from "@/components/Board";
import { DEFAULT_STATE, type SessionState } from "@/lib/types";

// Without this Next caches the route statically and your "live" page is a snapshot.
export const dynamic = "force-dynamic";

async function getState(sid: string): Promise<SessionState | null> {
  const backend = process.env.BACKEND_URL;
  if (!backend) return null;
  try {
    const r = await fetch(`${backend}/api/state?session=${encodeURIComponent(sid)}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(4000),
    });
    if (!r.ok) return null;
    return (await r.json()) as SessionState;
  } catch {
    return null;
  }
}

export default async function SessionPage({ params }: { params: Promise<{ sid: string }> }) {
  const { sid } = await params;
  const state = await getState(sid);

  // Expired or unknown token: a plain card, never a 404. A browser error page
  // in the middle of a demo reads as broken software.
  if (!state) {
    return (
      <main className="flex min-h-dvh items-center justify-center px-6">
        <div className="max-w-sm text-center">
          <h1 className="font-display text-xl font-extrabold tracking-[-0.02em]">
            This shortlist has expired
          </h1>
          <p className="mt-2 text-sm text-muted">
            Shortlists live as long as the call. Ring us back and we&rsquo;ll build a new one.
          </p>
        </div>
      </main>
    );
  }

  // Server-rendered first paint — the caller opens this mid-sentence, so a
  // spinner is a dead beat. The poller takes over from here.
  return <Board sid={sid} initial={{ ...DEFAULT_STATE, ...state }} />;
}
