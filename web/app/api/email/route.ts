// Tap Send on a drafted email. Same proxy reasoning as /api/state and /api/call:
// the phone must never resolve ngrok directly, and BACKEND_URL stays out of
// client code.
//
// The backend answers { sent: boolean } — it returns false (without changing
// state) when Resend isn't configured, so the button reports what actually
// happened rather than assuming success.
export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  const backend = process.env.BACKEND_URL?.replace(/\/+$/, "");
  if (!backend) return Response.json({ error: "BACKEND_URL not set" }, { status: 500 });

  try {
    const r = await fetch(`${backend}/agent/email`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: await req.text(),
      cache: "no-store",
      signal: AbortSignal.timeout(12000),
    });
    return new Response(await r.text(), {
      status: r.status,
      headers: { "content-type": "application/json" },
    });
  } catch {
    return Response.json({ error: "backend unreachable" }, { status: 502 });
  }
}
