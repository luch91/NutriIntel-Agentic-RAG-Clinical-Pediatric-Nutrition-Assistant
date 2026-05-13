"use client";

import { useCallback, useState } from "react";
import { getOrCreateSessionId, sendMessage as apiSendMessage } from "@/lib/api";
import type { ChatMessage, CPNAResponse } from "@/lib/types";

function makeId(): string {
  return Math.random().toString(36).slice(2, 10);
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;

    setError(null);

    const userMsg: ChatMessage = {
      id: makeId(),
      role: "user",
      content: trimmed,
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const sessionId = getOrCreateSessionId();
      const response: CPNAResponse = await apiSendMessage(sessionId, trimmed);
      const assistantMsg: ChatMessage = {
        id: makeId(),
        role: "assistant",
        content: response,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Something went wrong. Please try again.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [isLoading]);

  return { messages, isLoading, error, sendMessage };
}
