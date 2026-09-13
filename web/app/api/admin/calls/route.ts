import { proxyAdmin } from "../_proxy";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const limit = new URL(req.url).searchParams.get("limit") || "20";
  return proxyAdmin(`/admin/calls?limit=${encodeURIComponent(limit)}`);
}
