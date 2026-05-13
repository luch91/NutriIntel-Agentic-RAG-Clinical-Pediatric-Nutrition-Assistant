import type { ComparisonResponse, QualitativePoints, QuantitativeMatrix } from "@/lib/types";
import { EvidenceBadge } from "@/components/ui/EvidenceBadge";

interface Props {
  data: ComparisonResponse;
}

function isQualitative(m: QuantitativeMatrix | QualitativePoints): m is QualitativePoints {
  return "entity_a" in m;
}

export function ComparisonCard({ data }: Props) {
  const entityA = data.entities[0] ?? "";
  const entityB = data.entities[1] ?? "";

  return (
    <div>
      <h2 style={titleStyle}>{data.title}</h2>

      <p style={{ fontWeight: 600, color: "#1C1C1A", marginBottom: "1rem", fontSize: "0.95rem" }}>
        {data.executive_takeaway}
      </p>

      {data.context_or_assumptions && (
        <p style={{ fontSize: "0.85rem", color: "#666", marginBottom: "0.75rem" }}>
          {data.context_or_assumptions}
        </p>
      )}

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        {[entityA, entityB].filter(Boolean).map((e, i) => (
          <span key={i} style={{
            background: i === 0 ? "#E8F5F3" : "#F3E8FF",
            color: i === 0 ? "#004D40" : "#4A148C",
            borderRadius: "4px",
            padding: "3px 10px",
            fontWeight: 600,
            fontSize: "0.875rem",
          }}>
            {e}
          </span>
        ))}
      </div>

      {isQualitative(data.matrix_or_points) ? (
        <QualitativeView points={data.matrix_or_points} />
      ) : (
        <QuantitativeView matrix={data.matrix_or_points} />
      )}

      {data.interpretation && (
        <div style={{ marginTop: "0.75rem", fontSize: "0.875rem", color: "#555" }}>
          <Label>Interpretation</Label>
          <p style={{ margin: 0 }}>{data.interpretation}</p>
        </div>
      )}

      {data.decision_rules.length > 0 && (
        <div style={{ marginTop: "0.75rem" }}>
          <Label>Decision Guidance</Label>
          <ul style={{ margin: 0, paddingLeft: "1.25rem", fontSize: "0.875rem" }}>
            {data.decision_rules.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        </div>
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

function QualitativeView({ points }: { points: QualitativePoints }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "0.75rem" }}>
      <Column label={points.entity_a} items={points.points_a} color="#004D40" />
      <Column label={points.entity_b} items={points.points_b} color="#4A148C" />
    </div>
  );
}

function Column({ label, items, color }: { label: string; items: string[]; color: string }) {
  return (
    <div>
      <div style={{ fontWeight: 700, color, marginBottom: "0.4rem", fontSize: "0.875rem" }}>{label}</div>
      {items.length > 0 ? (
        <ul style={{ margin: 0, paddingLeft: "1.25rem", fontSize: "0.875rem", color: "#444" }}>
          {items.map((pt, i) => <li key={i}>{pt}</li>)}
        </ul>
      ) : (
        <p style={{ fontSize: "0.85rem", color: "#aaa", margin: 0 }}>No data available.</p>
      )}
    </div>
  );
}

function QuantitativeView({ matrix }: { matrix: QuantitativeMatrix }) {
  if (matrix.headers.length === 0) return null;
  return (
    <div style={{ overflowX: "auto", marginBottom: "0.75rem" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
        <thead>
          <tr style={{ borderBottom: "2px solid #E5E3DF" }}>
            {matrix.headers.map((h, i) => (
              <th key={i} style={{ textAlign: "left", padding: "7px 10px", fontWeight: 600, color: "#555", fontSize: "0.78rem" }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.rows.map((row, i) => (
            <tr key={i} style={{ borderBottom: "1px solid #F0EFEC" }}>
              {matrix.headers.map((h, j) => (
                <td key={j} style={{ padding: "7px 10px", fontFamily: typeof row[h] === "number" ? "var(--font-mono)" : undefined }}>
                  {row[h] !== undefined && row[h] !== null ? String(row[h]) : "—"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
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
