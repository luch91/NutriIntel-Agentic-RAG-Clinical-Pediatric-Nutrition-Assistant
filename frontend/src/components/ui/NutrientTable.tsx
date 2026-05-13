import type { NutrientTargetRow } from "@/lib/types";

interface Props { rows: NutrientTargetRow[]; }

export function NutrientTable({ rows }: Props) {
  if (rows.length === 0) return null;
  const hasNotes = rows.some((r) => r.clinical_note !== null);

  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
        <thead>
          <tr style={{ borderBottom: "1px solid rgba(0,255,148,0.2)" }}>
            <th style={thStyle}>Nutrient</th>
            <th style={{ ...thStyle, textAlign: "right" }}>Target</th>
            <th style={thStyle}>Unit</th>
            {hasNotes && <th style={thStyle}>Clinical Note</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} style={{
              borderBottom: "1px solid rgba(30,45,74,0.4)",
              background: i % 2 === 0 ? "transparent" : "rgba(0,255,148,0.02)",
            }}>
              <td style={tdStyle}>{row.nutrient}</td>
              <td style={{
                ...tdStyle, textAlign: "right",
                fontFamily: "var(--font-mono)", fontWeight: 700, color: "#00FF94",
              }}>{row.value}</td>
              <td style={{ ...tdStyle, color: "#4A5878", fontFamily: "var(--font-mono)", fontSize: "0.8rem" }}>{row.unit}</td>
              {hasNotes && (
                <td style={{ ...tdStyle, color: "#8B9BB4", fontSize: "0.82rem" }}>
                  {row.clinical_note ?? "—"}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const thStyle: React.CSSProperties = {
  textAlign: "left", padding: "8px 12px",
  fontWeight: 700, color: "#8B9BB4",
  fontSize: "0.72rem", textTransform: "uppercase",
  letterSpacing: "0.08em", fontFamily: "var(--font-mono)",
};

const tdStyle: React.CSSProperties = {
  padding: "8px 12px", verticalAlign: "top", color: "#E8EDF5",
};
