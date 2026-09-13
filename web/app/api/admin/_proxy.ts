export const dynamic = "force-dynamic";

function backend(): string | null {
  return process.env.BACKEND_URL?.replace(/\/+$/, "") || null;
}

export async function proxyAdmin(path: string): Promise<Response> {
  const base = backend();
  if (!base) return Response.json({ error: "BACKEND_URL not set" }, { status: 500 });
  try {
    const r = await fetch(`${base}${path}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(20000),
    });
    return new Response(await r.text(), {
      status: r.status,
      headers: { "content-type": "application/json", "cache-control": "no-store" },
    });
  } catch {
    return Response.json({ error: "backend unreachable" }, { status: 502 });
  }
}
