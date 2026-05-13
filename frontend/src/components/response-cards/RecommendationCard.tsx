import type { RecommendationResponse } from "@/lib/types";
import { EvidenceBadge } from "@/components/ui/EvidenceBadge";

interface Props { data: RecommendationResponse; }

export function RecommendationCard({ data }: Props) {
  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
        <span style={{ color: "#00FF94", fontFamily: "var(--font-mono)", fontSize: "0.65rem", letterSpacing: "0.1em" }}>RECOMMENDATION</span>
        <div style={{ flex: 1, height: "1px", background: "rgba(0,255,148,0.15)" }}/>
      </div>

      <h2 style={titleStyle}>{data.title}</h2>

      {data.context_summary && (
        <p style={{ color: "#8B9BB4", marginBottom: "0.75rem", fontSize: "0.9rem" }}>
          {data.context_summary}
        </p>
      )}

      {data.nutrient_preview && data.nutrient_preview.length > 0 && (
        <div style={{ marginBottom: "1rem" }}>
          <Label>Reference Nutrient Intakes</Label>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid rgba(30,45,74,0.8)" }}>
                  <Th>Nutrient</Th>
                  <Th align="right">RDA</Th>
                  <Th align="right">AI</Th>
                  <Th>Unit</Th>
                </tr>
              </thead>
              <tbody>
                {data.nutrient_preview.map((row, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid rgba(30,45,74,0.3)" }}>
                    <td style={tdStyle}>{row.nutrient}</td>
                    <td style={{ ...tdStyle, textAlign: "right", fontFamily: "var(--font-mono)", color: "#00FF94" }}>
                      {row.rda ?? "—"}
                    </td>
                    <td style={{ ...tdStyle, textAlign: "right", fontFamily: "var(--font-mono)", color: "#7C4DFF" }}>
                      {row.ai ?? "—"}
                    </td>
                    <td style={{ ...tdStyle, color: "#4A5878" }}>{row.unit}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {data.practical_guidance && (
        <div style={{ marginBottom: "1rem" }}>
          <Label>Practical Guidance</Label>
          <p style={{ margin: 0, fontSize: "0.9rem", color: "#E8EDF5" }}>{data.practical_guidance}</p>
        </div>
      )}

      {data.foods_to_emphasize.length > 0 && (
        <div style={{ marginBottom: "0.75rem" }}>
          <Label>Foods to Emphasise</Label>
          <ul style={{ margin: 0, paddingLeft: "1.25rem", fontSize: "0.875rem", color: "#8B9BB4" }}>
            {data.foods_to_emphasize.map((f, i) => (
              <li key={i} style={{ marginBottom: "2px" }}>
                <span style={{ color: "#00FF94" }}>✓ </span>{f}
              </li>
            ))}
          </ul>
        </div>
      )}

      {data.foods_to_limit.length > 0 && (
        <div style={{ marginBottom: "0.75rem" }}>
          <Label color="#FF5252">Foods to Limit</Label>
          <ul style={{ margin: 0, paddingLeft: "1.25rem", fontSize: "0.875rem", color: "#8B9BB4" }}>
            {data.foods_to_limit.map((f, i) => (
              <li key={i} style={{ marginBottom: "2px" }}>
                <span style={{ color: "#FF5252" }}>✕ </span>{f}
              </li>
            ))}
          </ul>
        </div>
      )}

      {data.therapy_upgrade_note && (
        <div style={{
          marginTop: "0.75rem", padding: "0.75rem 1rem",
          background: "rgba(0,255,148,0.06)",
          border: "1px solid rgba(0,255,148,0.2)",
          borderRadius: "8px", fontSize: "0.875rem", color: "#00FF94",
        }}>
          {data.therapy_upgrade_note}
        </div>
      )}

      {data.follow_up_hint && (
        <p style={{ fontSize: "0.82rem", color: "#4A5878", marginTop: "0.75rem" }}>
          {data.follow_up_hint}
        </p>
      )}
      <EvidenceBadge evidence={data.evidence_summary} />
    </div>
  );
}

function Label({ children, color = "#00FF94" }: { children: React.ReactNode; color?: string }) {
  return (
    <div style={{
      fontSize: "0.7rem", fontWeight: 700, textTransform: "uppercase",
      letterSpacing: "0.1em", color, marginBottom: "0.4rem",
      fontFamily: "var(--font-mono)",
    }}>{children}</div>
  );
}

function Th({ children, align }: { children: React.ReactNode; align?: "left" | "right" }) {
  return (
    <th style={{
      textAlign: align ?? "left", padding: "6px 10px",
      fontWeight: 700, color: "#8B9BB4",
      fontSize: "0.72rem", textTransform: "uppercase",
      fontFamily: "var(--font-mono)",
    }}>{children}</th>
  );
}

const titleStyle: React.CSSProperties = {
  fontFamily: "var(--font-display)", fontSize: "1.05rem",
  fontWeight: 700, marginBottom: "0.5rem", color: "#E8EDF5",
};

const tdStyle: React.CSSProperties = {
  padding: "7px 10px", verticalAlign: "top", color: "#E8EDF5",
};
