const API_BASE = process.env.YFD_STUDIO_API_BASE || "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ jobId: string }> },
) {
  const { jobId } = await params;

  try {
    const response = await fetch(`${API_BASE}/api/jobs/${encodeURIComponent(jobId)}/events`, {
      cache: "no-store",
      headers: {
        accept: "text/event-stream"
      }
    });

    if (!response.ok || !response.body) {
      const text = await response.text();
      return new Response(text, {
        status: response.status,
        headers: {
          "content-type": response.headers.get("content-type") || "application/json"
        }
      });
    }

    return new Response(response.body, {
      status: response.status,
      headers: {
        "content-type": response.headers.get("content-type") || "text/event-stream",
        "cache-control": "no-cache, no-transform",
        connection: "keep-alive"
      }
    });
  } catch {
    return Response.json(
      {
        detail: "Backend API is not reachable."
      },
      { status: 502 },
    );
  }
}
