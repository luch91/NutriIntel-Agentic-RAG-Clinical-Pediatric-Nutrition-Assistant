import type { TherapyResponse } from "@/lib/types";
import { EvidenceBadge } from "@/components/ui/EvidenceBadge";
import { NutrientTable } from "@/components/ui/NutrientTable";

const SEVERITY_COLORS: Record<string, string> = {
  HIGH:     "#FF5252",
  MODERATE: "#FFB547",
  LOW:      "#8B9BB4",
};

interface Props { data: TherapyResponse; }

export function TherapyCard({ data }: Props) {
  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
        <span style={{ color: "#FFB547", fontFamily: "var(--font-mono)", fontSize: "0.65rem", letterSpacing: "0.1em" }}>THERAPY PLAN</span>
        <div style={{ flex: 1, height: "1px", background: "rgba(255,181,71,0.2)" }}/>
      </div>

      <h2 style={sectionTitleStyle}>{data.title}</h2>
      <p style={{ marginBottom: "0.75rem", color: "#8B9BB4", fontSize: "0.9rem" }}>{data.summary}</p>

      {data.patient_summary && (
        <Section label="Patient" accent="#00FF94">
          <p style={{ margin: 0, color: "#E8EDF5", fontSize: "0.875rem" }}>{data.patient_summary}</p>
        </Section>
      )}
      {data.assumptions_used.length > 0 && (
        <Section label="Assumptions" accent="#8B9BB4">
          <ul style={{ margin: 0, paddingLeft: "1.25rem", color: "#8B9BB4", fontSize: "0.875rem" }}>
            {data.assumptions_used.map((a, i) => <li key={i}>{a}</li>)}
          </ul>
        </Section>
      )}
      {data.nutrient_targets.length > 0 && (
        <Section label="Nutrient Targets" accent="#00FF94">
          <NutrientTable rows={data.nutrient_targets} />
        </Section>
      )}
      {data.drug_nutrient_notes.length > 0 && (
        <Section label="Drug & Nutrient Interactions" accent="#FFB547">
          {data.drug_nutrient_notes.map((note, i) => (
            <div key={i} style={{ display: "flex", gap: "0.5rem", alignItems: "flex-start", marginBottom: "0.5rem" }}>
              <span style={{
                background: `${SEVERITY_COLORS[note.severity] ?? "#8B9BB4"}22`,
                color: SEVERITY_COLORS[note.severity] ?? "#8B9BB4",
                border: `1px solid ${SEVERITY_COLORS[note.severity] ?? "#8B9BB4"}44`,
                borderRadius: "4px", padding: "1px 7px",
                fontSize: "0.68rem", fontWeight: 700, whiteSpace: "nowrap",
                marginTop: "2px", fontFamily: "var(--font-mono)",
              }}>
                {note.severity}
              </span>
              <div style={{ fontSize: "0.875rem", color: "#E8EDF5" }}>
                <strong style={{ color: "#FFB547" }}>{note.drug}</strong>
                <span style={{ color: "#8B9BB4" }}> / {note.nutrient}: </span>
                {note.note}
              </div>
            </div>
          ))}
        </Section>
      )}
      {data.food_sources.length > 0 && (
        <Section label="Food Sources" accent="#00FF94">
          {data.food_sources.map((sec, i) => (
            <div key={i} style={{ marginBottom: "0.4rem", fontSize: "0.875rem" }}>
              <span style={{ fontWeight: 600, color: "#00FF94" }}>{sec.nutrient}: </span>
              <span style={{ color: "#8B9BB4" }}>{sec.foods.join(", ")}</span>
            </div>
          ))}
        </Section>
      )}
      {data.meal_plan && data.meal_plan.days.length > 0 && (
        <Section label="Meal Plan" accent="#7C4DFF">
          {data.meal_plan.days.map((day, i) => (
            <div key={i} style={{ marginBottom: "0.75rem" }}>
              <div style={{ fontWeight: 700, fontSize: "0.8rem", marginBottom: "4px", color: "#7C4DFF", fontFamily: "var(--font-mono)" }}>DAY {day.day}</div>
              {Array.isArray(day.meals) && day.meals.map((meal, j) => (
                <div key={j} style={{ marginLeft: "1rem", fontSize: "0.85rem", color: "#8B9BB4", marginBottom: "2px" }}>
                  <strong style={{ color: "#E8EDF5" }}>{meal.meal_name}:</strong>{" "}
                  {Array.isArray(meal.foods) ? meal.foods.join(", ") : ""}
                </div>
              ))}
            </div>
          ))}
        </Section>
      )}
      {data.next_step && (
        <p style={{ fontWeight: 600, color: "#00FF94", marginTop: "0.75rem", fontSize: "0.9rem" }}>
          {data.next_step}
        </p>
      )}
      {data.follow_up_hint && (
        <p style={{ fontSize: "0.82rem", color: "#4A5878", marginTop: "0.5rem" }}>{data.follow_up_hint}</p>
      )}
      <EvidenceBadge evidence={data.evidence_summary} />
    </div>
  );
}

function Section({ label, children, accent = "#00FF94" }: { label: string; children: React.ReactNode; accent?: string }) {
  return (
    <div style={{ marginBottom: "1rem" }}>
      <div style={{
        fontSize: "0.68rem", fontWeight: 700, textTransform: "uppercase",
        letterSpacing: "0.1em", color: accent, marginBottom: "0.4rem",
        fontFamily: "var(--font-mono)",
      }}>{label}</div>
      {children}
    </div>
  );
}

const sectionTitleStyle: React.CSSProperties = {
  fontFamily: "var(--font-display)", fontSize: "1.05rem",
  fontWeight: 700, marginBottom: "0.35rem", color: "#E8EDF5",
};
