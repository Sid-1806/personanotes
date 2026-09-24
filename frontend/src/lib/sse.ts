import { API_BASE, ApiError, getToken } from "@/lib/api";

export interface SseHandlers {
  onEvent: (event: string, data: Record<string, unknown>) => void;
  signal?: AbortSignal;
}

/**
 * POST a JSON body and consume a `text/event-stream` response.
 *
 * `EventSource` can't send a body or an Authorization header, so streaming
 * endpoints are driven through `fetch` and parsed here. Events arrive as
 * `event: <name>\ndata: <json>\n\n`.
 */
export async function streamRequest(
  path: string,
  body: unknown,
  { onEvent, signal }: SseHandlers,
): Promise<void> {
  const token = getToken();
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    let detail = "The stream could not be started.";
    try {
      detail = (await response.json())?.detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    if (response.status === 429) {
      const header = response.headers.get("retry-after");
      throw new ApiError(detail, "rate_limited", 429, header ? Number(header) : 60);
    }
    if (response.status === 401) {
      throw new ApiError("Your session expired.", "unauthorized", 401);
    }
    throw new ApiError(detail, response.status >= 500 ? "server" : "validation", response.status);
  }

  if (!response.body) throw new ApiError("Streaming isn't supported here.", "unknown");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // Frames are separated by a blank line; keep any partial tail in the buffer.
    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const frame = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      boundary = buffer.indexOf("\n\n");

      let eventName = "message";
      const dataLines: string[] = [];
      for (const line of frame.split("\n")) {
        if (line.startsWith("event:")) eventName = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
      }
      if (!dataLines.length) continue;
      try {
        onEvent(eventName, JSON.parse(dataLines.join("\n")));
      } catch {
        /* a malformed frame shouldn't kill the stream */
      }
    }
  }
}
