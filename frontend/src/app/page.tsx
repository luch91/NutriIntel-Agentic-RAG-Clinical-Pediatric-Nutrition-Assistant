"use client";

import { useChat } from "@/hooks/useChat";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { InputBar } from "@/components/chat/InputBar";

export default function Home() {
  const { messages, isLoading, error, sendMessage } = useChat();

  return (
    <main
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100dvh",
        maxWidth: "760px",
        margin: "0 auto",
        width: "100%",
      }}
    >
      <ChatWindow messages={messages} isLoading={isLoading} />

      {error && (
        <div
          role="alert"
          style={{
            padding: "0.5rem 1rem",
            background: "#FFEBEE",
            color: "#B71C1C",
            fontSize: "0.85rem",
            borderTop: "1px solid #FFCDD2",
          }}
        >
          {error}
        </div>
      )}

      <InputBar onSend={sendMessage} disabled={isLoading} />
    </main>
  );
}
