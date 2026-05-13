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

export async function sendMessage(
  sessionId: string,
  message: string
): Promise<CPNAResponse> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message }),
    });
  } catch {
    throw new Error("Something went wrong.");
  }

  if (!res.ok) {
    throw new Error("Something went wrong.");
  }

  const data: { response: CPNAResponse } = await res.json();
  return data.response;
}
