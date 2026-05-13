import type { NutrientTargetRow } from "@/lib/types";

interface Props {
  rows: NutrientTargetRow[];
}

export function NutrientTable({ rows }: Props) {
  if (rows.length === 0) return null;
  const hasNotes = rows.some((r) => r.clinical_note !== null);

  return (
    <div style={{ overflowX: "auto" }}>
      <table
        style={{
          width: "100%",
          borderCollapse: "collapse",
          fontSize: "0.875rem",
          fontFamily: "var(--font-body)",
        }}
      >
        <thead>
          <tr style={{ borderBottom: "2px solid #E5E3DF" }}>
            <th style={thStyle}>Nutrient</th>
            <th style={{ ...thStyle, textAlign: "right" }}>Target</th>
            <th style={thStyle}>Unit</th>
            {hasNotes && <th style={thStyle}>Clinical Note</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={i}
              style={{ borderBottom: "1px solid #F0EFEC" }}
            >
              <td style={tdStyle}>{row.nutrient}</td>
              <td
                style={{
                  ...tdStyle,
                  textAlign: "right",
                  fontFamily: "var(--font-mono)",
                  fontWeight: 600,
                }}
              >
                {row.value}
              </td>
              <td style={{ ...tdStyle, color: "#777" }}>{row.unit}</td>
              {hasNotes && (
                <td style={{ ...tdStyle, color: "#888", fontSize: "0.82rem" }}>
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
  textAlign: "left",
  padding: "8px 12px",
  fontWeight: 600,
  color: "#555",
  fontSize: "0.8rem",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
};

const tdStyle: React.CSSProperties = {
  padding: "8px 12px",
  verticalAlign: "top",
};
