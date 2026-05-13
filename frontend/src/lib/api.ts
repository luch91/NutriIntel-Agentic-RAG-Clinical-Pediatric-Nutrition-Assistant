import type { CPNAResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";
const SESSION_KEY = "cpna_session_id";

export function getOrCreateSessionId(): string {
  if (typeof window === "undefined") return "ssr-session";
  const existing = sessionStorage.getItem(SESSION_KEY);
  if (existing) return existing;
  const id = crypto.randomUUID();
  sessionStorage.setItem(SESSION_KEY, id);
  return id;
}

// ── Structured client-side logger ───────────────────────────────────────────

const IS_DEV = process.env.NODE_ENV === "development";

export const clientLog = {
  info: (event: string, data?: Record<string, unknown>) => {
    if (IS_DEV) console.log(`[NutriIntel] ${event}`, data ?? "");
  },
  warn: (event: string, data?: Record<string, unknown>) => {
    console.warn(`[NutriIntel:warn] ${event}`, data ?? "");
  },
  error: (event: string, data?: Record<string, unknown>) => {
    console.error(`[NutriIntel:error] ${event}`, data ?? "");
  },
};

// ── API call ─────────────────────────────────────────────────────────────────

export async function sendMessage(
  sessionId: string,
  message: string
): Promise<CPNAResponse> {
  const url = `${API_BASE}/api/chat`;
  const t0 = performance.now();

  clientLog.info("request_start", { url, sessionId });

  let res: Response;
  try {
    res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message }),
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    clientLog.error("network_error", { url, sessionId, error: msg });
    throw new Error(`Network error: ${msg}`);
  }

  const latencyMs = Math.round(performance.now() - t0);

  if (!res.ok) {
    let body = "(no body)";
    try { body = await res.text(); } catch { /* ignore */ }
    clientLog.error("http_error", {
      url,
      sessionId,
      status: res.status,
      statusText: res.statusText,
      latencyMs,
      responseBody: body.slice(0, 500),
    });
    throw new Error(`HTTP ${res.status} ${res.statusText} — ${body.slice(0, 200)}`);
  }

  let data: { response: CPNAResponse };
  try {
    data = await res.json();
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    clientLog.error("json_parse_error", { url, sessionId, latencyMs, error: msg });
    throw new Error(`Invalid JSON from server: ${msg}`);
  }

  clientLog.info("request_ok", {
    url,
    sessionId,
    latencyMs,
    queryType: data.response?.query_type,
  });

  return data.response;
}
