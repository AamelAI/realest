import { proxyAdmin } from "../../_proxy";

export const dynamic = "force-dynamic";

export async function GET(
  _req: Request,
  ctx: { params: Promise<{ id: string }> },
) {
  const { id } = await ctx.params;
  if (!id) return Response.json({ error: "missing id" }, { status: 400 });
  return proxyAdmin(`/admin/calls/${encodeURIComponent(id)}`);
}
