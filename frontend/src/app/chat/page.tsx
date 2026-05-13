"use client";

import Link from "next/link";
import { useChat } from "@/hooks/useChat";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { InputBar } from "@/components/chat/InputBar";

function NutriIntelLogo({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="40" height="40" rx="10" fill="#0F1525" stroke="#00FF94" strokeWidth="1.5"/>
      <path d="M20 6L32 13V27L20 34L8 27V13L20 6Z" stroke="#00FF94" strokeWidth="1.2" fill="none" opacity="0.4"/>
      <circle cx="20" cy="20" r="3.5" fill="#00FF94"/>
      <line x1="20" y1="10" x2="20" y2="16.5" stroke="#00FF94" strokeWidth="1.2" opacity="0.8"/>
      <line x1="20" y1="23.5" x2="20" y2="30" stroke="#00FF94" strokeWidth="1.2" opacity="0.8"/>
      <line x1="11" y1="15" x2="16.7" y2="18.3" stroke="#00FF94" strokeWidth="1.2" opacity="0.8"/>
      <line x1="23.3" y1="21.7" x2="29" y2="25" stroke="#00FF94" strokeWidth="1.2" opacity="0.8"/>
      <line x1="29" y1="15" x2="23.3" y2="18.3" stroke="#00FF94" strokeWidth="1.2" opacity="0.8"/>
      <line x1="16.7" y1="21.7" x2="11" y2="25" stroke="#00FF94" strokeWidth="1.2" opacity="0.8"/>
      <circle cx="20" cy="10" r="1.5" fill="#00FF94" opacity="0.6"/>
      <circle cx="20" cy="30" r="1.5" fill="#00FF94" opacity="0.6"/>
      <circle cx="11" cy="15" r="1.5" fill="#00FF94" opacity="0.6"/>
      <circle cx="29" cy="15" r="1.5" fill="#00FF94" opacity="0.6"/>
      <circle cx="11" cy="25" r="1.5" fill="#00FF94" opacity="0.6"/>
      <circle cx="29" cy="25" r="1.5" fill="#00FF94" opacity="0.6"/>
    </svg>
  );
}

export default function ChatPage() {
  const { messages, isLoading, error, sendMessage } = useChat();

  return (
    <div style={{
      display: "flex", flexDirection: "column", height: "100dvh",
      background: "#0A0E1A", position: "relative", overflow: "hidden",
    }}>
      {/* Subtle grid bg */}
      <div style={{
        position: "absolute", inset: 0, pointerEvents: "none",
        backgroundImage: `linear-gradient(rgba(0,255,148,0.025) 1px, transparent 1px),
                          linear-gradient(90deg, rgba(0,255,148,0.025) 1px, transparent 1px)`,
        backgroundSize: "50px 50px",
      }}/>
      {/* Top glow */}
      <div style={{
        position: "absolute", top: -100, left: "50%", transform: "translateX(-50%)",
        width: 600, height: 300, pointerEvents: "none",
        background: "radial-gradient(ellipse, rgba(0,255,148,0.05) 0%, transparent 70%)",
      }}/>

      {/* Header */}
      <header style={{
        position: "relative", zIndex: 10,
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0.85rem 1.25rem",
        background: "rgba(10,14,26,0.9)",
        backdropFilter: "blur(12px)",
        borderBottom: "1px solid rgba(0,255,148,0.1)",
        flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
          <Link href="/" style={{ display: "flex", alignItems: "center", textDecoration: "none" }}>
            <NutriIntelLogo size={28} />
          </Link>
          <div>
            <div style={{ fontFamily: "var(--font-mono)", fontWeight: 700, fontSize: "0.85rem", color: "#E8EDF5", letterSpacing: "0.06em" }}>
              NUTRIINTEL
            </div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.62rem", color: "#8B9BB4", letterSpacing: "0.08em" }}>
              CLINICAL PEDIATRIC NUTRITION ASSISTANT
            </div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <span style={{
            display: "flex", alignItems: "center", gap: "0.35rem",
            fontSize: "0.72rem", color: "#00FF94", fontFamily: "var(--font-mono)",
          }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#00FF94", display: "inline-block", boxShadow: "0 0 6px #00FF94" }}/>
            LIVE
          </span>
          <Link href="/" style={{
            color: "#8B9BB4", textDecoration: "none", fontSize: "0.78rem",
            border: "1px solid rgba(30,45,74,0.8)", borderRadius: "6px",
            padding: "0.3rem 0.7rem", transition: "all 0.2s", fontFamily: "var(--font-mono)",
          }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = "#00FF94"; (e.currentTarget as HTMLElement).style.borderColor = "rgba(0,255,148,0.3)"; }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = "#8B9BB4"; (e.currentTarget as HTMLElement).style.borderColor = "rgba(30,45,74,0.8)"; }}
          >← Home</Link>
        </div>
      </header>

      {/* Chat window */}
      <main style={{ position: "relative", zIndex: 1, flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        <div style={{ flex: 1, maxWidth: "800px", width: "100%", margin: "0 auto", display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <ChatWindow messages={messages} isLoading={isLoading} />

          {error && (
            <div role="alert" style={{
              padding: "0.5rem 1rem", margin: "0 1rem",
              background: "rgba(255,82,82,0.1)", color: "#FF5252",
              fontSize: "0.85rem", borderRadius: "8px",
              border: "1px solid rgba(255,82,82,0.2)",
            }}>
              {error}
            </div>
          )}

          <InputBar onSend={sendMessage} disabled={isLoading} />
        </div>
      </main>
    </div>
  );
}
