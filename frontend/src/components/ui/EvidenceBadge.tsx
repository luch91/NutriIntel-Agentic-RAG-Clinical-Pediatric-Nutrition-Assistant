"use client";

import { useState } from "react";
import type { EvidenceSummary } from "@/lib/types";

interface Props {
  evidence: EvidenceSummary;
}

export function EvidenceBadge({ evidence }: Props) {
  const [open, setOpen] = useState(false);
  const count = evidence.used_sources.length;

  if (count === 0) return null;

  return (
    <div style={{ marginTop: "1rem" }}>
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          background: "none",
          border: "1px solid #E5E3DF",
          borderRadius: "4px",
          padding: "4px 10px",
          fontSize: "0.8rem",
          color: "#00796B",
          cursor: "pointer",
          fontFamily: "var(--font-body)",
        }}
      >
        {open ? "▲" : "▼"} Sources ({count})
      </button>

      {open && (
        <div style={{ marginTop: "0.5rem" }}>
          {evidence.used_sources.map((src, i) => (
            <div
              key={i}
              style={{
                borderLeft: "3px solid #00796B",
                paddingLeft: "0.75rem",
                marginBottom: "0.75rem",
                fontSize: "0.82rem",
                color: "#555",
              }}
            >
              <div style={{ fontWeight: 600, marginBottom: "2px" }}>
                {src.source_title}
              </div>
              <div>{src.excerpt_safe}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
