---
name: live-surface
description: The Next.js page the caller opens mid-call — card list, live polling, tap-to-confirm, call states. Use when working in web/, on usePolling, on the listing cards, or on anything the caller sees on their phone while talking.
---

# The live surface

The page the caller opens from an SMS **while still on the phone**. It reorders as they talk.

## Why it exists

Voice is invisible. A judge watching forty videos cannot *see* a shortlist reorder inside an audio stream. This page makes the product legible — and it's something the user genuinely needs, because nobody picks an apartment without seeing the photos.

It also does a job voice can't: tapping three checkboxes is far more reliable than parsing *"yeah, do the first and the third one"* out of a phone call.

## The design rule that overrides everything

**The page is never load-bearing.** If polling dies, the phone locks, or Vercel hiccups, the voice loop still completes — still calls, still books, still texts. Build it as an enhancement on a working conversation.

This is correct engineering and it is also demo insurance.

## One route, not one endpoint per user

The link in the SMS is `https://realest.vercel.app/s/<token>`. That is **one** Next.js dynamic route — `web/app/s/[sid]/page.tsx` — with the session id as a path parameter. You never register anything per user.

### The token

Minted when the inbound call's websocket opens, mapped to the Twilio `CallSid`:

```python
import secrets
token = secrets.token_urlsafe(8)          # 11 chars, 64 bits of entropy
SESSIONS[token] = SessionState(session_id=token, call_sid=call_sid)
```

Short matters — it goes in an SMS and people glance at it. Don't put the raw `CallSid` in the URL (34 characters, and it leaks a Twilio identifier).

### The security model, stated plainly

**There is no auth. The token is the secret.** Same pattern as a password-reset link or a "anyone with the link" doc:

- Unguessable — 64 bits from `secrets`, never `random`
- Expires with the session (~2h TTL), and dies on process restart
- No PII in the path
- Anyone holding the link sees that shortlist

That's the right trade for a caller who is mid-conversation and cannot log in. **Put it in the README under limitations** — SMS isn't encrypted end to end and a forwarded link stays live until expiry. Judges reward naming your own limitations; they penalize pretending they aren't there.

## Proxy through Vercel — don't let the phone hit ngrok

The page is on Vercel; `SessionStore` is on a laptop behind ngrok. Do **not** have the browser fetch the ngrok URL directly.

```ts
// web/app/api/state/route.ts
export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const sid = new URL(req.url).searchParams.get("session");
  const r = await fetch(`${process.env.BACKEND_URL}/api/state?session=${sid}`, {
    cache: "no-store",
  });
  return new Response(await r.text(), {
    headers: { "content-type": "application/json", "cache-control": "no-store" },
  });
}
```

Three reasons, in order of how badly they bite:

1. **Some mobile carriers and corporate DNS block ngrok domains outright.** If the demo phone is on a network that does, the page never loads and you find out on camera. Vercel is never blocked.
2. No CORS. `usePolling` fetches the relative `/api/state` and same-origin rules apply.
3. The ngrok URL never appears in client code or the network tab.

`BACKEND_URL` is a Vercel env var. Changing tunnels means changing one variable, not redeploying the client.

## First paint must not be blank

The caller opens this while talking. A spinner is a dead beat in the demo.

Server-render the initial list, then hand off to the poller:

```tsx
// web/app/s/[sid]/page.tsx
export const dynamic = "force-dynamic";   // without this Next caches it statically

export default async function Page({ params }: { params: { sid: string } }) {
  const state = await fetch(`${process.env.BACKEND_URL}/api/state?session=${params.sid}`,
                            { cache: "no-store" }).then(r => r.json());
  return <Board sid={params.sid} initial={state} />;   // client component polls from here
}
```

Pass `initial` into `usePolling` as the starting state so nothing flashes.

**Unknown or expired token:** render a plain "this shortlist has expired" card. Never a 404 — a browser error page in the middle of a demo reads as broken software.

## Many sessions at once

