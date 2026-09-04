import { NextRequest } from "next/server";
import { proxyDelete } from "../../../_proxy";

export async function DELETE(
  req: NextRequest,
  context: { params: Promise<{ symbol: string }> }
) {
  const { symbol } = await context.params;
  return proxyDelete(`/api/market/stocks/${encodeURIComponent(symbol)}`, req);
}
