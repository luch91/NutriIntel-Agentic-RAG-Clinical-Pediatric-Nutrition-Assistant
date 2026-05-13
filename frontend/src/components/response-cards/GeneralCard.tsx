import type { GeneralResponse } from "@/lib/types";
import { EvidenceBadge } from "@/components/ui/EvidenceBadge";

interface Props {
  data: GeneralResponse;
}

export function GeneralCard({ data }: Props) {
  return (
    <div>
      <h2 style={titleStyle}>{data.title}</h2>

      {data.direct_answer && (
        <p style={{ fontWeight: 500, marginBottom: "0.75rem", lineHeight: 1.55 }}>
          {data.direct_answer}
        </p>
      )}

      {data.explanation && (
        <p style={{ color: "#444", fontSize: "0.9rem", lineHeight: 1.6, marginBottom: "0.75rem" }}>
          {data.explanation}
        </p>
      )}

      {data.examples && data.examples.length > 0 && (
        <div style={{ marginBottom: "0.75rem" }}>
          <Label>Examples</Label>
          <ul style={{ margin: 0, paddingLeft: "1.25rem", fontSize: "0.875rem", color: "#555" }}>
            {data.examples.map((ex, i) => <li key={i}>{ex}</li>)}
          </ul>
        </div>
      )}

      {data.transition_note && (
        <p style={{ fontSize: "0.85rem", color: "#888", fontStyle: "italic", marginBottom: "0.5rem" }}>
          {data.transition_note}
        </p>
      )}

      {data.follow_up_hint && (
        <p style={{ fontSize: "0.82rem", color: "#888", marginTop: "0.5rem" }}>
          {data.follow_up_hint}
        </p>
      )}

      <EvidenceBadge evidence={data.evidence_summary} />
    </div>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "#00796B", marginBottom: "0.35rem" }}>
      {children}
    </div>
  );
}

const titleStyle: React.CSSProperties = {
  fontFamily: "var(--font-display)",
  fontSize: "1.1rem",
  fontWeight: 600,
  marginBottom: "0.5rem",
  color: "#1C1C1A",
};