The store is a dict keyed by token, so concurrent sessions just work. Test it — two of you calling at the same time is exactly what happens when you rehearse, and a shared-mutable-state bug shows up there first.

## Polling, not websockets

A 3rd-place winner shipped exactly this, at 2000ms:

```ts
export function usePolling(intervalMs = 1500): SessionState {
  const [state, setState] = useState<SessionState>(DEFAULT_STATE);
  const prev = useRef<string>(JSON.stringify(DEFAULT_STATE));

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch(`/api/state?session=${sessionId}`, { cache: "no-store" });
        const data = await res.json();
        const json = JSON.stringify(data);
        if (json !== prev.current) { prev.current = json; setState(data); }
      } catch { /* server unreachable — keep last good state */ }
    };
    poll();
    const id = setInterval(poll, intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);

  return state;
}
```

Three things in there that matter:

- **`cache: "no-store"`** — without it you'll poll a cached response and swear the backend is broken.
- **Diff on the serialized payload** before `setState`, or you re-render every tick and the cards flicker.
- **Swallow the error and keep the last good state.** A dropped poll must never blank the screen mid-demo.

1000–1500ms is the sweet spot. Fast enough that the reorder feels live, slow enough to be free.

## Layout

One screen. A vertical list of cards. Mobile-first — it opens on a phone, held in one hand, next to someone's ear.

No routing, no auth, no nav, no dark-mode toggle. The session id in the URL is the whole access model.

## Card states

Five, and each must be readable at a glance from across a room — a judge is watching this at video scale.

| Status | Treatment |
|---|---|
| `PENDING` | Neutral. Photo, address, rent, beds/baths, amenities |
| `CALLING` | Live indicator + running timer. All three light up simultaneously — **that's the shot** |
| `VERIFIED` | Green. Show what the call revealed and the slot offered |
| `DEAD` | Red, address struck through, sinks to the bottom |
| `NO_ANSWER` | Amber. Drafted email shown inline with a **Send** button |
| `BOOKED` | Green, confirmed slot, locked |

**Corrected facts must visibly replace listed ones.** `$3,250` → `$3,430 real`, with the listed figure struck through. The correction is the product; don't bury it in a detail view.

**Every call-derived fact carries its provenance:** *"parking $180 — Mark, 1:42pm."* That line is what turns a UI into evidence.

## Animate the reorder, briefly

The cards moving is the single most important visual in the submission. Use a FLIP-style transition or Framer Motion's layout animation so positions interpolate rather than snap — a snap is unreadable at video speed.

Keep it ~300ms. Respect `prefers-reduced-motion`.

## Tap-to-confirm

Checkboxes on each card plus one **Call these** button. Posts listing ids to `/agent/start-calls`.

Both paths must work: the caller can tap, or tell the agent out loud. Neither is the only way in — the page is not load-bearing.

## Header

One line at the top showing `agent_says` — the last thing the agent said. It lets a viewer follow the conversation without audio, which matters because judges may watch your video muted the first time.

## CopilotKit

If someone on the team is already fluent in AG-UI, build the cards as streaming agent state and claim **Best Use of CopilotKit** — a named award with a much smaller field than the podium.

If nobody is fluent: plain React plus the poll above. Ship first. Don't let award-chasing sink the build.

## Deploy

Vercel, so the SMS link is a real public URL. `/s/<session_id>` routes straight to the board — no landing page, no click-through. The caller is on the phone; every extra tap is friction.

## Gotchas

- **Never sort in the page.** `listings` arrives ranked. Two sort implementations will disagree at the worst possible moment.
- **`no-store` on every fetch**, and don't let Next cache the route.
- **Images need fixed aspect ratios** or the list jumps as photos load — which looks exactly like a bug during a reorder.
- **Test on a real phone over cellular**, not desktop Chrome. That's where it will be filmed.
- **Strict TypeScript on the state type.** Mirror `SessionState` in `web/lib/types.ts` and keep it in sync with `server/state.py`. A silent shape drift here shows up as blank cards.
