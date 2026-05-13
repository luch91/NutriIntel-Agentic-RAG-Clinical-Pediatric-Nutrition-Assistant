import type { GeneralResponse } from "@/lib/types";
import { EvidenceBadge } from "@/components/ui/EvidenceBadge";

interface Props { data: GeneralResponse; }

export function GeneralCard({ data }: Props) {
  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
        <span style={{ color: "#00FF94", fontFamily: "var(--font-mono)", fontSize: "0.65rem", letterSpacing: "0.1em" }}>GENERAL</span>
        <div style={{ flex: 1, height: "1px", background: "rgba(0,255,148,0.15)" }}/>
      </div>
      <h2 style={titleStyle}>{data.title}</h2>

      {data.direct_answer && (
        <p style={{ fontWeight: 600, marginBottom: "0.75rem", lineHeight: 1.55, color: "#E8EDF5" }}>
          {data.direct_answer}
        </p>
      )}
      {data.explanation && (
        <p style={{ color: "#8B9BB4", fontSize: "0.9rem", lineHeight: 1.6, marginBottom: "0.75rem" }}>
          {data.explanation}
        </p>
      )}
      {data.examples && data.examples.length > 0 && (
        <div style={{ marginBottom: "0.75rem" }}>
          <Label>Examples</Label>
          <ul style={{ margin: 0, paddingLeft: "1.25rem", fontSize: "0.875rem", color: "#8B9BB4" }}>
            {data.examples.map((ex, i) => <li key={i}>{ex}</li>)}
          </ul>
        </div>
      )}
      {data.transition_note && (
        <p style={{ fontSize: "0.85rem", color: "#4A5878", fontStyle: "italic", marginBottom: "0.5rem" }}>
          {data.transition_note}
        </p>
      )}
      {data.follow_up_hint && (
        <p style={{ fontSize: "0.82rem", color: "#4A5878", marginTop: "0.5rem" }}>
          {data.follow_up_hint}
        </p>
      )}
      <EvidenceBadge evidence={data.evidence_summary} />
    </div>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ fontSize: "0.7rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", color: "#00FF94", marginBottom: "0.35rem", fontFamily: "var(--font-mono)" }}>
      {children}
    </div>
  );
}

const titleStyle: React.CSSProperties = {
  fontFamily: "var(--font-display)",
  fontSize: "1.05rem", fontWeight: 700,
  marginBottom: "0.6rem", color: "#E8EDF5",
};
