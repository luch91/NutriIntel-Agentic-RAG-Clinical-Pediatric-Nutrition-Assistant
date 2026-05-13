import type { TherapyResponse } from "@/lib/types";
import { EvidenceBadge } from "@/components/ui/EvidenceBadge";
import { NutrientTable } from "@/components/ui/NutrientTable";

const SEVERITY_COLORS: Record<string, string> = {
  HIGH: "#C62828",
  MODERATE: "#E65100",
  LOW: "#757575",
};

interface Props {
  data: TherapyResponse;
}

export function TherapyCard({ data }: Props) {
  return (
    <div>
      <h2 style={sectionTitleStyle}>{data.title}</h2>
      <p style={{ marginBottom: "0.75rem", color: "#555" }}>{data.summary}</p>

      {data.patient_summary && (
        <Section label="Patient">
          <p style={{ margin: 0 }}>{data.patient_summary}</p>
        </Section>
      )}

      {data.assumptions_used.length > 0 && (
        <Section label="Assumptions">
          <ul style={{ margin: 0, paddingLeft: "1.25rem", color: "#888", fontSize: "0.875rem" }}>
            {data.assumptions_used.map((a, i) => <li key={i}>{a}</li>)}
          </ul>
        </Section>
      )}

      {data.nutrient_targets.length > 0 && (
        <Section label="Nutrient Targets">
          <NutrientTable rows={data.nutrient_targets} />
        </Section>
      )}

      {data.drug_nutrient_notes.length > 0 && (
        <Section label="Drug &amp; Nutrient Interactions">
          {data.drug_nutrient_notes.map((note, i) => (
            <div key={i} style={{ display: "flex", gap: "0.5rem", alignItems: "flex-start", marginBottom: "0.5rem" }}>
              <span
                style={{
                  background: SEVERITY_COLORS[note.severity] ?? "#757575",
                  color: "#fff",
                  borderRadius: "3px",
                  padding: "1px 6px",
                  fontSize: "0.72rem",
                  fontWeight: 700,
                  whiteSpace: "nowrap",
                  marginTop: "2px",
                }}
              >
                {note.severity}
              </span>
              <div style={{ fontSize: "0.875rem" }}>
                <strong>{note.drug}</strong> / {note.nutrient}: {note.note}
              </div>
            </div>
          ))}
        </Section>
      )}

      {data.food_sources.length > 0 && (
        <Section label="Food Sources">
          {data.food_sources.map((sec, i) => (
            <div key={i} style={{ marginBottom: "0.5rem" }}>
              <span style={{ fontWeight: 600, fontSize: "0.875rem" }}>{sec.nutrient}: </span>
              <span style={{ fontSize: "0.875rem", color: "#555" }}>{sec.foods.join(", ")}</span>
            </div>
          ))}
        </Section>
      )}

      {data.meal_plan && data.meal_plan.days.length > 0 && (
        <Section label="Meal Plan">
          {data.meal_plan.days.map((day, i) => (
            <div key={i} style={{ marginBottom: "0.75rem" }}>
              <div style={{ fontWeight: 600, fontSize: "0.875rem", marginBottom: "4px" }}>Day {day.day}</div>
              {Array.isArray(day.meals) && day.meals.map((meal, j) => (
                <div key={j} style={{ marginLeft: "1rem", fontSize: "0.85rem", color: "#555", marginBottom: "2px" }}>
                  <strong>{meal.meal_name}:</strong> {Array.isArray(meal.foods) ? meal.foods.join(", ") : ""}
                </div>
              ))}
            </div>
          ))}
        </Section>
      )}

      {data.next_step && (
        <p style={{ fontWeight: 600, color: "#00796B", marginTop: "0.75rem", fontSize: "0.9rem" }}>
          {data.next_step}
        </p>
      )}

      {data.follow_up_hint && (
        <p style={{ fontSize: "0.82rem", color: "#888", marginTop: "0.5rem" }}>{data.follow_up_hint}</p>
      )}

      <EvidenceBadge evidence={data.evidence_summary} />
    </div>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: "1rem" }}>
      <div style={labelStyle}>{label}</div>
      {children}
    </div>
  );
}

const sectionTitleStyle: React.CSSProperties = {
  fontFamily: "var(--font-display)",
  fontSize: "1.1rem",
  fontWeight: 600,
  marginBottom: "0.35rem",
  color: "#1C1C1A",
};

const labelStyle: React.CSSProperties = {
  fontSize: "0.75rem",
  fontWeight: 700,
  textTransform: "uppercase",
  letterSpacing: "0.06em",
  color: "#00796B",
  marginBottom: "0.4rem",
};
