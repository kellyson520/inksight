import { NextRequest, NextResponse } from "next/server";

const backendBase = process.env.INKSIGHT_BACKEND_API_BASE?.replace(/\/$/, "") || "http://127.0.0.1:8070";

async function forward(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const subPath = (path || []).join("/");
  const url = `${backendBase}/api/auth/${subPath}${req.nextUrl.search}`;

  const headers = new Headers();
  req.headers.forEach((val, key) => {
    if (key.toLowerCase() !== "host") {
      headers.set(key, val);
    }
  });

  const body = req.method !== "GET" && req.method !== "HEAD" ? await req.arrayBuffer() : undefined;

  try {
    const upstreamRes = await fetch(url, {
      method: req.method,
      headers,
      body,
      redirect: "manual",
    });

    const resHeaders = new Headers();
    upstreamRes.headers.forEach((val, key) => {
      if (key.toLowerCase() === "set-cookie") {
        resHeaders.append(key, val);
      } else {
        resHeaders.set(key, val);
      }
    });

    const resBody = await upstreamRes.arrayBuffer();
    return new NextResponse(resBody, {
      status: upstreamRes.status,
      headers: resHeaders,
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { error: "upstream_unreachable", message: msg },
      { status: 502 },
    );
  }
}

export const GET = forward;
export const POST = forward;
export const PUT = forward;
export const DELETE = forward;
