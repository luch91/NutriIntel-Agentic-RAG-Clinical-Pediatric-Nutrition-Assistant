"use client";

import { useEffect, useRef } from "react";
import type { ChatMessage } from "@/lib/types";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";

interface Props {
  messages: ChatMessage[];
  isLoading: boolean;
}

const SUGGESTIONS = [
  "What are the iron requirements for a 6-month-old?",
  "Compare bambara nut vs groundnut for zinc content",
  "Recommend foods for a child with cystic fibrosis",
  "What is the DRI for calcium in a 5-year-old?",
];

export function ChatWindow({ messages, isLoading }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div style={{
      flex: 1, overflowY: "auto", padding: "1.5rem 1rem",
      display: "flex", flexDirection: "column",
    }}>
      {messages.length === 0 && !isLoading && (
        <div style={{
          margin: "auto", textAlign: "center", maxWidth: "480px",
          animation: "fadeUp 0.5s ease both",
        }}>
          {/* Logo glow */}
          <div style={{ marginBottom: "1.5rem" }}>
            <div style={{
              width: 64, height: 64, borderRadius: "16px",
              background: "rgba(0,255,148,0.08)", border: "1px solid rgba(0,255,148,0.2)",
              margin: "0 auto",
              display: "flex", alignItems: "center", justifyContent: "center",
              boxShadow: "0 0 30px rgba(0,255,148,0.1)",
            }}>
              <svg width="36" height="36" viewBox="0 0 40 40" fill="none">
                <path d="M20 6L32 13V27L20 34L8 27V13L20 6Z" stroke="#00FF94" strokeWidth="1.2" fill="none" opacity="0.5"/>
                <circle cx="20" cy="20" r="5" fill="#00FF94" opacity="0.9"/>
                <line x1="20" y1="10" x2="20" y2="15" stroke="#00FF94" strokeWidth="1.2"/>
                <line x1="20" y1="25" x2="20" y2="30" stroke="#00FF94" strokeWidth="1.2"/>
                <line x1="11" y1="15" x2="15.5" y2="17.5" stroke="#00FF94" strokeWidth="1.2"/>
                <line x1="24.5" y1="22.5" x2="29" y2="25" stroke="#00FF94" strokeWidth="1.2"/>
                <line x1="29" y1="15" x2="24.5" y2="17.5" stroke="#00FF94" strokeWidth="1.2"/>
                <line x1="15.5" y1="22.5" x2="11" y2="25" stroke="#00FF94" strokeWidth="1.2"/>
              </svg>
            </div>
          </div>

          <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "#00FF94", letterSpacing: "0.12em", marginBottom: "0.5rem" }}>
            NUTRIINTEL ASSISTANT
          </p>
          <p style={{ fontFamily: "var(--font-display)", fontSize: "1.2rem", color: "#E8EDF5", fontWeight: 700, marginBottom: "0.5rem" }}>
            Clinical Pediatric Nutrition Intelligence
          </p>
          <p style={{ color: "#8B9BB4", fontSize: "0.875rem", lineHeight: 1.6, marginBottom: "2rem" }}>
            Ask about pediatric dietary requirements, food comparisons, therapy plans,
            or nutrition recommendations for specific conditions.
          </p>

          {/* Suggestion chips */}
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {SUGGESTIONS.map((s, i) => (
              <div key={i} style={{
                padding: "0.6rem 1rem",
                background: "rgba(15,21,37,0.8)",
                border: "1px solid rgba(30,45,74,0.8)",
                borderRadius: "8px", cursor: "default",
                fontSize: "0.82rem", color: "#8B9BB4",
                textAlign: "left", lineHeight: 1.4,
                animation: `fadeUp 0.4s ease ${i * 80}ms both`,
              }}>
                <span style={{ color: "#00FF94", marginRight: "0.5rem", fontFamily: "var(--font-mono)", fontSize: "0.7rem" }}>›</span>
                {s}
              </div>
            ))}
          </div>
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
