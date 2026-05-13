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

  return (
    <div
      style={{
        display: "flex",
        gap: "0.5rem",
        padding: "0.75rem 1rem",
        borderTop: "1px solid #E5E3DF",
        background: "#F7F6F3",
        alignItems: "flex-end",
      }}
    >
      <textarea
        ref={ref}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={onKeyDown}
        disabled={disabled}
        placeholder="Ask about pediatric nutrition..."
        rows={1}
        style={{
          flex: 1,
          resize: "none",
          border: "1px solid #E5E3DF",
          borderRadius: "8px",
          padding: "10px 14px",
          fontSize: "0.9rem",
          fontFamily: "var(--font-body)",
          background: disabled ? "#EDECEA" : "#FFFFFF",
          color: "#1C1C1A",
          outline: "none",
          lineHeight: 1.5,
          minHeight: "42px",
          maxHeight: "120px",
          overflowY: "auto",
        }}
      />
      <button
        onClick={submit}
        disabled={disabled || !value.trim()}
        aria-label="Send message"
        style={{
          background: disabled || !value.trim() ? "#B2DFDB" : "#00796B",
          color: "#fff",
          border: "none",
          borderRadius: "8px",
          padding: "10px 18px",
          fontSize: "0.9rem",
          fontFamily: "var(--font-body)",
          cursor: disabled || !value.trim() ? "not-allowed" : "pointer",
          fontWeight: 600,
          transition: "background 0.15s",
          flexShrink: 0,
        }}
      >
        Send
      </button>
    </div>
  );
}
