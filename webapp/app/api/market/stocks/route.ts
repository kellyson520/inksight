import { NextRequest } from "next/server";
import { proxyGet, proxyPost } from "../../_proxy";

export async function GET(req: NextRequest) {
  return proxyGet("/api/market/stocks", req);
}

export async function POST(req: NextRequest) {
  return proxyPost("/api/market/stocks", req);
}
