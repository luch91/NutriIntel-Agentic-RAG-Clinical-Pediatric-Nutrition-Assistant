"use client";

import { useEffect, useRef } from "react";
import type { ChatMessage } from "@/lib/types";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";

interface Props {
  messages: ChatMessage[];
  isLoading: boolean;
}

export function ChatWindow({ messages, isLoading }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div
      style={{
        flex: 1,
        overflowY: "auto",
        padding: "1.25rem 1rem",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {messages.length === 0 && !isLoading && (
        <div
          style={{
            margin: "auto",
            textAlign: "center",
            color: "#aaa",
            fontSize: "0.9rem",
            maxWidth: "340px",
          }}
        >
          <p style={{ fontFamily: "var(--font-display)", fontSize: "1.1rem", color: "#888", marginBottom: "0.4rem" }}>
            CPNA Clinical Nutrition Assistant
          </p>
          <p style={{ margin: 0 }}>
            Ask a question about paediatric nutrition, dietary guidance, or food comparisons.
          </p>
        </div>
      )}

      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}

      {isLoading && <TypingIndicator />}

      <div ref={bottomRef} />
    </div>
  );
}
