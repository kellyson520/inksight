import { NextRequest } from "next/server";
import { proxyGet, proxyPost } from "../_proxy";

export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  return proxyGet(`/api/server-status${url.search}`, req);
}

export async function POST(req: NextRequest) {
  const url = new URL(req.url);
  return proxyPost(`/api/server-status${url.search}`, req);
}
