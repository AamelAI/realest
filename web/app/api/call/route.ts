// Tap-to-confirm posts here. Same proxy reasoning as /api/state: the phone must
// never resolve ngrok directly, and BACKEND_URL stays out of client code.
export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  const backend = process.env.BACKEND_URL?.replace(/\/+$/, "");
  if (!backend) return Response.json({ error: "BACKEND_URL not set" }, { status: 500 });

  try {
    const r = await fetch(`${backend}/agent/start-calls`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: await req.text(),
      cache: "no-store",
      signal: AbortSignal.timeout(120000),
    });
    return new Response(await r.text(), {
      status: r.status,
      headers: { "content-type": "application/json" },
    });
  } catch {
    return Response.json({ error: "backend unreachable" }, { status: 502 });
  }
}
