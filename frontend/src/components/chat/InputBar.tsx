"use client";

import { KeyboardEvent, useRef, useState } from "react";

interface Props {
  onSend: (text: string) => void;
  disabled: boolean;
}

export function InputBar({ onSend, disabled }: Props) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    ref.current?.focus();
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const canSend = !disabled && value.trim().length > 0;

  return (
    <div style={{
      display: "flex", gap: "0.6rem",
      padding: "0.85rem 1rem 1rem",
      borderTop: "1px solid rgba(30,45,74,0.7)",
      background: "rgba(10,14,26,0.95)",
      backdropFilter: "blur(12px)",
      alignItems: "flex-end",
      flexShrink: 0,
    }}>
      <textarea
        ref={ref}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={onKeyDown}
        disabled={disabled}
        placeholder="Ask about pediatric nutrition..."
        rows={1}
        style={{
          flex: 1, resize: "none",
          border: `1px solid ${canSend ? "rgba(0,255,148,0.3)" : "rgba(30,45,74,0.8)"}`,
          borderRadius: "10px",
          padding: "10px 14px",
          fontSize: "0.9rem",
          fontFamily: "var(--font-body)",
          background: disabled ? "rgba(15,21,37,0.5)" : "rgba(15,21,37,0.9)",
          color: "#E8EDF5",
          outline: "none",
          lineHeight: 1.5,
          minHeight: "44px", maxHeight: "120px",
          overflowY: "auto",
          transition: "border-color 0.2s",
          caretColor: "#00FF94",
        }}
      />
      <button
        onClick={submit}
        disabled={!canSend}
        aria-label="Send message"
        style={{
          background: canSend
            ? "linear-gradient(135deg, #00FF94, #00CC76)"
            : "rgba(30,45,74,0.6)",
          color: canSend ? "#0A0E1A" : "#4A5878",
          border: "none",
          borderRadius: "10px",
          padding: "10px 18px",
          fontSize: "0.875rem",
          fontFamily: "var(--font-body)",
          cursor: canSend ? "pointer" : "not-allowed",
          fontWeight: 700,
          transition: "all 0.15s",
          flexShrink: 0,
          boxShadow: canSend ? "0 0 16px rgba(0,255,148,0.3)" : "none",
          minWidth: "70px",
        }}
        onMouseEnter={e => { if (canSend) (e.currentTarget as HTMLElement).style.boxShadow = "0 0 24px rgba(0,255,148,0.5)"; }}
        onMouseLeave={e => { if (canSend) (e.currentTarget as HTMLElement).style.boxShadow = "0 0 16px rgba(0,255,148,0.3)"; }}
      >
        Send
      </button>
    </div>
  );
}
