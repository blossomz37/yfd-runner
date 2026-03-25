import { NextResponse } from "next/server";

const API_BASE = process.env.YFD_STUDIO_API_BASE || "http://127.0.0.1:8000";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ jobId: string }> },
) {
  const { jobId } = await params;

  try {
    const response = await fetch(`${API_BASE}/api/jobs/${encodeURIComponent(jobId)}`, {
      cache: "no-store"
    });

    const text = await response.text();
    return new NextResponse(text, {
      status: response.status,
      headers: {
        "content-type": response.headers.get("content-type") || "application/json"
      }
    });
  } catch {
    return NextResponse.json(
      {
        detail: "Backend API is not reachable."
      },
      { status: 502 },
    );
  }
}
