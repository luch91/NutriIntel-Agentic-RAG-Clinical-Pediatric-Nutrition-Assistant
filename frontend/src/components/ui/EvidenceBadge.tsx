"use client";

import { useState } from "react";
import type { EvidenceSummary } from "@/lib/types";

interface Props { evidence: EvidenceSummary; }

export function EvidenceBadge({ evidence }: Props) {
  const [open, setOpen] = useState(false);
  const count = evidence.used_sources.length;
  if (count === 0) return null;

  return (
    <div style={{ marginTop: "1rem" }}>
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          background: open ? "rgba(0,255,148,0.08)" : "transparent",
          border: "1px solid rgba(0,255,148,0.2)",
          borderRadius: "6px", padding: "4px 12px",
          fontSize: "0.75rem", color: "#00FF94",
          cursor: "pointer", fontFamily: "var(--font-mono)",
          letterSpacing: "0.06em", transition: "all 0.15s",
        }}
        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = "rgba(0,255,148,0.1)"; }}
        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = open ? "rgba(0,255,148,0.08)" : "transparent"; }}
      >
        {open ? "▲" : "▼"} SOURCES ({count})
      </button>

      {open && (
        <div style={{ marginTop: "0.6rem" }}>
          {evidence.used_sources.map((src, i) => (
            <div key={i} style={{
              borderLeft: "2px solid rgba(0,255,148,0.4)",
              paddingLeft: "0.75rem", marginBottom: "0.75rem",
              fontSize: "0.82rem",
            }}>
              <div style={{ fontWeight: 600, marginBottom: "2px", color: "#E8EDF5" }}>
                {src.source_title}
              </div>
              <div style={{ color: "#8B9BB4" }}>{src.excerpt_safe}</div>
            </div>
          ))}
          {evidence.retrieval_note && (
            <p style={{ fontSize: "0.75rem", color: "#4A5878", fontStyle: "italic", margin: 0 }}>
              {evidence.retrieval_note}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
