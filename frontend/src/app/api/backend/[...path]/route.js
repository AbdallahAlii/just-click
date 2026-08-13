import { NextResponse } from "next/server";
import { FLASK_ORIGIN } from "@/lib/env";

function buildTarget(req, pathParts) {
  const incoming = new URL(req.url);
  const parts = Array.isArray(pathParts) ? pathParts : [String(pathParts || "")].filter(Boolean);
  const target = new URL(`${FLASK_ORIGIN}/api/${parts.join("/")}`);
  target.search = incoming.search;
  return target;
}

function cleanHeaders(reqHeaders) {
  const h = new Headers(reqHeaders);

  // remove hop-by-hop / troublesome headers
  h.delete("host");
  h.delete("connection");
  h.delete("content-length");
  h.delete("accept-encoding");

  return h;
}

async function proxy(req, ctx) {
  const pathParam = ctx?.params?.path;
  const targetUrl = buildTarget(req, pathParam);

  try {
    const method = req.method.toUpperCase();
    const hasBody = method !== "GET" && method !== "HEAD";
    const headers = cleanHeaders(req.headers);

    // optional debug headers
    headers.set("X-Forwarded-Host", new URL(req.url).host);
    headers.set("X-Forwarded-Proto", new URL(req.url).protocol.replace(":", ""));

    console.log("[Proxy]", method, String(targetUrl));

    const upstream = await fetch(targetUrl, {
      method,
      headers,
      body: hasBody ? await req.arrayBuffer() : undefined,
      redirect: "manual",
    });

    const resHeaders = new Headers(upstream.headers);
    const data = await upstream.arrayBuffer();

    return new NextResponse(data, { status: upstream.status, headers: resHeaders });
  } catch (err) {
    console.error("[Proxy ERROR]", {
      FLASK_ORIGIN,
      target: String(targetUrl),
      message: err?.message,
      stack: err?.stack,
    });

    const isProd = process.env.NODE_ENV === "production";
    return NextResponse.json(
      {
        success: false,
        message: "Proxy failed to reach Flask backend.",
        // Never leak internal Flask origin to browsers in production.
        ...(isProd
          ? {}
          : {
              target: String(targetUrl),
              flask_origin: FLASK_ORIGIN,
              error: String(err?.message || err),
            }),
      },
      { status: 500 }
    );
  }
}

export async function GET(req, ctx) { return proxy(req, ctx); }
export async function POST(req, ctx) { return proxy(req, ctx); }
export async function PUT(req, ctx) { return proxy(req, ctx); }
export async function PATCH(req, ctx) { return proxy(req, ctx); }
export async function DELETE(req, ctx) { return proxy(req, ctx); }
export async function OPTIONS(req, ctx) { return proxy(req, ctx); }