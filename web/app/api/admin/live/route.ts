import { proxyAdmin } from "../_proxy";

export const dynamic = "force-dynamic";

export async function GET() {
  return proxyAdmin("/admin/live");
}
