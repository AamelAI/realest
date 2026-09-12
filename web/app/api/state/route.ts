// Proxy so the phone NEVER resolves ngrok directly.
//
// Some mobile carriers and corporate DNS block ngrok domains outright. If the
// demo phone is on such a network the page never loads, and you find out on
// camera. Vercel is never blocked. It also removes CORS and keeps the tunnel
// URL out of client code.
//
// BACKEND_URL is a Vercel env var — changing tunnels means changing one
// variable, not redeploying.
export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const session = new URL(req.url).searchParams.get("session");
  if (!session) return Response.json({ error: "missing session" }, { status: 400 });

  const backend = process.env.BACKEND_URL;
  if (!backend) return Response.json({ error: "BACKEND_URL not set" }, { status: 500 });

  try {
    const r = await fetch(`${backend}/api/state?session=${encodeURIComponent(session)}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(4000),
    });
    return new Response(await r.text(), {
      status: r.status,
      headers: { "content-type": "application/json", "cache-control": "no-store" },
    });
  } catch {
    // Never 500 into the poller — it keeps its last good state on a bad tick.
    return Response.json({ error: "backend unreachable" }, { status: 502 });
  }
}
