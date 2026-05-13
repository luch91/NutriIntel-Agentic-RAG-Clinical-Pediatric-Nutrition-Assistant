import type { RecommendationResponse } from "@/lib/types";
import { EvidenceBadge } from "@/components/ui/EvidenceBadge";

interface Props {
  data: RecommendationResponse;
}

export function RecommendationCard({ data }: Props) {
  return (
    <div>
      <h2 style={titleStyle}>{data.title}</h2>

      {data.context_summary && (
        <p style={{ color: "#555", marginBottom: "0.75rem", fontSize: "0.9rem" }}>
          {data.context_summary}
        </p>
      )}

      {data.nutrient_preview && data.nutrient_preview.length > 0 && (
        <div style={{ marginBottom: "1rem" }}>
          <Label>Reference Nutrient Intakes</Label>
          <div style={{ overflowX: "auto" }}>
            <table style={tableStyle}>
              <thead>
                <tr style={{ borderBottom: "2px solid #E5E3DF" }}>
                  <Th>Nutrient</Th>
                  <Th align="right">RDA</Th>
                  <Th align="right">AI</Th>
                  <Th>Unit</Th>
                </tr>
              </thead>
              <tbody>
                {data.nutrient_preview.map((row, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid #F0EFEC" }}>
                    <td style={tdStyle}>{row.nutrient}</td>
                    <td style={{ ...tdStyle, textAlign: "right", fontFamily: "var(--font-mono)" }}>
                      {row.rda ?? "—"}
                    </td>
                    <td style={{ ...tdStyle, textAlign: "right", fontFamily: "var(--font-mono)" }}>
                      {row.ai ?? "—"}
                    </td>
                    <td style={{ ...tdStyle, color: "#888" }}>{row.unit}</td>
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
          <p style={{ margin: 0, fontSize: "0.9rem" }}>{data.practical_guidance}</p>
        </div>
      )}

      {data.foods_to_emphasize.length > 0 && (
        <div style={{ marginBottom: "0.75rem" }}>
          <Label>Foods to Emphasise</Label>
          <ul style={{ margin: 0, paddingLeft: "1.25rem", fontSize: "0.875rem" }}>
            {data.foods_to_emphasize.map((f, i) => <li key={i}>{f}</li>)}
          </ul>
        </div>
      )}

      {data.foods_to_limit.length > 0 && (
        <div style={{ marginBottom: "0.75rem" }}>
          <Label>Foods to Limit</Label>
          <ul style={{ margin: 0, paddingLeft: "1.25rem", fontSize: "0.875rem", color: "#B71C1C" }}>
            {data.foods_to_limit.map((f, i) => <li key={i}>{f}</li>)}
          </ul>
        </div>
      )}

      {data.therapy_upgrade_note && (
        <p style={{
          marginTop: "0.75rem",
          padding: "0.6rem 0.9rem",
          background: "#E8F5F3",
          borderRadius: "6px",
          fontSize: "0.875rem",
          color: "#004D40",
        }}>
          {data.therapy_upgrade_note}
        </p>
      )}

      {data.follow_up_hint && (
        <p style={{ fontSize: "0.82rem", color: "#888", marginTop: "0.75rem" }}>
          {data.follow_up_hint}
        </p>
      )}

      <EvidenceBadge evidence={data.evidence_summary} />
    </div>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      fontSize: "0.75rem",
      fontWeight: 700,
      textTransform: "uppercase",
      letterSpacing: "0.06em",
      color: "#00796B",
      marginBottom: "0.4rem",
    }}>
      {children}
    </div>
  );
}

function Th({ children, align }: { children: React.ReactNode; align?: "left" | "right" }) {
  return (
    <th style={{
      textAlign: align ?? "left",
      padding: "6px 10px",
      fontWeight: 600,
      color: "#555",
      fontSize: "0.78rem",
      textTransform: "uppercase",
    }}>
      {children}
    </th>
  );
}

const titleStyle: React.CSSProperties = {
  fontFamily: "var(--font-display)",
  fontSize: "1.1rem",
  fontWeight: 600,
  marginBottom: "0.5rem",
  color: "#1C1C1A",
};

const tableStyle: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: "0.875rem",
};

const tdStyle: React.CSSProperties = {
  padding: "7px 10px",
  verticalAlign: "top",
};
