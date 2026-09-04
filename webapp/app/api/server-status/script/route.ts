import { NextRequest } from "next/server";
import { proxyGet } from "../../_proxy";

export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  return proxyGet(`/api/server-status/script${url.search}`, req);
}
