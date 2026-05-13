import type { ComparisonResponse, QualitativePoints, QuantitativeMatrix } from "@/lib/types";
import { EvidenceBadge } from "@/components/ui/EvidenceBadge";

interface Props { data: ComparisonResponse; }

function isQualitative(m: QuantitativeMatrix | QualitativePoints): m is QualitativePoints {
  return "entity_a" in m;
}

export function ComparisonCard({ data }: Props) {
  const entityA = data.entities[0] ?? "";
  const entityB = data.entities[1] ?? "";

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
        <span style={{ color: "#7C4DFF", fontFamily: "var(--font-mono)", fontSize: "0.65rem", letterSpacing: "0.1em" }}>COMPARISON</span>
        <div style={{ flex: 1, height: "1px", background: "rgba(124,77,255,0.2)" }}/>
      </div>

      <h2 style={titleStyle}>{data.title}</h2>
      <p style={{ fontWeight: 600, color: "#E8EDF5", marginBottom: "1rem", fontSize: "0.95rem" }}>
        {data.executive_takeaway}
      </p>
      {data.context_or_assumptions && (
        <p style={{ fontSize: "0.85rem", color: "#8B9BB4", marginBottom: "0.75rem" }}>
          {data.context_or_assumptions}
        </p>
      )}

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        {[entityA, entityB].filter(Boolean).map((e, i) => (
          <span key={i} style={{
            background: i === 0 ? "rgba(0,255,148,0.1)" : "rgba(124,77,255,0.1)",
            color: i === 0 ? "#00FF94" : "#7C4DFF",
            border: `1px solid ${i === 0 ? "rgba(0,255,148,0.3)" : "rgba(124,77,255,0.3)"}`,
            borderRadius: "6px", padding: "3px 12px",
            fontWeight: 700, fontSize: "0.875rem",
          }}>{e}</span>
        ))}
      </div>

      {isQualitative(data.matrix_or_points) ? (
        <QualitativeView points={data.matrix_or_points} />
      ) : (
        <QuantitativeView matrix={data.matrix_or_points} />
      )}

      {data.interpretation && (
        <div style={{ marginTop: "0.75rem", fontSize: "0.875rem" }}>
          <Label>Interpretation</Label>
          <p style={{ margin: 0, color: "#8B9BB4" }}>{data.interpretation}</p>
        </div>
      )}
      {data.decision_rules.length > 0 && (
        <div style={{ marginTop: "0.75rem" }}>
          <Label>Decision Guidance</Label>
          <ul style={{ margin: 0, paddingLeft: "1.25rem", fontSize: "0.875rem", color: "#8B9BB4" }}>
            {data.decision_rules.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
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

function QualitativeView({ points }: { points: QualitativePoints }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "0.75rem" }}>
      <Column label={points.entity_a} items={points.points_a} color="#00FF94" bg="rgba(0,255,148,0.05)" />
      <Column label={points.entity_b} items={points.points_b} color="#7C4DFF" bg="rgba(124,77,255,0.05)" />
    </div>
  );
}

function Column({ label, items, color, bg }: { label: string; items: string[]; color: string; bg: string }) {
  return (
    <div style={{ background: bg, border: `1px solid ${color}22`, borderRadius: "8px", padding: "0.75rem" }}>
      <div style={{ fontWeight: 700, color, marginBottom: "0.5rem", fontSize: "0.8rem", fontFamily: "var(--font-mono)" }}>{label}</div>
      {items.length > 0 ? (
        <ul style={{ margin: 0, paddingLeft: "1.25rem", fontSize: "0.85rem", color: "#8B9BB4" }}>
          {items.map((pt, i) => <li key={i}>{pt}</li>)}
        </ul>
      ) : (
        <p style={{ fontSize: "0.85rem", color: "#4A5878", margin: 0 }}>No data available.</p>
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
          <tr style={{ borderBottom: "1px solid rgba(30,45,74,0.8)" }}>
            {matrix.headers.map((h, i) => (
              <th key={i} style={{
                textAlign: "left", padding: "7px 10px",
                fontWeight: 700, color: "#00FF94",
                fontSize: "0.72rem", fontFamily: "var(--font-mono)", letterSpacing: "0.06em",
              }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.rows.map((row, i) => (
            <tr key={i} style={{ borderBottom: "1px solid rgba(30,45,74,0.4)" }}>
              {matrix.headers.map((h, j) => (
                <td key={j} style={{
                  padding: "7px 10px", color: j === 0 ? "#E8EDF5" : "#8B9BB4",
                  fontFamily: typeof row[h] === "number" ? "var(--font-mono)" : undefined,
                }}>
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
    <div style={{
      fontSize: "0.7rem", fontWeight: 700, textTransform: "uppercase",
      letterSpacing: "0.1em", color: "#7C4DFF", marginBottom: "0.35rem",
      fontFamily: "var(--font-mono)",
    }}>{children}</div>
  );
}

const titleStyle: React.CSSProperties = {
  fontFamily: "var(--font-display)", fontSize: "1.05rem",
  fontWeight: 700, marginBottom: "0.5rem", color: "#E8EDF5",
};
